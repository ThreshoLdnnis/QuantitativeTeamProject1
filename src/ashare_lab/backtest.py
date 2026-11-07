"""Auditable daily accounting for the teaching baseline.

Signals use month-end information and execute at the following session's open.
Quantities are fractional *adjusted-price units*, not actual exchange shares.
The engine is a price-return approximation: it does not book cash dividends,
corporate actions, board lots, minimum commissions, market impact or capacity.
It honors supplied directional execution flags; unknown flags are an explicit
configuration choice. Rejected orders expire rather than retry the next day.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    daily: pd.DataFrame
    trades: pd.DataFrame
    positions: pd.DataFrame
    orders: pd.DataFrame


DAILY_COLUMNS = ["date", "nav", "cash", "equity", "return", "turnover", "cost", "holdings_count"]
TRADE_COLUMNS = ["date", "signal_date", "symbol", "side", "quantity", "price", "notional", "commission", "tax", "slippage_cost"]
POSITION_COLUMNS = ["date", "symbol", "quantity", "close", "market_value", "weight"]
ORDER_COLUMNS = ["date", "signal_date", "symbol", "side", "status", "reason", "requested_quantity", "filled_quantity"]


def _positive_price(row, column: str, symbol: str, date: pd.Timestamp) -> float:
    if row is None:
        raise ValueError(f"Missing held price row: {symbol} on {date.date()}")
    value = float(row[column])
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"Invalid {column} for {symbol} on {date.date()}: {value}")
    return value


def _execution_calendar(calendar: pd.DatetimeIndex) -> dict:
    """Map next-session execution dates to completed month-end signal dates."""
    dates = pd.DatetimeIndex(pd.to_datetime(calendar)).sort_values().unique()
    if len(dates) < 2:
        return {}
    last = pd.Series(dates, index=dates).groupby(dates.to_period("M")).last()
    next_day = dict(zip(dates[:-1], dates[1:]))
    return {next_day[signal]: signal for signal in last if signal in next_day}


def run_backtest(
    prices: pd.DataFrame,
    factors: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    config: dict,
    score_column: Optional[str] = "composite",
    top_n: Optional[int] = None,
) -> BacktestResult:
    """Run an equal-weight monthly strategy with cash and realized holdings.

    ``score_column=None`` is the equal-weight pool benchmark, using precisely
    the factor-complete universe at each signal. Ties sort by symbol. Buy/sell
    flags are observed only when trying to execute; they do not change ranking.
    ``cost_multiplier`` (default 1) scales all three configured cost rates.

    A rebalance targets equal weights against pretrade open equity, sells
    reductions first, then scales buy shortfalls to affordable cash. An
    unsellable holding remains in the portfolio. A blocked buy leaves cash.
    No orders retry before the next monthly rebalance, and final holdings are
    marked to the last close without charging a hypothetical liquidation.

    ``daily.equity`` includes cash. ``positions.close`` is adjusted close;
    ``turnover`` is total executed buy+sell notional / pretrade open equity,
    without division by two. ``cost`` includes fees, sell tax and slippage.
    """
    dates = pd.DatetimeIndex(pd.to_datetime(calendar)).sort_values().unique()
    start, end = pd.Timestamp(config["start"]), pd.Timestamp(config["end"])
    dates = dates[(dates >= start) & (dates <= end)]
    if len(dates) == 0:
        raise ValueError("No calendar sessions inside the backtest interval")
    initial_cash = float(config.get("initial_cash", 1_000_000.0))
    if not np.isfinite(initial_cash) or initial_cash <= 0:
        raise ValueError("initial_cash must be positive and finite")
    if score_column is not None:
        top_n = int(config.get("top_n", 10) if top_n is None else top_n)
        if top_n <= 0:
            raise ValueError("top_n must be positive")
    multiplier = float(config.get("cost_multiplier", 1.0))
    rates = [float(config.get(key, default)) * multiplier / 10_000.0 for key, default in
             [("commission_bps", 3), ("slippage_bps", 5), ("sell_tax_bps", 5)]]
    commission_rate, slip_rate, tax_rate = rates
    if (not all(np.isfinite(x) and x >= 0 for x in [multiplier, *rates])
            or slip_rate >= 1 or commission_rate + tax_rate >= 1):
        raise ValueError("Cost rates must be finite, nonnegative and below 100%")
    allow_unknown = bool(config.get("allow_unknown_status", False))

    p = prices.copy()
    p["date"] = pd.to_datetime(p["date"])
    p["symbol"] = p["symbol"].astype(str)
    required = {"date", "symbol", "adj_open", "adj_close", "can_buy", "can_sell", "status_known"}
    if not required.issubset(p.columns):
        raise ValueError(f"Missing price columns: {sorted(required - set(p.columns))}")
    if p.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate price rows (date, symbol)")
    price_days = {day: frame.set_index("symbol") for day, frame in p.groupby("date", sort=False)}
    f = factors.copy()
    f["date"] = pd.to_datetime(f["date"])
    f["symbol"] = f["symbol"].astype(str)
    if f.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate factor rows (date, symbol)")
    score = "composite" if score_column is None else score_column
    if score not in f:
        raise ValueError(f"Missing factor score column: {score}")
    factor_days = {day: frame for day, frame in f.groupby("date", sort=False)}
    executions = _execution_calendar(pd.DatetimeIndex(calendar))

    cash = initial_cash
    holdings: dict[str, float] = {}
    daily_rows, trade_rows, position_rows, order_rows = [], [], [], []
    previous_equity = initial_cash

    for day in dates:
        day_prices = price_days.get(day)

        def row_for(symbol):
            return None if day_prices is None or symbol not in day_prices.index else day_prices.loc[symbol]

        # All held instruments need a valid session row. No implicit forward fill.
        for symbol in holdings:
            row = row_for(symbol)
            _positive_price(row, "adj_open", symbol, day)
            _positive_price(row, "adj_close", symbol, day)

        day_cost, day_notional = 0.0, 0.0
        open_equity = cash + sum(quantity * _positive_price(row_for(symbol), "adj_open", symbol, day)
                                 for symbol, quantity in holdings.items())
        signal_date = executions.get(day)
        if signal_date is not None and start <= signal_date <= end:
            signal = factor_days.get(signal_date, f.iloc[:0])
            # All comparisons use the same three-factor-complete research pool.
            if "composite" in signal:
                signal = signal.loc[np.isfinite(pd.to_numeric(signal["composite"], errors="coerce"))]
            signal = signal.loc[np.isfinite(pd.to_numeric(signal[score], errors="coerce"))]
            signal = signal.sort_values([score, "symbol"], ascending=[False, True], kind="stable")
            selected = signal["symbol"].tolist() if score_column is None else signal.head(top_n)["symbol"].tolist()
            allocation = open_equity / len(selected) if selected else 0.0
            targets = {}
            for symbol in selected:
                row = row_for(symbol)
                try:
                    price = _positive_price(row, "adj_open", symbol, day)
                except (ValueError, TypeError, KeyError):
                    order_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="buy",
                                           status="rejected", reason="unavailable_open", requested_quantity=np.nan,
                                           filled_quantity=0.0))
                    # If already held, the validation above has already raised.
                    continue
                targets[symbol] = allocation / price

            def allowed(symbol, side):
                row = row_for(symbol)
                if pd.isna(row["status_known"]) or not bool(row["status_known"]):
                    if not allow_unknown:
                        raise ValueError(f"Unknown execution status: {symbol} on {day.date()}; "
                                         "supply historical flags or explicitly allow the teaching assumption")
                flag = row["can_buy" if side == "buy" else "can_sell"]
                return pd.notna(flag) and bool(flag)

            # A failed sale retains the old holding; its market value is not cash.
            for symbol in sorted(list(holdings)):
                requested = max(holdings[symbol] - targets.get(symbol, 0.0), 0.0)
                if requested <= 1e-12:
                    continue
                if not allowed(symbol, "sell"):
                    order_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="sell",
                                           status="rejected", reason="sell_blocked", requested_quantity=requested,
                                           filled_quantity=0.0))
                    continue
                reference = _positive_price(row_for(symbol), "adj_open", symbol, day)
                fill_price = reference * (1 - slip_rate)
                notional = requested * fill_price
                commission, tax = notional * commission_rate, notional * tax_rate
                slip_cost = requested * (reference - fill_price)
                cash += notional - commission - tax
                holdings[symbol] -= requested
                if holdings[symbol] <= 1e-12:
                    del holdings[symbol]
                trade_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="sell",
                                       quantity=requested, price=fill_price, notional=notional,
                                       commission=commission, tax=tax, slippage_cost=slip_cost))
                order_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="sell",
                                       status="filled", reason="", requested_quantity=requested,
                                       filled_quantity=requested))
                day_cost += commission + tax + slip_cost
                day_notional += notional

            buys = []
            for symbol in sorted(targets):
                requested = max(targets[symbol] - holdings.get(symbol, 0.0), 0.0)
                if requested <= 1e-12:
                    continue
                if not allowed(symbol, "buy"):
                    order_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="buy",
                                           status="rejected", reason="buy_blocked", requested_quantity=requested,
                                           filled_quantity=0.0))
                    continue
                reference = _positive_price(row_for(symbol), "adj_open", symbol, day)
                fill_price = reference * (1 + slip_rate)
                buys.append((symbol, requested, reference, fill_price))
            required_cash = sum(quantity * fill_price * (1 + commission_rate)
                                for _, quantity, _, fill_price in buys)
            scale = min(1.0, max(cash, 0.0) / required_cash) if required_cash > 0 else 0.0
            for symbol, requested, reference, fill_price in buys:
                filled = requested * scale
                if filled <= 1e-12:
                    order_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="buy",
                                           status="rejected", reason="insufficient_cash", requested_quantity=requested,
                                           filled_quantity=0.0))
                    continue
                notional = filled * fill_price
                commission = notional * commission_rate
                slip_cost = filled * (fill_price - reference)
                cash -= notional + commission
                holdings[symbol] = holdings.get(symbol, 0.0) + filled
                trade_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="buy",
                                       quantity=filled, price=fill_price, notional=notional,
                                       commission=commission, tax=0.0, slippage_cost=slip_cost))
                order_rows.append(dict(date=day, signal_date=signal_date, symbol=symbol, side="buy",
                                       status="partial" if scale < 1 - 1e-12 else "filled",
                                       reason="cash_scaled" if scale < 1 - 1e-12 else "",
                                       requested_quantity=requested, filled_quantity=filled))
                day_cost += commission + slip_cost
                day_notional += notional

        if cash < -max(initial_cash * 1e-10, 1e-7):
            raise ArithmeticError(f"Negative cash on {day.date()}: {cash}")
        cash = max(cash, 0.0)  # floating-point dust only
        market_values = {symbol: quantity * _positive_price(row_for(symbol), "adj_close", symbol, day)
                         for symbol, quantity in holdings.items()}
        equity = cash + sum(market_values.values())
        if not np.isfinite(equity) or equity <= 0:
            raise ArithmeticError(f"Nonpositive portfolio equity on {day.date()}")
        daily_rows.append(dict(date=day, nav=equity / initial_cash, cash=cash, equity=equity,
                               **{"return": equity / previous_equity - 1},
                               turnover=day_notional / open_equity if open_equity > 0 else 0.0,
                               cost=day_cost, holdings_count=len(holdings)))
        for symbol in sorted(holdings):
            position_rows.append(dict(date=day, symbol=symbol, quantity=holdings[symbol],
                                      close=float(row_for(symbol)["adj_close"]),
                                      market_value=market_values[symbol], weight=market_values[symbol] / equity))
        previous_equity = equity

    return BacktestResult(pd.DataFrame(daily_rows, columns=DAILY_COLUMNS),
                          pd.DataFrame(trade_rows, columns=TRADE_COLUMNS),
                          pd.DataFrame(position_rows, columns=POSITION_COLUMNS),
                          pd.DataFrame(order_rows, columns=ORDER_COLUMNS))


def metrics(daily: pd.DataFrame, annual_risk_free: float = 0.0) -> dict:
    """Performance from daily returns, including initial costs and drawdowns.

    Works on a chronological slice too: its first return retains the preceding
    session's valuation baseline. Annualization uses 252 sessions, not calendar
    years. Sharpe is the arithmetic daily excess mean / sample standard deviation
    times sqrt(252). ICIR is a separate research statistic.
    """
    if len(daily) == 0:
        return {key: np.nan for key in ["total_return", "annual_return", "annual_volatility", "sharpe",
                                         "max_drawdown", "annual_turnover", "total_cost"]}
    returns = pd.to_numeric(daily["return"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(returns).all() or (returns <= -1).any():
        raise ValueError("Invalid daily returns")
    if annual_risk_free <= -1 or not np.isfinite(annual_risk_free):
        raise ValueError("annual_risk_free must be finite and greater than -1")
    wealth = np.r_[1.0, np.cumprod(1 + returns)]
    n = len(returns)
    total = float(wealth[-1] - 1)
    volatility = float(np.std(returns, ddof=1)) if n > 1 else np.nan
    daily_rf = (1 + annual_risk_free) ** (1 / 252) - 1
    sharpe = float((np.mean(returns) - daily_rf) / volatility * np.sqrt(252)) if volatility > 0 else np.nan
    return dict(total_return=total, annual_return=float(wealth[-1] ** (252 / n) - 1),
                annual_volatility=volatility * np.sqrt(252), sharpe=sharpe,
                max_drawdown=float(np.min(wealth / np.maximum.accumulate(wealth) - 1)),
                annual_turnover=float(daily["turnover"].sum() * 252 / n),
                total_cost=float(daily["cost"].sum()))
