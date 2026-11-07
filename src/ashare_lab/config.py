"""Explicit frozen experiment rules; no optimizer or test-set tuning."""
import json
import math
from pathlib import Path

import pandas as pd


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("lookback", "activity_short", "activity_long", "top_n", "groups"):
        if not isinstance(cfg[key], int) or cfg[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if cfg["lookback"] < 2 or cfg["activity_short"] > cfg["activity_long"]:
        raise ValueError("invalid rolling windows")
    if cfg["activity_mode"] not in {"relative_volume", "turnover"}:
        raise ValueError("activity_mode must be relative_volume or turnover")
    if set(cfg["directions"]) != {"momentum", "volatility", "activity"}:
        raise ValueError("specify all three factor directions")
    if any(x not in (-1, 1) for x in cfg["directions"].values()):
        raise ValueError("factor directions must be +1 or -1")
    if cfg["groups"] < 2:
        raise ValueError("groups must be at least two")
    for key in ("commission_bps", "slippage_bps", "sell_tax_bps", "mad_scale"):
        if not math.isfinite(cfg[key]) or not 0 <= cfg[key] < 10000:
            raise ValueError(f"invalid {key}")
    if cfg["mad_scale"] <= 0:
        raise ValueError("mad_scale must be positive")
    if not math.isfinite(cfg["initial_cash"]) or cfg["initial_cash"] <= 0:
        raise ValueError("initial_cash must be positive")
    if not cfg["cost_multipliers"] or any(not math.isfinite(x) or x < 0 for x in cfg["cost_multipliers"]):
        raise ValueError("cost_multipliers must be non-negative")
    start, end = pd.Timestamp(cfg["start"]), pd.Timestamp(cfg["end"])
    if pd.isna(start) or pd.isna(end) or start >= end:
        raise ValueError("start must precede end")
    previous = None
    for name, bounds in cfg["splits"].items():
        a, b = map(pd.Timestamp, bounds)
        if pd.isna(a) or pd.isna(b) or a > b or a < start or b > end or (previous is not None and a <= previous):
            raise ValueError(f"invalid or overlapping chronological split: {name}")
        previous = b
    return cfg
