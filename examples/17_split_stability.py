r"""第十七课：连续账户的事后分段稳定性检查。

运行：.\.venv\Scripts\python.exe examples/17_split_stability.py
读取第十六课 1 倍成本结果，不重新清仓、注资或调参。
"""

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

from ashare_lab.backtest import metrics
from ashare_lab.config import load_config
from ashare_lab.data import write_json


SPLIT_LABELS = {"development": "开发期", "validation": "验证期", "test": "测试期"}


def read_continuous_account(path, initial_cash, expected_dates):
    """检查账户收益以初始资金/前一日权益为基准；不填补缺失日收益。"""
    daily = pd.read_csv(path, parse_dates=["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    if daily.empty or daily["date"].duplicated().any():
        raise ValueError("账户记录为空或日期重复。")
    pd.testing.assert_index_equal(pd.DatetimeIndex(daily["date"]), expected_dates,
                                  check_names=False, check_exact=True)
    values = daily[["equity", "nav", "return", "cash", "cost"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (daily["equity"] <= 0).any() or (daily["return"] <= -1).any():
        raise ValueError("账户金额或日收益缺失/非法，停止分段。")
    previous_equity = daily["equity"].shift(1)
    previous_equity.iloc[0] = initial_cash
    np.testing.assert_allclose(daily["return"], daily["equity"] / previous_equity - 1,
                               rtol=0, atol=1e-12)
    np.testing.assert_allclose(daily["nav"], daily["equity"] / initial_cash,
                               rtol=0, atol=1e-12)
    return daily


def split_account(daily, split, bounds, initial_cash):
    """保留区间首条收益；展示净值以首条收益之前的权益为 1。"""
    start, end = map(pd.Timestamp, bounds)
    mask = daily["date"].between(start, end, inclusive="both")
    block = daily.loc[mask].copy()
    if block.empty:
        raise ValueError(f"{split} 没有账户记录。")

    # 这些是连续账户的上一日基准，不是在分段开始时注入的新资金。
    first_position = np.flatnonzero(mask.to_numpy())[0]
    if first_position == 0:
        anchor_equity = initial_cash
        anchor_date = None
        anchor_holdings = 0
    else:
        anchor = daily.iloc[first_position - 1]
        anchor_equity = float(anchor["equity"])
        anchor_date = anchor["date"]
        anchor_holdings = int(anchor["holdings_count"])

    # 本课核心：切的是已有日收益，不对切片重新 pct_change 或把首条收益填零。
    block["period_nav"] = (1 + block["return"]).cumprod(skipna=False)
    block["period_peak"] = block["period_nav"].cummax(skipna=False).clip(lower=1.0)
    block["period_drawdown"] = block["period_nav"] / block["period_peak"] - 1
    values = metrics(block)

    np.testing.assert_allclose(block["period_nav"], block["equity"] / anchor_equity,
                               rtol=0, atol=1e-10)
    np.testing.assert_allclose(block["period_drawdown"].min(), values["max_drawdown"],
                               rtol=0, atol=1e-10)
    signed_drawdown = values.pop("max_drawdown")
    row = dict(split=split, label=SPLIT_LABELS.get(split, split), requested_start=str(start.date()),
               requested_end=str(end.date()), first_date=str(block["date"].iloc[0].date()),
               last_date=str(block["date"].iloc[-1].date()), n_days=len(block), **values,
               max_drawdown=-signed_drawdown, max_drawdown_signed=signed_drawdown,
               anchor_equity=float(anchor_equity), ending_equity=float(block["equity"].iloc[-1]))
    boundary = dict(split=split, anchor_date=anchor_date, anchor_equity=float(anchor_equity),
                    anchor_holdings_count=anchor_holdings, first_date=block["date"].iloc[0],
                    first_day_return=float(block["return"].iloc[0]),
                    first_close_equity=float(block["equity"].iloc[0]),
                    last_date=block["date"].iloc[-1], ending_equity=float(block["equity"].iloc[-1]))
    block["split"] = split
    return block, row, boundary


def compare_periods(metric_table, paths, splits):
    """以相同区间配对；收益差用百分点，比例比较用相对财富。"""
    rows, relative_frames = [], []
    for split in splits:
        selected = metric_table.loc[metric_table["split"].eq(split)].set_index("portfolio")
        strategy_return = float(selected.loc["strategy", "total_return"])
        benchmark_return = float(selected.loc["benchmark", "total_return"])
        return_gap_pp = (strategy_return - benchmark_return) * 100
        relative_return = (1 + strategy_return) / (1 + benchmark_return) - 1
        rows.append(dict(split=split, label=SPLIT_LABELS.get(split, split),
                         n_days=int(selected.loc["strategy", "n_days"]),
                         strategy_total_return=strategy_return, benchmark_total_return=benchmark_return,
                         return_gap_percentage_points=return_gap_pp, relative_return=relative_return,
                         strategy_annual_return=float(selected.loc["strategy", "annual_return"]),
                         benchmark_annual_return=float(selected.loc["benchmark", "annual_return"]),
                         strategy_max_drawdown=float(selected.loc["strategy", "max_drawdown"]),
                         benchmark_max_drawdown=float(selected.loc["benchmark", "max_drawdown"])))
        strategy = paths.loc[paths["split"].eq(split) & paths["portfolio"].eq("strategy"),
                             ["date", "period_nav"]].rename(columns={"period_nav": "strategy_period_nav"})
        benchmark = paths.loc[paths["split"].eq(split) & paths["portfolio"].eq("benchmark"),
                              ["date", "period_nav"]].rename(columns={"period_nav": "benchmark_period_nav"})
        pair = strategy.merge(benchmark, on="date", how="inner", validate="one_to_one")
        assert len(pair) == len(strategy) == len(benchmark)
        pair["relative_nav"] = pair["strategy_period_nav"] / pair["benchmark_period_nav"]
        pair["relative_return"] = pair["relative_nav"] - 1
        pair["split"] = split
        np.testing.assert_allclose(pair["relative_return"].iloc[-1], relative_return, rtol=0, atol=1e-10)
        relative_frames.append(pair)
    return pd.DataFrame(rows), pd.concat(relative_frames, ignore_index=True)


def reconcile_segments(accounts, metric_table, comparison):
    """相邻区间收益连乘、费用求和；回撤不做跨段求和或取最大值。"""
    rows = []
    for portfolio, daily in accounts.items():
        periods = metric_table.loc[metric_table["portfolio"].eq(portfolio)]
        reconstructed_return = (1 + periods["total_return"]).prod() - 1
        whole = metrics(daily)
        np.testing.assert_allclose(reconstructed_return, whole["total_return"], rtol=0, atol=1e-10)
        np.testing.assert_allclose(periods["total_cost"].sum(), whole["total_cost"], rtol=0, atol=1e-7)
        assert periods["n_days"].sum() == len(daily)
        rows.append(dict(portfolio=portfolio, n_days=len(daily),
                         compounded_segment_return=float(reconstructed_return),
                         full_history_return=float(whole["total_return"]),
                         full_history_max_drawdown=float(-whole["max_drawdown"]),
                         summed_segment_cost=float(periods["total_cost"].sum()),
                         full_history_cost=float(whole["total_cost"])))
    strategy_total = metrics(accounts["strategy"])["total_return"]
    benchmark_total = metrics(accounts["benchmark"])["total_return"]
    np.testing.assert_allclose((1 + comparison["relative_return"]).prod() - 1,
                               (1 + strategy_total) / (1 + benchmark_total) - 1, rtol=0, atol=1e-10)
    return pd.DataFrame(rows)


def plot_stability(paths, metric_table, boundaries, splits, output_path):
    """同一幅图展示分段净值、复合年化收益和区间内最大回撤。"""
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    fig = plt.figure(figsize=(13, 8.5), layout="constrained")
    grid = fig.add_gridspec(2, 6, height_ratios=[1.1, 1])
    fig.suptitle("开发、验证、测试：事后分段检查（模拟数据，1 倍成本）", fontsize=17)
    nav_min = min(1.0, paths["period_nav"].min()) - 0.05
    nav_max = max(1.0, paths["period_nav"].max()) + 0.17
    for number, split in enumerate(splits):
        ax = fig.add_subplot(grid[0, number * 2:number * 2 + 2])
        block = paths.loc[paths["split"].eq(split)]
        dates = pd.DatetimeIndex(sorted(block["date"].unique()))
        ax.set_title(f"{SPLIT_LABELS.get(split, split)}\n{dates[0]:%Y-%m-%d} 至 {dates[-1]:%Y-%m-%d}，N={len(dates)}",
                     fontsize=11, pad=12)
        for portfolio, color, line, label in [
            ("strategy", "#3268A8", "-", "三因子策略"),
            ("benchmark", "#747D86", "--", "同池等权基准"),
        ]:
            local = block.loc[block["portfolio"].eq(portfolio)]
            boundary = boundaries.loc[boundaries["split"].eq(split) &
                                        boundaries["portfolio"].eq(portfolio)].iloc[0]
            anchor_date = boundary["anchor_date"]
            if pd.isna(anchor_date):
                anchor_date = local["date"].iloc[0]
            x_values = [anchor_date, *local["date"].tolist()]
            y_values = [1.0, *local["period_nav"].tolist()]
            ax.plot(x_values, y_values, color=color, linestyle=line, linewidth=1.5, label=label)
        ax.axhline(1, color="#9FA6AD", linestyle=":", linewidth=0.8)
        ax.set_ylim(nav_min, nav_max)
        if number == 0:
            ax.set_ylabel("区间净值（段前权益 = 1）")
        else:
            ax.tick_params(labelleft=False)
        ax.set_xticks([dates[0], dates[len(dates) // 2], dates[-1]])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.legend(loc="upper left", frameon=False, fontsize=10)
        ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="both", labelsize=10)

    labels = [SPLIT_LABELS.get(split, split) for split in splits]
    x_positions = np.arange(len(labels))
    for column, field, title in [
        (0, "annual_return", "复合年化收益（252 交易日口径）"),
        (3, "max_drawdown", "区间内最大回撤幅度（正数）"),
    ]:
        ax = fig.add_subplot(grid[1, column:column + 3])
        all_values = []
        for portfolio, offset, color, edge, hatch, label in [
            ("strategy", -0.18, "#3268A8", "#3268A8", None, "三因子策略"),
            ("benchmark", 0.18, "#D1D5DA", "#747D86", "//", "同池等权基准"),
        ]:
            values = metric_table.loc[metric_table["portfolio"].eq(portfolio)].set_index("split").loc[list(splits), field]
            all_values.extend(values.tolist())
            bars = ax.bar(x_positions + offset, values, width=0.34, color=color, edgecolor=edge,
                           linewidth=0.8, hatch=hatch, label=label)
            ax.bar_label(bars, labels=[f"{value:.2%}" for value in values], padding=4, fontsize=10)
        if field == "annual_return":
            ax.set_ylim(min(0, min(all_values)) - 0.025, max(0, max(all_values)) + 0.05)
        else:
            ax.set_ylim(0, max(all_values) * 1.4)
        ax.axhline(0, color="#747D86", linewidth=0.8)
        ax.set_xticks(x_positions, labels)
        ax.set_title(title, fontsize=12, pad=12)
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
        ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=10)
        ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.supxlabel("账户连续持仓；上方分段净值以段前权益归一化；各段时长不同，回撤受观察长度影响", fontsize=10)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main():
    project_dir = Path(__file__).resolve().parents[1]
    run_dir = project_dir / "runs" / "first_demo_20261107"
    source_dir = run_dir / "lesson16_benchmark_cost"
    output_dir = run_dir / "lesson17_split_stability"

    # 1. 读取上一课冻结配置和已运行的连续账户。
    config_path = source_dir / "config_snapshot.json"
    config = load_config(config_path)
    splits = config["splits"]
    calendar = pd.read_csv(run_dir / "input" / "calendar.csv", parse_dates=["date"])
    expected = pd.DatetimeIndex(calendar.loc[calendar["date"].between(config["start"], config["end"]), "date"])
    accounts, lineage = {}, {}
    for portfolio in ["strategy", "benchmark"]:
        path = source_dir / f"{portfolio}_cost1" / "daily.csv"
        accounts[portfolio] = read_continuous_account(path, config["initial_cash"], expected)
        lineage[portfolio] = dict(path=str(path), sha256=sha256(path.read_bytes()).hexdigest())
    pd.testing.assert_series_equal(accounts["strategy"]["date"], accounts["benchmark"]["date"])

    # 2. 按原定日期切分日收益；不清仓、不重置账户、不重新计算分段首日收益。
    metric_rows, path_frames, boundary_rows = [], [], []
    for portfolio, daily in accounts.items():
        coverage = np.zeros(len(daily), dtype=int)
        for split, bounds in splits.items():
            coverage += daily["date"].between(*bounds).to_numpy(dtype=int)
            block, row, boundary = split_account(daily, split, bounds, config["initial_cash"])
            row["portfolio"] = portfolio
            boundary["portfolio"] = portfolio
            block["portfolio"] = portfolio
            metric_rows.append(row)
            path_frames.append(block)
            boundary_rows.append(boundary)
        if not (coverage == 1).all():
            raise ValueError("各分区必须恰好覆盖完整账户一次，不能遗漏或重叠日期。")

    # 3. 同期配对与跨段对账。
    metric_table = pd.DataFrame(metric_rows)
    paths = pd.concat(path_frames, ignore_index=True)
    boundaries = pd.DataFrame(boundary_rows)
    comparison, relative_paths = compare_periods(metric_table, paths, splits)
    reconciliation = reconcile_segments(accounts, metric_table, comparison)

    # 4. 保存来源和计算过程。收益以小数存储，百分点字段已乘以 100。
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in [("metrics", metric_table), ("period_paths", paths),
                        ("boundaries", boundaries), ("comparison", comparison),
                        ("relative_paths", relative_paths), ("reconciliation", reconciliation)]:
        frame.to_csv(output_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    write_json(output_dir / "config_snapshot.json", config)
    write_json(output_dir / "methodology.json", dict(
        source="synthetic teaching data; weekday calendar, not an A-share exchange calendar",
        evaluation="retrospective split stability check; full history has already been viewed",
        rules="frozen lesson16 config and cost1 accounts; no parameter selection or backtest rerun",
        partitions=splits, annual_sessions=252,
        local_nav="cumprod(1 + original daily returns); equivalent to equity / preceding session equity",
        boundary="retain first included return, prior holdings and prior equity; initial capital for first segment",
        drawdown="local high-water mark starts at 1; segment drawdowns do not reconstruct full-history drawdown",
        comparison="same dates and cost1; total-return difference in percentage points; relative wealth ratio minus 1",
        caution="three unequal-length periods are descriptive, not proof of stability or an untouched holdout",
        positive_relative_periods=int(comparison["relative_return"].gt(0).sum()),
        number_of_periods=len(comparison), inputs=lineage,
        config_sha256=sha256(config_path.read_bytes()).hexdigest(),
    ))
    plot_stability(paths, metric_table, boundaries, splits, output_dir / "split_stability.png")

    print("事后分段检查：人工数据，1 倍教学成本，账户连续持仓。")
    print("\n六组区间指标（收益/回撤以小数存储）：")
    print(metric_table[["split", "portfolio", "n_days", "total_return", "annual_return",
                        "annual_volatility", "max_drawdown", "total_cost"]].to_string(index=False))
    print("\n同期比较：")
    print(comparison.to_string(index=False))
    print("\n边界账户核对：")
    print(boundaries.to_string(index=False))
    print("\n跨段复原全期：")
    print(reconciliation.to_string(index=False))
    print("\n本课结果目录：", output_dir)


if __name__ == "__main__":
    main()
