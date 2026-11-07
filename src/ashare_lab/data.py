"""CSV contract, reproducible synthetic fixture, SQLite and optional AKShare input."""
from datetime import datetime, timezone
from contextlib import closing
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sqlite3

import numpy as np
import pandas as pd

PRICE_COLUMNS = ["date", "symbol", "open", "high", "low", "close", "adj_open",
                 "adj_close", "volume", "turnover", "can_buy", "can_sell", "status_known"]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _bool_column(series, name):
    mapped = series.astype(str).str.lower().map({"true": True, "false": False, "1": True, "0": False})
    if mapped.isna().any():
        raise ValueError(f"{name}: expected 0/1 or true/false, no missing flags")
    return mapped.astype(bool)


def load_dataset(folder):
    folder = Path(folder)
    prices = pd.read_csv(folder / "prices.csv", dtype={"symbol": str}, parse_dates=["date"])
    universe = pd.read_csv(folder / "universe.csv", dtype={"symbol": str}, parse_dates=["date"])
    raw_calendar = pd.read_csv(folder / "calendar.csv", parse_dates=["date"])
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    for col in PRICE_COLUMNS:
        if col not in prices:
            raise ValueError(f"prices.csv missing {col}")
    for col in ("open", "high", "low", "close", "adj_open", "adj_close", "volume", "turnover"):
        prices[col] = pd.to_numeric(prices[col], errors="raise")
    for col in ("can_buy", "can_sell", "status_known"):
        prices[col] = _bool_column(prices[col], col)
    universe["eligible"] = _bool_column(universe["eligible"], "eligible")
    if raw_calendar["date"].duplicated().any():
        raise ValueError("duplicate calendar dates")
    calendar = pd.DatetimeIndex(raw_calendar["date"].sort_values())
    validate_dataset(prices, universe, calendar)
    return prices.sort_values(["date", "symbol"]), universe, calendar, metadata


