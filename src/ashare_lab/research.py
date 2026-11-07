"""Factor diagnostics with explicit next-open labels and temporal split purging.

These are theoretical gross forward-return diagnostics. Execution constraints,
transaction costs and realized portfolio accounting belong to the backtester.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from .factors import SCORE_COLUMNS, monthly_signal_dates


LABEL_COLUMNS = ["date", "entry_date", "exit_date", "symbol", "forward_return", "split"]
IC_COLUMNS = ["date", "factor", "ic", "n", "split"]
SUMMARY_COLUMNS = ["split", "factor", "n", "mean_ic", "ic_std", "icir", "hac_tstat", "hac_lags"]
GROUP_COLUMNS = ["date", "factor", "group", "forward_return", "n", "split"]
CORRELATION_COLUMNS = ["date", "factor_a", "factor_b", "correlation", "n", "split"]


def _split_for_dates(signal: pd.Timestamp, entry: pd.Timestamp,
                     exit_: pd.Timestamp, config: dict) -> str | None:
    """Purge a label unless its signal, entry and exit share one declared split."""
    for name, bounds in config.get("splits", {}).items():
        begin, end = pd.Timestamp(bounds[0]), pd.Timestamp(bounds[1])
        if begin <= signal <= entry <= exit_ <= end:
            return str(name)
    return None


def build_forward_labels(prices: pd.DataFrame, factors: pd.DataFrame,
                         calendar: pd.DatetimeIndex, config: dict) -> pd.DataFrame:
    """Return complete next-open to next-rebalance-open labels.

    Stocks are drawn from factor rows at the signal date, never from future
    membership. A missing/invalid entry or exit quote removes that label; no
    return is manufactured by filling a missing price. Tradeability flags are
    intentionally not applied: these diagnostics measure gross theoretical
    return, and are distinct from executable strategy returns.
    """
    days = pd.DatetimeIndex(pd.to_datetime(calendar)).drop_duplicates().sort_values()
    signals = monthly_signal_dates(days)
    if len(signals) < 2:
        return pd.DataFrame(columns=LABEL_COLUMNS)
    frame = prices.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    if frame.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate price date/symbol keys")
    factor_keys = factors[["date", "symbol"]].copy()
    factor_keys["date"] = pd.to_datetime(factor_keys["date"])
    if factor_keys.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate factor date/symbol keys")
    open_prices = frame.set_index(["date", "symbol"])["adj_open"]
    lower = pd.Timestamp(config.get("start", days[0]))
    upper = pd.Timestamp(config.get("end", days[-1]))
    rows = []
    for signal, next_signal in zip(signals[:-1], signals[1:]):
        if signal < lower or signal > upper:
            continue
        entry = days[days.get_loc(signal) + 1]
        exit_ = days[days.get_loc(next_signal) + 1]
        if exit_ > upper:
            continue
        split = _split_for_dates(signal, entry, exit_, config)
        if split is None:
            continue
        symbols = factor_keys.loc[factor_keys["date"].eq(signal), "symbol"]
        for symbol in symbols:
            start_price = open_prices.get((entry, symbol), np.nan)
            end_price = open_prices.get((exit_, symbol), np.nan)
            if not (np.isfinite(start_price) and np.isfinite(end_price)
                    and start_price > 0 and end_price > 0):
                continue
            rows.append((signal, entry, exit_, symbol, end_price / start_price - 1.0, split))
    return pd.DataFrame(rows, columns=LABEL_COLUMNS)


def _rank_correlation(x: pd.Series, y: pd.Series) -> float:
    """Spearman correlation with average ties, without a SciPy dependency."""
    if x.nunique() < 2 or y.nunique() < 2:
        return np.nan
    return float(x.rank(method="average").corr(y.rank(method="average")))


def _hac_mean_tstat(values: pd.Series, max_lags: int = 3) -> tuple[float, int]:
    """Newey-West/Bartlett mean t-statistic; no small-sample p-value claim."""
    data = values.dropna().to_numpy(dtype=float)
    n = len(data)
    lag = min(max_lags, max(0, n - 1))
    if n < 2:
        return np.nan, lag
    centered = data - data.mean()
    long_run_variance = float(centered @ centered / n)
    for k in range(1, lag + 1):
        covariance = float(centered[k:] @ centered[:-k] / n)
        long_run_variance += 2.0 * (1.0 - k / (lag + 1.0)) * covariance
    if long_run_variance <= np.finfo(float).eps:
        return np.nan, lag
    return float(data.mean() / np.sqrt(long_run_variance / n)), lag


def analyze_factors(prices: pd.DataFrame, factors: pd.DataFrame,
                    calendar: pd.DatetimeIndex, config: dict) -> dict[str, pd.DataFrame]:
    """Return labels, ICs, split summaries, group returns and correlations.

    Dict keys are ``labels``, ``ic``, ``ic_summary``, ``groups`` and
    ``correlation``. The three individual factors use signed standardized scores
    (higher always means the predeclared preferred direction); composite is the
    fixed equal-weight score. Rank IC needs >=5 valid stocks. ICIR is mean IC /
    sample std of IC and is not annualized. HAC t-statistics use up to 3 monthly
    lags and are descriptive; short samples do not establish significance.

    Groups are numbered from low to high signed score. Average-rank boundaries
    keep tied stocks together. A constant score has no grouping information and
    is skipped; ties can result in fewer nonempty groups than requested.
    """
    labels = build_forward_labels(prices, factors, calendar, config)
    groups_requested = int(config.get("groups", 5))
    if groups_requested < 2:
        raise ValueError("groups must be >= 2")
    factor_data = factors.copy()
    factor_data["date"] = pd.to_datetime(factor_data["date"])
    merged = labels.merge(factor_data, on=["date", "symbol"], how="inner", validate="one_to_one")
    ic_rows, group_rows, correlation_rows = [], [], []
    for (date, split), cross_section in merged.groupby(["date", "split"], sort=True):
        for name, column in SCORE_COLUMNS.items():
            valid = cross_section[[column, "forward_return"]].replace(
                [np.inf, -np.inf], np.nan
            ).dropna()
            n = len(valid)
            ic = _rank_correlation(valid[column], valid["forward_return"]) if n >= 5 else np.nan
            ic_rows.append((date, name, ic, n, split))
            if n < 2 or valid[column].nunique() < 2:
                continue
            count = min(groups_requested, n)
            rank = valid[column].rank(method="average")
            bucket = np.floor((rank - 1.0) * count / n).astype(int) + 1
            for group, selection in valid.groupby(bucket, sort=True):
                group_rows.append((date, name, int(group),
                                   float(selection["forward_return"].mean()), len(selection), split))
        for (left_name, left), (right_name, right) in combinations(SCORE_COLUMNS.items(), 2):
            valid = cross_section[[left, right]].replace([np.inf, -np.inf], np.nan).dropna()
            value = _rank_correlation(valid[left], valid[right]) if len(valid) >= 2 else np.nan
            correlation_rows.append((date, left_name, right_name, value, len(valid), split))

    ic_frame = pd.DataFrame(ic_rows, columns=IC_COLUMNS)
    summaries = []
    for (split, factor), block in ic_frame.groupby(["split", "factor"], sort=True):
        values = block["ic"].dropna()
        std = float(values.std(ddof=1)) if len(values) >= 2 else np.nan
        mean = float(values.mean()) if len(values) else np.nan
        icir = mean / std if np.isfinite(std) and std > np.finfo(float).eps else np.nan
        tstat, lags = _hac_mean_tstat(values)
        summaries.append((split, factor, len(values), mean, std, icir, tstat, lags))
    return {
        "labels": labels,
        "ic": ic_frame,
        "ic_summary": pd.DataFrame(summaries, columns=SUMMARY_COLUMNS),
        "groups": pd.DataFrame(group_rows, columns=GROUP_COLUMNS),
        "correlation": pd.DataFrame(correlation_rows, columns=CORRELATION_COLUMNS),
    }
