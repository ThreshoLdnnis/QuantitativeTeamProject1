r"""第十六课：同池等权基准、相对收益与 0/1/2 倍教学成本。

运行：.\.venv\Scripts\python.exe examples/16_benchmark_cost_comparison.py
六条路径均使用同一人工数据、因子完整股票池、起止日期和成交规则。
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

from ashare_lab.backtest import metrics, run_backtest
from ashare_lab.config import load_config
from ashare_lab.data import load_dataset, write_json
from ashare_lab.factors import compute_factors, monthly_signal_dates


def build_signal_pools(factors, calendar, config):
    """记录每个信号日的目标池；执行日状态只影响成交，不影响排名。"""
    rows = []
    targets = {"benchmark": {}, "strategy": {}}
    for signal_date in monthly_signal_dates(calendar):
        execution_date = calendar[calendar.get_loc(signal_date) + 1]
        if not (pd.Timestamp(config["start"]) <= signal_date < execution_date <= pd.Timestamp(config["end"])):
            continue
        cross = factors.loc[factors["date"].eq(signal_date)]
        cross = cross.loc[np.isfinite(cross["composite"])]
        ranked = cross.sort_values(["composite", "symbol"], ascending=[False, True])
        whole_pool = ranked["symbol"].tolist()
        top_names = ranked.head(config["top_n"])["symbol"].tolist()
        if not whole_pool:
            raise ValueError("本课信号日的完整因子股票池为空。")
        targets["benchmark"][signal_date] = set(whole_pool)
        targets["strategy"][signal_date] = set(top_names)
        rows.append(dict(signal_date=signal_date, execution_date=execution_date,
                         benchmark_target_count=len(whole_pool), strategy_target_count=len(top_names),
                         benchmark_symbols="|".join(sorted(whole_pool)), strategy_symbols="|".join(top_names)))
    return pd.DataFrame(rows), targets


def audit_and_save(result, folder, target_sets):
    """核对现金/持仓/费用及买入名单，保存可逐笔检查的表。"""
    daily = result.daily
    invested = result.positions.groupby("date")["market_value"].sum()
    values = daily["date"].map(invested).fillna(0)  # 没有持仓的日期市值为 0，不填补行情。
    np.testing.assert_allclose(daily["equity"], daily["cash"] + values, rtol=0, atol=1e-7)
    np.testing.assert_allclose(daily["nav"], daily["equity"] / daily["equity"].iloc[0],
                               rtol=0, atol=1e-10)  # 本课首日是净值 1 的持币日。
    assert (daily["cash"] >= 0).all()
    assert (result.trades["date"] > result.trades["signal_date"]).all()
    recorded_cost = result.trades[["commission", "tax", "slippage_cost"]].sum().sum()
    np.testing.assert_allclose(daily["cost"].sum(), recorded_cost, rtol=0, atol=1e-7)
    for signal_date, buys in result.trades.loc[result.trades["side"].eq("buy")].groupby("signal_date"):
        assert set(buys["symbol"]).issubset(target_sets[signal_date])
    folder.mkdir(parents=True, exist_ok=True)
    for name in ["daily", "trades", "orders", "positions"]:
        getattr(result, name).to_csv(folder / f"{name}.csv", index=False, date_format="%Y-%m-%d")


def build_comparison(results):
    """同费率配对：收益差用小数存储，显示时转换为百分点。"""
    dates = results["strategy_cost1"].daily["date"].reset_index(drop=True)
    paths = pd.DataFrame({"date": dates})
    for name, result in results.items():
        pd.testing.assert_series_equal(result.daily["date"].reset_index(drop=True), dates)
        paths[f"{name}_nav"] = result.daily["nav"].to_numpy()

    rows = []
    for multiplier in [0, 1, 2]:
        strategy = results[f"strategy_cost{multiplier}"].daily
        benchmark = results[f"benchmark_cost{multiplier}"].daily

        # 相对财富曲线是两条同起点净值之比，不是收益率之差的连乘。
        relative_nav = strategy["nav"] / benchmark["nav"]
        relative_daily_return = (1 + strategy["return"]) / (1 + benchmark["return"]) - 1
        np.testing.assert_allclose((1 + relative_daily_return).cumprod(skipna=False), relative_nav,
                                   rtol=0, atol=1e-10)
        paths[f"relative_nav_cost{multiplier}"] = relative_nav
        paths[f"relative_return_cost{multiplier}"] = relative_nav - 1
        paths[f"cumulative_return_gap_cost{multiplier}"] = strategy["nav"] - benchmark["nav"]

        strategy_return = strategy["nav"].iloc[-1] - 1
        benchmark_return = benchmark["nav"].iloc[-1] - 1
        return_gap = strategy_return - benchmark_return
        relative_return = relative_nav.iloc[-1] - 1
        rows.append(dict(cost_multiplier=multiplier, strategy_total_return=float(strategy_return),
                         benchmark_total_return=float(benchmark_return), return_gap=float(return_gap),
                         return_gap_percentage_points=float(return_gap * 100), relative_return=float(relative_return)))
    return paths, pd.DataFrame(rows)


def build_cost_impact(summary):
    """终值差包含费用改变资金/持仓及复利路径的影响，不等于累计费用。"""
    rows = []
    for portfolio in ["strategy", "benchmark"]:
        cases = summary.loc[summary["portfolio"].eq(portfolio)].set_index("cost_multiplier")
        zero_fee_equity = cases.loc[0, "final_equity"]
        for multiplier in [1, 2]:
            wealth_gap = zero_fee_equity - cases.loc[multiplier, "final_equity"]
            recorded_cost = cases.loc[multiplier, "total_cost"]
            rows.append(dict(portfolio=portfolio, cost_multiplier=multiplier,
                             terminal_wealth_gap_vs_zero_cost=float(wealth_gap),
                             recorded_total_cost=float(recorded_cost),
                             gap_minus_recorded_cost=float(wealth_gap - recorded_cost)))
    return pd.DataFrame(rows)


def plot_comparison(paths, summary, output_path):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    fig, axes = plt.subplots(3, 1, figsize=(11.5, 10.5), sharex=True, layout="constrained")
    fig.suptitle("基准比较与交易成本敏感性（模拟数据，2020—2025）", fontsize=17)
    dates = paths["date"]
    styles = {0: ("#977312", "--"), 1: ("#3268A8", "-"), 2: ("#B46A31", ":")}

    ax = axes[0]
    ax.set_title("1 倍教学费率：前 10 只策略与完整因子池等权基准", loc="left", fontsize=12, pad=10)
    ax.plot(dates, paths["strategy_cost1_nav"], color="#3268A8", linewidth=1.5,
            label=f"三因子策略（期末 {paths['strategy_cost1_nav'].iloc[-1]:.4f}）")
    ax.plot(dates, paths["benchmark_cost1_nav"], color="#747D86", linestyle="--", linewidth=1.4,
            label=f"同池等权基准（期末 {paths['benchmark_cost1_nav'].iloc[-1]:.4f}）")
    ax.axhline(1, color="#9FA6AD", linestyle=":", linewidth=0.8)
    ax.set_ylabel("净值（初始 = 1）")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    net_values = paths[["strategy_cost1_nav", "benchmark_cost1_nav"]]
    ax.set_ylim(net_values.min().min() - 0.06, net_values.max().max() + 0.12)

    ax = axes[1]
    ax.set_title("三因子策略：仅调整费用档位，分别重新回测", loc="left", fontsize=12, pad=10)
    for multiplier, (color, line) in styles.items():
        column = f"strategy_cost{multiplier}_nav"
        ax.plot(dates, paths[column], color=color, linestyle=line, linewidth=1.5,
                label=f"{multiplier} 倍成本（期末 {paths[column].iloc[-1]:.4f}）")
    ax.axhline(1, color="#9FA6AD", linestyle=":", linewidth=0.8)
    ax.set_ylabel("净值（初始 = 1）")
    cost_values = paths[[f"strategy_cost{m}_nav" for m in styles]]
    ax.set_ylim(cost_values.min().min() - 0.05, cost_values.max().max() + 0.16)
    ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=10)

    ax = axes[2]
    ax.set_title("各档策略相对同档基准：净值比值 − 1", loc="left", fontsize=12, pad=10)
    for multiplier, (color, line) in styles.items():
        column = f"relative_return_cost{multiplier}"
        ax.plot(dates, paths[column], color=color, linestyle=line, linewidth=1.5,
                label=f"{multiplier} 倍配对（期末 {paths[column].iloc[-1]:.2%}）")
    ax.axhline(0, color="#747D86", linewidth=0.9)
    ax.set_ylabel("相对收益（比值口径）")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    relative_values = paths[[f"relative_return_cost{m}" for m in styles]]
    ax.set_ylim(relative_values.min().min() - 0.025, relative_values.max().max() + 0.09)
    ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=10)

    ticks = pd.date_range(dates.iloc[0], dates.iloc[-1], freq="YS")
    ticks = ticks.union(pd.DatetimeIndex([dates.iloc[0], dates.iloc[-1]]))
    axes[-1].set_xticks(ticks)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    axes[-1].set_xlim(dates.iloc[0] - pd.Timedelta(days=20), dates.iloc[-1] + pd.Timedelta(days=20))
    axes[-1].set_xlabel("日期（人工行情与工作日日历；期末按收盘估值，仍有持仓）")
    for ax in axes:
        ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="both", labelsize=10)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main():
    project_dir = Path(__file__).resolve().parents[1]
    run_dir = project_dir / "runs" / "first_demo_20261107"
    output_dir = run_dir / "lesson16_benchmark_cost"
    prices, universe, calendar, _ = load_dataset(run_dir / "input")
    config = load_config(project_dir / "configs" / "baseline.json")
    config["calendar_dates"] = calendar.strftime("%Y-%m-%d").tolist()
    factors = compute_factors(prices, universe, config)
    signal_pools, targets = build_signal_pools(factors, calendar, config)

    # 同一费率同时比较策略和基准；每个档位重新模拟真实现金与实际持仓。
    results = {}
    metric_rows = []
    fee_rows = []
    for multiplier in [0, 1, 2]:
        scenario = dict(config, cost_multiplier=multiplier)
        fee_rows.append(dict(cost_multiplier=multiplier,
                             commission_bps=config["commission_bps"] * multiplier,
                             slippage_bps=config["slippage_bps"] * multiplier,
                             sell_tax_bps=config["sell_tax_bps"] * multiplier))
        for portfolio, score in [("benchmark", None), ("strategy", "composite")]:
            name = f"{portfolio}_cost{multiplier}"
            result = run_backtest(prices, factors, calendar, scenario, score_column=score)
            audit_and_save(result, output_dir / name, targets[portfolio])
            results[name] = result
            values = metrics(result.daily)
            signed_drawdown = values.pop("max_drawdown")
            metric_rows.append(dict(case=name, portfolio=portfolio, cost_multiplier=multiplier,
                                    n_days=len(result.daily), **values,
                                    max_drawdown=-signed_drawdown, max_drawdown_signed=signed_drawdown,
                                    final_equity=float(result.daily["equity"].iloc[-1]),
                                    final_nav=float(result.daily["nav"].iloc[-1]),
                                    commission=float(result.trades["commission"].sum()),
                                    sell_tax=float(result.trades["tax"].sum()),
                                    slippage=float(result.trades["slippage_cost"].sum())))
            print(f"完成 {name}: 累计收益 {values['total_return']:.6%}", flush=True)

    summary = pd.DataFrame(metric_rows)
    paths, comparison = build_comparison(results)
    cost_impact = build_cost_impact(summary)

    # 1 倍策略必须与上一课完整历史结果一致。
    previous_path = run_dir / "lesson15_full_backtest" / "daily.csv"
    if previous_path.exists():
        previous = pd.read_csv(previous_path, parse_dates=["date"])
        current = results["strategy_cost1"].daily
        pd.testing.assert_frame_equal(current, previous[current.columns], check_exact=False, rtol=0, atol=1e-8)

    summary.to_csv(output_dir / "metrics.csv", index=False)
    comparison.to_csv(output_dir / "relative_comparison.csv", index=False)
    cost_impact.to_csv(output_dir / "cost_impact.csv", index=False)
    paths.to_csv(output_dir / "comparison_paths.csv", index=False, date_format="%Y-%m-%d")
    signal_pools.to_csv(output_dir / "signal_pools.csv", index=False, date_format="%Y-%m-%d")
    pd.DataFrame(fee_rows).to_csv(output_dir / "fee_schedule.csv", index=False)
    write_json(output_dir / "config_snapshot.json", {k: v for k, v in config.items() if k != "calendar_dates"})
    write_json(output_dir / "methodology.json", dict(
        source="synthetic teaching data; weekday calendar, not an A-share exchange calendar",
        start=config["start"], end=config["end"], annual_sessions=252,
        benchmark="monthly target equal weight across the same finite-composite pool, score_column=None",
        strategy="top 10 by composite from that same pool, monthly target equal weight",
        execution="next-session open, sell first, cash-scaled buys, supplied status flags",
        fees="fixed teaching bps; multiplier scales commission, slippage and sell tax together",
        relative_return="strategy NAV / same-cost benchmark NAV - 1; not a tradable long-short return",
        return_gap="strategy total return - benchmark total return; multiply by 100 for percentage points",
        cost_comparison="separately rerun paths; terminal wealth gap includes costs and changed investment paths",
        terminal_valuation="last close; no hypothetical liquidation",
    ))
    plot_comparison(paths, summary, output_dir / "benchmark_cost_comparison.png")

    print("\n六组指标（收益和回撤以小数存储）：")
    print(summary[["case", "total_return", "annual_return", "annual_volatility", "max_drawdown", "total_cost"]].to_string(index=False))
    print("\n同费率配对比较：")
    print(comparison.to_string(index=False))
    print("\n终值差与累计成本：")
    print(cost_impact.to_string(index=False))
    print("\n本课结果目录：", output_dir)


if __name__ == "__main__":
    main()
