r"""第十八课：真实 A 股快照接入、数据核对与教学成交回放。

运行：.\.venv\Scripts\python.exe examples/18_real_market_data.py
复现已保存的真实历史快照；行情完整不等于历史成交状态已经核实。
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

from ashare_lab.cli import run_pipeline
from ashare_lab.config import load_config
from ashare_lab.data import data_quality, load_dataset, sha256, write_json


def verify_source_files(data_dir, metadata):
    """原始响应哈希匹配只证明快照未变，不证明供应商数据绝对正确。"""
    rows = []
    for name, expected in metadata["source_files"].items():
        actual = sha256(data_dir / "raw" / name)
        rows.append(dict(file=name, expected_sha256=expected, actual_sha256=actual, matches=actual == expected))
    checks = pd.DataFrame(rows)
    if checks.empty or not checks["matches"].all():
        raise ValueError("原始响应与 metadata 中保存的哈希不一致，停止复现。")
    return checks


def verify_normalization(data_dir, prices, metadata):
    """逐只复核原价、后复权价及单位转换，保留六位字符串代码。"""
    checks = []
    for symbol in metadata["symbols"]:
        raw = pd.read_csv(data_dir / "raw" / f"{symbol}_raw.csv",
                          dtype={"股票代码": str}, parse_dates=["日期"]).set_index("日期").sort_index()
        adjusted = pd.read_csv(data_dir / "raw" / f"{symbol}_hfq.csv",
                               dtype={"股票代码": str}, parse_dates=["日期"]).set_index("日期").sort_index()
        normalized = prices.loc[prices["symbol"].eq(symbol)].set_index("date").sort_index()
        pd.testing.assert_index_equal(raw.index, adjusted.index, check_names=False)
        pd.testing.assert_index_equal(raw.index, normalized.index, check_names=False)

        expected = pd.DataFrame(index=raw.index)
        for english, chinese in [("open", "开盘"), ("high", "最高"), ("low", "最低"), ("close", "收盘")]:
            expected[english] = raw[chinese]
        expected["adj_open"] = adjusted["开盘"]
        expected["adj_close"] = adjusted["收盘"]
        expected["volume"] = raw["成交量"] * 100
        expected["turnover"] = raw["换手率"] / 100
        np.testing.assert_allclose(normalized[expected.columns], expected, rtol=0, atol=1e-8)
        np.testing.assert_array_equal(normalized["can_buy"], normalized["volume"] > 0)
        np.testing.assert_array_equal(normalized["can_sell"], normalized["volume"] > 0)
        if normalized["status_known"].any():
            raise ValueError("这份快照的成交状态应保持未知；不能伪装成已核实。")
        errors = (normalized[expected.columns] - expected).abs().max()
        checks.append(dict(symbol=symbol, rows=len(normalized), raw_adjusted_dates_match=True,
                           max_price_error=float(errors[["open", "high", "low", "close", "adj_open", "adj_close"]].max()),
                           max_volume_error=float(errors["volume"]), max_turnover_error=float(errors["turnover"])))
    return pd.DataFrame(checks)


def inspect_coverage(prices, universe, calendar, metadata, config):
    """同时报告全笛卡尔缺口与当前 eligible 定义下的缺口。"""
    full_grid = pd.MultiIndex.from_product([calendar, metadata["symbols"]],
                                            names=["date", "symbol"]).to_frame(index=False)
    coverage = full_grid.merge(universe, on=["date", "symbol"], how="left", validate="one_to_one")
    if coverage["eligible"].isna().any():
        raise ValueError("股票池定义缺少日期/股票记录，不能默认为合格。")
    coverage = coverage.merge(prices[["date", "symbol"]], on=["date", "symbol"],
                               how="left", validate="one_to_one", indicator=True)
    coverage["missing"] = coverage["_merge"].eq("left_only")
    coverage["missing_eligible"] = coverage["missing"] & coverage["eligible"]
    coverage["in_study"] = coverage["date"].between(config["start"], config["end"])
    missing = coverage.loc[coverage["missing"], ["date", "symbol", "eligible", "in_study"]].copy()
    yearly = coverage.assign(year=coverage["date"].dt.year).groupby("year").agg(
        expected_fixed_pool_rows=("symbol", "size"), eligible_rows=("eligible", "sum"),
        missing_fixed_pool_rows=("missing", "sum"), missing_eligible_rows=("missing_eligible", "sum"),
    ).reset_index()
    study = coverage.loc[coverage["in_study"]]
    if study["missing"].any():
        raise ValueError("既定研究区间存在股票/日期行情缺口，停止；不填价后继续。")
    if not study["eligible"].all():
        raise ValueError("本课既定区间应完整覆盖固定教学池，请先核对资格定义。")
    return missing, yearly, int(len(study))


def audit_results(results, output_dir):
    rows = []
    for name, result in results.items():
        daily = result.daily
        invested = result.positions.groupby("date")["market_value"].sum()
        error = daily["equity"] - daily["cash"] - daily["date"].map(invested).fillna(0)
        np.testing.assert_allclose(error, 0, rtol=0, atol=1e-7)
        assert (daily["cash"] >= 0).all()
        assert (result.trades["date"] > result.trades["signal_date"]).all()
        np.testing.assert_allclose((1 + daily["return"]).cumprod(skipna=False), daily["nav"], rtol=0, atol=1e-10)
        np.testing.assert_allclose(daily["cost"].sum(),
                                   result.trades[["commission", "tax", "slippage_cost"]].sum().sum(),
                                   rtol=0, atol=1e-7)
        rows.append(dict(strategy=name, daily_rows=len(daily), trade_count=len(result.trades),
                         max_equity_identity_error=float(error.abs().max()),
                         rejected_orders=int(result.orders["status"].eq("rejected").sum()),
                         fills_after_signal=True, costs_reconcile=True))
    pd.DataFrame(rows).to_csv(output_dir / "accounting_audit.csv", index=False)


def plot_market(results, output_path):
    """展示行情驱动的教学回放；不将假设成交标成已验证的实际成交。"""
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    fig, (ax_nav, ax_dd) = plt.subplots(2, 1, figsize=(11.5, 7.6), sharex=True,
                                       gridspec_kw={"height_ratios": [2, 1]}, layout="constrained")
    fig.suptitle("固定 30 股池：真实行情教学回放（2023—2025）", fontsize=17)
    ax_nav.set_title("后复权价格小数单位；成交状态未核实，采用教学假设；1 倍固定教学费用",
                     loc="left", fontsize=10, pad=12)
    nav_min, nav_max, dd_min = 1.0, 1.0, 0.0
    for key, color, line, label in [("multifactor", "#3268A8", "-", "三因子策略"),
                                     ("benchmark", "#747D86", "--", "同池等权基准")]:
        daily = results[key].daily
        peak = daily["nav"].cummax(skipna=False).clip(lower=1)
        drawdown = daily["nav"] / peak - 1
        ax_nav.plot(daily["date"], daily["nav"], color=color, linestyle=line, linewidth=1.5,
                     label=f"{label}（累计 {daily['nav'].iloc[-1] - 1:+.2%}）")
        ax_dd.plot(daily["date"], drawdown, color=color, linestyle=line, linewidth=1.3,
                    label=f"{label}（最大回撤幅度 {-drawdown.min():.2%}）")
        nav_min = min(nav_min, daily["nav"].min())
        nav_max = max(nav_max, daily["nav"].max())
        dd_min = min(dd_min, drawdown.min())
    ax_nav.set_ylim(nav_min - 0.04, nav_max + 0.13)
    ax_nav.axhline(1, color="#9FA6AD", linewidth=0.8, linestyle=":")
    ax_nav.set_ylabel("净值（初始资金 = 1）")
    ax_dd.set_ylim(dd_min - 0.025, 0.055)
    ax_dd.axhline(0, color="#9FA6AD", linewidth=0.8)
    ax_dd.set_ylabel("相对历史高点的回撤")
    ax_dd.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    dates = results["multifactor"].daily["date"]
    # 显示首尾和年度分界；元旦刻度只是时间轴标签，不表示当天开市。
    ticks = pd.DatetimeIndex([dates.iloc[0], pd.Timestamp("2024-01-01"),
                              pd.Timestamp("2025-01-01"), dates.iloc[-1]])
    ax_dd.set_xticks(ticks)
    ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax_dd.set_xlim(dates.iloc[0] - pd.Timedelta(days=10), dates.iloc[-1] + pd.Timedelta(days=10))
    ax_dd.set_xlabel("日期（供应商历史交易日历；期末仍持仓，按收盘估值）")
    for ax in (ax_nav, ax_dd):
        ax.legend(loc="upper left", frameon=False, fontsize=10)
        ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
        for boundary in [pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")]:
            ax.axvline(boundary, color="#DCE2E8", linewidth=0.8, linestyle=":")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main():
    project_dir = Path(__file__).resolve().parents[1]
    data_dir = project_dir / "data" / "market_teaching"
    config_path = project_dir / "configs" / "market_teaching.json"
    output_dir = project_dir / "runs" / "lesson18_real_market"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 使用已保存的真实原始响应与规范化快照，保留取数日期和版本。
    prices, universe, calendar, metadata = load_dataset(data_dir)
    config = load_config(config_path)
    if metadata["kind"] != "market_teaching_pool":
        raise ValueError("本课需要真实行情教学池。")
    input_hashes = {name: sha256(data_dir / name) for name in ["prices.csv", "universe.csv", "calendar.csv", "metadata.json"]}
    source_checks = verify_source_files(data_dir, metadata)
    normalization_checks = verify_normalization(data_dir, prices, metadata)

    # 2. 核对独立保存的供应商历史日历，不用普通工作日生成交易日历。
    raw_calendar = pd.read_csv(data_dir / "raw" / "calendar_source.csv", parse_dates=["trade_date"])
    source_calendar = pd.DatetimeIndex(raw_calendar["trade_date"])
    source_calendar = source_calendar[(source_calendar >= pd.Timestamp(metadata["requested_start"])) &
                                       (source_calendar <= pd.Timestamp(metadata["requested_end"]))].sort_values().unique()
    pd.testing.assert_index_equal(calendar, source_calendar, check_names=False)

    # 3. 沿用此前已冻结的 2023—2025 年区间，先查覆盖，再计算绩效。
    missing, yearly, expected_study_rows = inspect_coverage(prices, universe, calendar, metadata, config)
    quality = data_quality(prices, universe, calendar, metadata)
    study_prices = prices.loc[prices["date"].between(config["start"], config["end"])]
    study_calendar = calendar[(calendar >= pd.Timestamp(config["start"])) & (calendar <= pd.Timestamp(config["end"]))]
    quality.update(dict(full_fixed_grid_rows=len(calendar) * len(metadata["symbols"]),
                        full_fixed_grid_missing_rows=len(missing),
                        study_start=config["start"], study_end=config["end"],
                        study_sessions=len(study_calendar), study_price_rows=len(study_prices),
                        expected_study_rows=expected_study_rows, missing_eligible_rows_in_study=0,
                        unknown_status_rows_in_study=int((~study_prices["status_known"]).sum()),
                        verified_raw_files=len(source_checks)))
    write_json(output_dir / "data_quality.json", quality)
    source_checks.to_csv(output_dir / "source_hash_checks.csv", index=False)
    normalization_checks.to_csv(output_dir / "normalization_checks.csv", index=False)
    missing.to_csv(output_dir / "missing_fixed_pool_rows.csv", index=False, date_format="%Y-%m-%d")
    yearly.to_csv(output_dir / "yearly_coverage.csv", index=False)
    prices.loc[prices["symbol"].eq("000001")].head(6).to_csv(output_dir / "sample_000001.csv", index=False, date_format="%Y-%m-%d")
    print(f"预检通过：{len(prices)} 行、{prices['symbol'].nunique()} 股；研究区间 {len(study_calendar)} 日、{len(study_prices)} 行。", flush=True)
    print(f"完整固定池缺口 {len(missing)}，其中 eligible 缺口 {quality['missing_eligible_rows']}；研究区间缺口 0。", flush=True)
    print("成交状态未核实，下面显式采用教学成交假设；原始 status_known 保持 False。", flush=True)

    # 4. 同一条研究流水线：因子、IC/分组、基准/策略/成本、SQLite 与报告。
    results, research, metric_table = run_pipeline(
        data_dir, config_path, output_dir / "experiment", allow_unknown_status=True,
    )

    # 5. 核对账户和输入快照，保存主要结果与边界。
    audit_results(results, output_dir)
    assert input_hashes == {name: sha256(data_dir / name) for name in input_hashes}
    selected = metric_table.loc[metric_table["strategy"].isin(["multifactor", "benchmark"])].copy()
    selected["max_drawdown_amplitude"] = -selected["max_drawdown"]
    selected.to_csv(output_dir / "strategy_benchmark_metrics.csv", index=False)
    write_json(output_dir / "methodology.json", dict(
        data_source=metadata["source"], retrieved_at_utc=metadata["retrieved_at_utc"],
        stored_akshare_version=metadata["akshare_version"], symbols=metadata["symbols"],
        study_config=str(config_path), study_start=config["start"], study_end=config["end"],
        snapshot_input_sha256=input_hashes,
        coverage=dict(full_fixed_grid_missing_rows=len(missing),
                      missing_eligible_rows=quality["missing_eligible_rows"],
                      missing_eligible_rows_in_study=quality["missing_eligible_rows_in_study"]),
        eligibility="starts at first observed source row, not independently verified listing/IPO eligibility",
        execution="allow_unknown_status=True; volume-positive assumed can_buy/can_sell, not verified historical open tradability",
        universe="30 manually fixed selected survivors, not historical A-share population or index members",
        adjustment="provider hfq open and close directly; fractional adjusted units, not exchange share ledger",
        evaluation="replication of already-viewed snapshot and fixed years, not a new untouched holdout",
        fees="fixed teaching assumptions, not a historical tax/fee schedule",
        prior_failure="2020-2025 attempt stopped: missing held price 600009 on 2021-06-10; see runs/failed_2020_2025.json",
        terminal_valuation="last close, without hypothetical liquidation",
        official_api_reference="https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock_quote.md",
    ))
    plot_market(results, output_dir / "real_market_nav_drawdown.png")
    print("\n策略与基准结果（收益以小数存储；max_drawdown_amplitude 为正幅度）：")
    print(selected[["strategy", "split", "n_days", "total_return", "annual_return",
                    "annual_volatility", "max_drawdown_amplitude", "relative_return"]].to_string(index=False))
    print("\n本课结果目录：", output_dir)


if __name__ == "__main__":
    main()
