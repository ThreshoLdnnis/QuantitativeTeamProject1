"""Reproducible experiment entry points; no automatic selection of winning rules."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd

from . import __version__
from .backtest import metrics, run_backtest
from .config import load_config
from .data import data_quality, fetch_akshare, generate_demo, load_dataset, sha256, write_database, write_json
from .factors import compute_factors
from .research import analyze_factors


def run_pipeline(data_dir, config_path, out_dir, allow_unknown_status=False):
    cfg = load_config(config_path)
    prices, universe, calendar, metadata = load_dataset(data_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg["allow_unknown_status"] = bool(allow_unknown_status)
    quality = data_quality(prices, universe, calendar, metadata)
    active_study = universe.loc[universe["eligible"] & universe["date"].between(pd.Timestamp(cfg["start"]), pd.Timestamp(cfg["end"])), ["date", "symbol"]]
    coverage = active_study.merge(prices[["date", "symbol"]], on=["date", "symbol"], how="left", indicator=True)
    quality["missing_eligible_rows_in_study"] = int((coverage["_merge"] == "left_only").sum())
    quality["study_start"] = cfg["start"]
    quality["study_end"] = cfg["end"]
    write_json(out / "data_quality.json", quality)
    if quality["unknown_status_rows"] and not allow_unknown_status:
        raise ValueError("历史成交状态未核实。补齐 can_buy/can_sell/status_known，或明确使用 --allow-unknown-status 教学假设。详见 data_quality.json。")
    available = calendar[(calendar >= pd.Timestamp(cfg["start"])) & (calendar <= pd.Timestamp(cfg["end"]))]
    if len(available) < 30:
        raise ValueError("研究区间不足30个交易日；检查配置与数据日期")
    # Refuse a silently shortened experiment interval. Weekends/holidays allow up to 10 calendar days.
    if (available[0] - pd.Timestamp(cfg["start"])).days > 10 or (pd.Timestamp(cfg["end"]) - available[-1]).days > 10:
        raise ValueError("实际数据未覆盖配置区间；缩短并冻结 config 区间后再运行")
    observed = pd.DatetimeIndex(prices["date"].unique())
    if not available.isin(observed).all():
        raise ValueError("研究区间存在全股票缺失的交易日，不能用现金净值掩盖行情缺口")
    write_json(out / "config_snapshot.json", cfg)
    working = deepcopy(cfg)
    working["calendar_dates"] = calendar.strftime("%Y-%m-%d").tolist()
    print("1/5 Compute trailing factors and cross-sectional scores", flush=True)
    factors = compute_factors(prices, universe, working)
    factors.to_csv(out / "factors.csv", index=False, date_format="%Y-%m-%d")
    print("2/5 Analyze complete next-open labels and temporal splits", flush=True)
    research = analyze_factors(prices, factors, calendar, working)
    for name, frame in research.items():
        frame.to_csv(out / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    print("3/5 Run benchmark, individual factors and composite", flush=True)
    strategies = {"benchmark": None, "momentum": "z_momentum", "volatility": "z_volatility",
                  "activity": "z_activity", "multifactor": "composite"}
    results = {}
    for name, score in strategies.items():
        print(f"  {name}", flush=True)
        results[name] = run_backtest(prices, factors, calendar, working, score_column=score)
    for multiplier in cfg["cost_multipliers"]:
        if multiplier == 1:
            continue
        scenario = dict(working, cost_multiplier=multiplier)
        name = f"multifactor_cost{multiplier:g}"
        print(f"  {name}", flush=True)
        results[name] = run_backtest(prices, factors, calendar, scenario)
    metric_rows, position_frames = [], []
    for name, result in results.items():
        for field in ("daily", "trades", "positions", "orders"):
            getattr(result, field).to_csv(out / f"{field}_{name}.csv", index=False, date_format="%Y-%m-%d")
        position_frames.append(result.positions.assign(strategy=name))
        for split, bounds in {"all": [cfg["start"], cfg["end"]], **cfg["splits"]}.items():
            a, b = map(pd.Timestamp, bounds)
            block = result.daily.loc[result.daily["date"].between(a, b)]
            base = results["benchmark"].daily
            base = base.loc[base["date"].between(a, b)]
            values = metrics(block, cfg.get("annual_risk_free", 0))
            base_values = metrics(base, cfg.get("annual_risk_free", 0))
            relative = (1 + values["total_return"]) / (1 + base_values["total_return"]) - 1
            metric_rows.append(dict(strategy=name, split=split, n_days=len(block), **values, relative_return=relative))
    metrics_frame = pd.DataFrame(metric_rows)
    metrics_frame.to_csv(out / "metrics.csv", index=False)
    print("4/5 Persist queryable SQLite tables and evidence manifest", flush=True)
    positions = pd.concat(position_frames, ignore_index=True)
    write_database(out / "research.sqlite", prices, universe, calendar, factors, positions)
    source_dir = Path(__file__).parent
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": metadata, "package_version": __version__, "python": platform.python_version(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "pandas")},
        "input_files": {name: sha256(Path(data_dir) / name) for name in ("prices.csv", "universe.csv", "calendar.csv", "metadata.json")},
        "config_sha256": sha256(out / "config_snapshot.json"),
        "code_sha256": {p.name: sha256(p) for p in sorted(source_dir.glob("*.py"))},
        "metrics_sha256": sha256(out / "metrics.csv"),
        "claims": "Engineering baseline only; no automatic claim of factor validity or statistical significance.",
    }
    write_json(out / "manifest.json", manifest)
    print("5/5 Build self-contained report", flush=True)
    from .report import write_report
    write_report(out / "report.html", metadata, quality, cfg, research, results, metrics_frame)
    print(f"完成: {(out / 'report.html').resolve()}", flush=True)
    return results, research, metrics_frame


def build_parser():
    parser = argparse.ArgumentParser(description="A股多因子研究教学基线：数据、因子、检验、回测、报告")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="生成明确标注的模拟数据并运行全流程")
    demo.add_argument("--config", default="configs/baseline.json")
    demo.add_argument("--out", default="runs/demo")
    demo.add_argument("--seed", type=int, default=20261102)
    demo.add_argument("--symbols", type=int, default=40)
    fetch = sub.add_parser("fetch", help="通过 AKShare 下载手工指定的固定教学股票池")
    fetch.add_argument("--symbols", required=True, help="逗号分隔的六位代码")
    fetch.add_argument("--start", default="20190101")
    fetch.add_argument("--end", default="20251231")
    fetch.add_argument("--out", default="data/market")
    run = sub.add_parser("run", help="运行既有CSV数据快照")
    run.add_argument("--data", required=True)
    run.add_argument("--config", default="configs/baseline.json")
    run.add_argument("--out", default="runs/market")
    run.add_argument("--allow-unknown-status", action="store_true", help="显式接受历史可成交状态未知的教学假设")
    check = sub.add_parser("check-data", help="只校验CSV并打印数据质量，不回测")
    check.add_argument("--data", required=True)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        if args.command == "demo":
            if args.symbols < 5:
                raise ValueError("demo 至少需要5只模拟股票")
            data_dir = Path(args.out) / "input"
            generate_demo(data_dir, args.seed, args.symbols)
            run_pipeline(data_dir, args.config, args.out)
        elif args.command == "fetch":
            fetch_akshare(args.out, args.symbols.split(","), args.start, args.end)
            print(f"完成数据快照: {Path(args.out).resolve()}")
        elif args.command == "run":
            run_pipeline(args.data, args.config, args.out, args.allow_unknown_status)
        else:
            prices, universe, calendar, meta = load_dataset(args.data)
            print(json.dumps(data_quality(prices, universe, calendar, meta), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, ImportError) as exc:
        print(f"失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
