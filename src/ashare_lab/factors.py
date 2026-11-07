"""Trailing price/volume factors and same-day cross-sectional normalization.

The raw factors use data available after each date's close.  Eligibility is
point-in-time and is applied only after the trailing histories are calculated.
No future return, future universe member or forward-filled price is used here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


FACTOR_NAMES = ("momentum", "volatility", "activity")
SCORE_COLUMNS = {
    "momentum": "z_momentum",
    "volatility": "z_volatility",
    "activity": "z_activity",
    "composite": "composite",
}


def _winsorized_zscore(values: pd.Series, mad_scale: float) -> pd.Series:
    """Clip at median +/- scale * 1.4826 MAD, then use population std.

    If MAD is zero, clipping is skipped rather than discarding every outlier.
    A constant cross-section has score zero.  Fewer than two valid values have
    no estimable cross-sectional dispersion and retain missing scores.
    """
    clean = values.replace([np.inf, -np.inf], np.nan).astype(float)
    valid = clean.dropna()
    result = pd.Series(np.nan, index=values.index, dtype=float)
    if len(valid) < 2:
        return result
    median = float(valid.median())
    mad = float((valid - median).abs().median())
    if mad > 0:
        distance = float(mad_scale) * 1.4826 * mad
        valid = valid.clip(median - distance, median + distance)
    std = float(valid.std(ddof=0))
    if std <= np.finfo(float).eps * max(1.0, abs(float(valid.mean()))):
        result.loc[valid.index] = 0.0
    else:
        result.loc[valid.index] = (valid - valid.mean()) / std
    return result


def compute_factors(
    prices: pd.DataFrame, universe: pd.DataFrame, config: dict
) -> pd.DataFrame:
    """Return daily raw factors, signed z-scores and an equal-weight score.

    ``prices`` requires date, symbol, adj_close, volume and turnover. ``universe``
    requires date, symbol and boolean eligible for each historical member date.
    The shared session calendar is config.calendar_dates when supplied, otherwise
    the union of price dates. Reindexing every stock to that calendar stops a missing observation from shortening a rolling
    window into a different number of market sessions. All input price history
    (including warmup before config.start) is retained for calculation.

    Momentum is P[t]/P[t-lookback]-1. Volatility is the sample standard deviation
    of the last lookback daily returns, without annualization. Activity is mean
    turnover over lookback sessions, or mean short volume / mean long volume.
    Every raw factor must exist for the composite to exist.
    """
    required = {"date", "symbol", "adj_close", "volume", "turnover"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Missing price columns for factors: {sorted(missing)}")
    if not {"date", "symbol", "eligible"}.issubset(universe.columns):
        raise ValueError("Universe requires date, symbol, eligible")
    lookback = int(config.get("lookback", 20))
    short = int(config.get("activity_short", 5))
    long = int(config.get("activity_long", 20))
    if lookback < 2 or short < 1 or long < short:
        raise ValueError("Require lookback >= 2 and 1 <= activity_short <= activity_long")
    mode = config.get("activity_mode", "relative_volume")
    if mode not in {"relative_volume", "turnover"}:
        raise ValueError("activity_mode must be relative_volume or turnover")
    mad_scale = float(config.get("mad_scale", 3.0))
    if mad_scale <= 0:
        raise ValueError("mad_scale must be positive")
    directions = config.get(
        "directions", {"momentum": 1, "volatility": -1, "activity": -1}
    )
    if set(directions) != set(FACTOR_NAMES) or any(
        directions[name] not in (-1, 1) for name in FACTOR_NAMES
    ):
        raise ValueError("directions must assign +1 or -1 to all three factors")

    frame = prices.copy()
    members = universe.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    members["date"] = pd.to_datetime(members["date"])
    if frame.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate price date/symbol keys")
    if members.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate universe date/symbol keys")
    calendar = pd.DatetimeIndex(pd.to_datetime(
        config.get("calendar_dates", sorted(frame["date"].unique()))
    )).drop_duplicates().sort_values()
    if not frame["date"].isin(calendar).all():
        raise ValueError("Price dates outside configured trading calendar")
    columns = ["date", "symbol", *FACTOR_NAMES,
               "z_momentum", "z_volatility", "z_activity", "composite"]
    if len(calendar) == 0:
        return pd.DataFrame(columns=columns)

    histories = []
    for symbol, stock in frame.groupby("symbol", sort=True):
        stock = stock.set_index("date").sort_index().reindex(calendar)
        close = pd.to_numeric(stock["adj_close"], errors="coerce")
        close = close.where(close > 0)
        returns = close.pct_change(fill_method=None)
        # A complete price path also makes corruption/missing sessions explicit.
        complete = close.rolling(lookback + 1, min_periods=lookback + 1).count()
        momentum = (close / close.shift(lookback) - 1).where(complete == lookback + 1)
        volatility = returns.rolling(lookback, min_periods=lookback).std(ddof=1)
        if mode == "turnover":
            turnover = pd.to_numeric(stock["turnover"], errors="coerce")
            activity = turnover.where(turnover >= 0).rolling(
                lookback, min_periods=lookback
            ).mean()
        else:
            volume = pd.to_numeric(stock["volume"], errors="coerce")
            volume = volume.where(volume >= 0)
            denominator = volume.rolling(long, min_periods=long).mean()
            activity = volume.rolling(short, min_periods=short).mean() / denominator.where(
                denominator > 0
            )
        histories.append(pd.DataFrame({
            "date": calendar,
            "symbol": symbol,
            "momentum": momentum.to_numpy(),
            "volatility": volatility.to_numpy(),
            "activity": activity.to_numpy(),
        }))
    result = pd.concat(histories, ignore_index=True)
    members = members.loc[members["eligible"].eq(True), ["date", "symbol"]]
    result = result.merge(members, on=["date", "symbol"], how="inner", validate="one_to_one")
    result = result.sort_values(["date", "symbol"]).reset_index(drop=True)
    for name in FACTOR_NAMES:
        signed = result[name] * int(directions[name])
        result[f"z_{name}"] = signed.groupby(result["date"], group_keys=False).transform(
            lambda values: _winsorized_zscore(values, mad_scale)
        )
    zcols = [f"z_{name}" for name in FACTOR_NAMES]
    result["composite"] = result[zcols].mean(axis=1).where(result[zcols].notna().all(axis=1))
    return result[columns]


def monthly_signal_dates(calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Month's final known session with an available next execution session.

    The supplied calendar must be a verified market calendar for real research.
    The final available date is excluded because next-session execution is not
    possible. A truncated final month is therefore never treated as month-end.
    """
    days = pd.DatetimeIndex(pd.to_datetime(calendar)).drop_duplicates().sort_values()
    if len(days) < 2:
        return pd.DatetimeIndex([])
    ends = pd.Series(days, index=days).groupby(days.to_period("M")).last()
    return pd.DatetimeIndex(ends[ends < days[-1]].to_numpy())