def validate_dataset(prices, universe, calendar):
    calendar = pd.DatetimeIndex(calendar)
    if calendar.hasnans or calendar.has_duplicates or not calendar.equals(calendar.normalize()):
        raise ValueError("calendar must have unique nonmissing midnight session labels")
    if prices.empty or universe.empty or len(calendar) < 2:
        raise ValueError("empty dataset or insufficient trading calendar")
    for name, frame in (("prices", prices), ("universe", universe)):
        if frame[["date", "symbol"]].isna().any().any():
            raise ValueError(f"{name}: missing keys")
        if frame.duplicated(["date", "symbol"]).any():
            raise ValueError(f"{name}: duplicate date/symbol keys")
        if not frame["date"].isin(calendar).all():
            raise ValueError(f"{name}: date outside trading calendar")
        if (frame["date"] != frame["date"].dt.normalize()).any():
            raise ValueError(f"{name}: dates must be midnight session labels")
    cols = ["open", "high", "low", "close", "adj_open", "adj_close"]
    numeric = prices[cols].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy()).all() or (numeric <= 0).any().any():
        raise ValueError("prices must be finite and strictly positive; missing held prices cannot be filled silently")
    if ((numeric["high"] + 1e-8 < numeric[["open", "close", "low"]].max(axis=1)) |
            (numeric["low"] - 1e-8 > numeric[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("invalid OHLC ordering")
    volume = pd.to_numeric(prices["volume"], errors="coerce")
    if not np.isfinite(volume).all() or (volume < 0).any():
        raise ValueError("volume must be finite and non-negative")
    turnover = pd.to_numeric(prices["turnover"], errors="coerce")
    if (prices["turnover"].notna() & ~np.isfinite(turnover)).any() or (turnover.dropna() < 0).any():
        raise ValueError("turnover must be a non-negative fraction or missing")
    # A zero-volume day cannot be declared executable, even with unknown historical status.
    if ((volume == 0) & (prices["can_buy"] | prices["can_sell"])).any():
        raise ValueError("zero-volume rows must have can_buy=can_sell=False")


def data_quality(prices, universe, calendar, metadata):
    active = universe.loc[universe["eligible"], ["date", "symbol"]]
    coverage = active.merge(prices[["date", "symbol"]], on=["date", "symbol"], how="left", indicator=True)
    warnings = list(metadata.get("limitations", []))
    unknown = int((~prices["status_known"]).sum())
    if unknown:
        warnings.append("Historical execution status is unknown on some rows; assumed fills are educational only.")
    missing = int((coverage["_merge"] == "left_only").sum())
    if missing:
        warnings.append("Eligible symbol/session rows are missing. Rolling windows are invalidated; missing held prices abort a backtest.")
    return {
        "dataset_kind": metadata["kind"], "rows": len(prices), "symbols": int(prices["symbol"].nunique()),
        "first_date": str(calendar.min().date()), "last_date": str(calendar.max().date()),
        "calendar_sessions": len(calendar), "duplicate_keys": 0,
        "missing_eligible_rows": missing, "turnover_missing": int(prices["turnover"].isna().sum()),
        "unknown_status_rows": unknown,
        "blocked_buy_rows": int((~prices["can_buy"]).sum()),
        "blocked_sell_rows": int((~prices["can_sell"]).sum()), "limitations": warnings,
    }


def save_dataset(folder, prices, universe, calendar, metadata):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    prices[PRICE_COLUMNS].to_csv(folder / "prices.csv", index=False, date_format="%Y-%m-%d")
    universe.to_csv(folder / "universe.csv", index=False, date_format="%Y-%m-%d")
    pd.DataFrame({"date": calendar}).to_csv(folder / "calendar.csv", index=False, date_format="%Y-%m-%d")
    write_json(folder / "metadata.json", metadata)


def generate_demo(folder, seed=20261102, n_symbols=40):
    """Artificial OHLCV, not historical A shares. No promise of any factor premium."""
    rng = np.random.default_rng(seed)
    calendar = pd.bdate_range("2019-01-01", "2025-12-31")
    n = len(calendar)
    market = rng.normal(0.00015, 0.008, n)
    records = []
    for j in range(n_symbols):
        beta = rng.uniform(0.6, 1.3)
        daily = np.clip(beta * market + rng.normal(0, rng.uniform(0.008, 0.025), n), -0.12, 0.12)
        close = rng.uniform(10, 50) * np.cumprod(1 + daily)
        previous = np.r_[close[0] / (1 + daily[0]), close[:-1]]
        opening = previous * (1 + rng.normal(0, 0.003, n))
        high = np.maximum(opening, close) * (1 + rng.uniform(0.001, 0.015, n))
        low = np.minimum(opening, close) * (1 - rng.uniform(0.001, 0.015, n))
        volume = rng.lognormal(15, 0.4, n)
        can_buy = rng.random(n) > 0.012
        can_sell = rng.random(n) > 0.012
        # Synthetic suspension days carry an explicitly known valuation mark and no fills.
        suspended = rng.random(n) < 0.003
        for k in np.flatnonzero(suspended):
            mark = close[k - 1] if k else previous[k]
            opening[k] = close[k] = high[k] = low[k] = mark
        volume[suspended] = 0
        can_buy[suspended] = can_sell[suspended] = False
        records.append(pd.DataFrame({
            "date": calendar, "symbol": f"SYN{j+1:03d}", "open": opening, "high": high,
            "low": low, "close": close, "adj_open": opening, "adj_close": close,
            "volume": volume, "turnover": volume / 2e8,
            "can_buy": can_buy, "can_sell": can_sell, "status_known": True,
        }))
    prices = pd.concat(records, ignore_index=True).sort_values(["date", "symbol"])
    universe = prices[["date", "symbol"]].copy()
    universe["eligible"] = True
    metadata = {
        "kind": "synthetic", "source": "numpy.random.default_rng; artificial teaching fixture",
        "seed": seed, "n_symbols": n_symbols, "price_adjustment": "none; no corporate actions simulated",
        "universe": "synthetic fixed population known at start",
        "limitations": ["SIMULATED DATA: not A-share observations; no empirical investment conclusion is possible.",
                        "Calendar uses weekdays, including Chinese holidays; not an exchange calendar.",
                        "Artificial flags test blocked execution; they are not observed market events."],
    }
    save_dataset(folder, prices, universe, calendar, metadata)


def fetch_akshare(folder, symbols, start, end):
    """Fail atomically at the dataset level; preserve each successful source snapshot."""
    import akshare as ak

    if not symbols or any(not re.fullmatch(r"\d{6}", s) for s in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("symbols must be unique six-digit stock codes")
    folder = Path(folder)
    if (folder / "metadata.json").exists():
        raise ValueError("dataset already exists; use a new --out directory to preserve the input snapshot")
    raw_dir = folder / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for symbol in symbols:
        print(f"Downloading {symbol}: raw + hfq", flush=True)
        raw = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end, adjust="")
        adjusted = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end, adjust="hfq")
        if raw.empty or adjusted.empty:
            raise ValueError(f"empty provider response: {symbol}; no final dataset was written")
        raw.to_csv(raw_dir / f"{symbol}_raw.csv", index=False)
        adjusted.to_csv(raw_dir / f"{symbol}_hfq.csv", index=False)
        rename = {"日期": "date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume", "换手率": "turnover"}
        raw = raw.rename(columns=rename)
        adjusted = adjusted.rename(columns={"日期": "date", "开盘": "adj_open", "收盘": "adj_close"})
        if raw["date"].duplicated().any() or adjusted["date"].duplicated().any():
            raise ValueError(f"duplicate source dates: {symbol}")
        merged = raw.merge(adjusted[["date", "adj_open", "adj_close"]], on="date", validate="one_to_one", how="outer", indicator=True)
        if (merged["_merge"] != "both").any():
            raise ValueError(f"raw/adjusted sessions do not match: {symbol}")
        merged["date"] = pd.to_datetime(merged["date"])
        merged["symbol"] = symbol
        merged["volume"] = pd.to_numeric(merged["volume"]) * 100  # provider hands -> shares
        merged["turnover"] = pd.to_numeric(merged["turnover"]) / 100 if "turnover" in merged else np.nan
        merged["status_known"] = False  # daily bars cannot establish historical open auction tradability
        merged["can_buy"] = merged["can_sell"] = merged["volume"] > 0
        frames.append(merged[PRICE_COLUMNS])
    prices = pd.concat(frames, ignore_index=True)
    calendar_raw = ak.tool_trade_date_hist_sina()
    calendar_raw.to_csv(raw_dir / "calendar_source.csv", index=False)
    calendar = pd.DatetimeIndex(pd.to_datetime(calendar_raw["trade_date"]))
    calendar = calendar[(calendar >= pd.to_datetime(start)) & (calendar <= pd.to_datetime(end))].sort_values().unique()
    universe = pd.MultiIndex.from_product([calendar, symbols], names=["date", "symbol"]).to_frame(index=False)
    first = prices.groupby("symbol")["date"].min()
    universe["eligible"] = universe["date"] >= universe["symbol"].map(first)
    metadata = {
        "kind": "market_teaching_pool", "source": "AKShare stock_zh_a_hist / Eastmoney; tool_trade_date_hist_sina",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "akshare_version": importlib.metadata.version("akshare"), "symbols": symbols,
        "requested_start": start, "requested_end": end,
        "price_adjustment": "provider hfq adjusted open/close; raw OHLC also retained",
        "universe": "user-selected fixed teaching pool; not historical A-share index membership",
        "limitations": ["Fixed selected survivors may introduce survivorship and selection bias; cannot represent all A shares.",
                        "Historical ST, delisting, IPO exclusions and opening execution status are not supplied by this adapter.",
                        "can_buy/can_sell are volume-based assumptions, not verified historical limit/suspension flags.",
                        "Adjusted fractional units are an economic-return proxy; corporate-action cash flows and lots are not modeled."],
        "source_files": {p.name: sha256(p) for p in sorted(raw_dir.glob("*.csv"))},
    }
    validate_dataset(prices, universe, calendar)
    save_dataset(folder, prices, universe, calendar, metadata)


def write_database(path, prices, universe, calendar, factors, positions):
    """Typed source tables with enforced unique keys; derived tables remain queryable."""
    def serial(frame):
        frame = frame.copy()
        for col in ("date", "signal_date"):
            if col in frame:
                frame[col] = pd.to_datetime(frame[col]).dt.strftime("%Y-%m-%d")
        return frame

    with closing(sqlite3.connect(path)) as conn:
        serial(prices).to_sql("stock_prices", conn, if_exists="replace", index=False)
        serial(universe).to_sql("stock_universe", conn, if_exists="replace", index=False)
        pd.DataFrame({"date": calendar.strftime("%Y-%m-%d")}).to_sql("trading_calendar", conn, if_exists="replace", index=False)
        serial(factors).to_sql("factor_values", conn, if_exists="replace", index=False)
        serial(positions).to_sql("portfolio_positions", conn, if_exists="replace", index=False)
        for table in ("stock_prices", "stock_universe", "factor_values"):
            conn.execute(f"CREATE UNIQUE INDEX idx_{table} ON {table}(date,symbol)")
        conn.execute("CREATE UNIQUE INDEX idx_calendar ON trading_calendar(date)")
        conn.execute("CREATE UNIQUE INDEX idx_positions ON portfolio_positions(strategy,date,symbol)")
        conn.commit()
