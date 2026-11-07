r"""第十五课：完整历史回测，逐行计算收益、波动和回撤。

运行：.\.venv\Scripts\python.exe examples/15_full_history_performance.py
输入沿用 first_demo_20261107 的人工行情；不拼入第十四课的人为拒卖场景。
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
from ashare_lab.factors import compute_factors


def calculate_performance(daily, initial_cash, annual_sessions=252):
    """返回带计算过程的日表和指标；金额不再重复扣除交易成本。"""
    daily = daily.copy().sort_values("date").reset_index(drop=True)
    if len(daily) < 2 or daily["date"].duplicated().any():
        raise ValueError("至少需要两个不同日期的账户记录。")
    if initial_cash <= 0 or annual_sessions <= 0:
        raise ValueError("初始资金和每年交易日数必须为正。")
    returns = daily["return"].astype(float)
    if not np.isfinite(returns).all() or (returns <= -1).any():
        raise ValueError("日收益缺失或非法；不能填零后继续计算。")

    # A. 净值与累计收益：每一行是账户的已知日收益，包括持币日。
    daily["growth_factor"] = 1 + returns
    daily["nav_from_returns"] = daily["growth_factor"].cumprod(skipna=False)
    daily["cumulative_return"] = daily["nav_from_returns"] - 1
    total_return = daily["cumulative_return"].iloc[-1]

    # B. 复合年化：把 n 个模拟交易日折算成 n / 252 个交易年。
    n_days = len(returns)
    annual_return = (1 + total_return) ** (annual_sessions / n_days) - 1

    # C. 样本日波动率及平方根时间法则下的年化波动率。
    daily_volatility = returns.std(ddof=1)
    annual_volatility = daily_volatility * np.sqrt(annual_sessions)

    # D. 初始净值 1 也参与历史高点，避免漏掉开局亏损。
    daily["running_peak"] = daily["nav_from_returns"].cummax(skipna=False).clip(lower=1.0)
    daily["drawdown"] = daily["nav_from_returns"] / daily["running_peak"] - 1
    max_drawdown_signed = daily["drawdown"].min()
    max_drawdown = -max_drawdown_signed

    # E. 定位最深回撤的谷底，以及谷底之前的历史峰值。
    trough_index = daily["drawdown"].idxmin()
    before_trough = daily.loc[:trough_index]
    peak_index = before_trough["nav_from_returns"].idxmax()
    peak_date = None
    peak_nav = 1.0
    if before_trough.loc[peak_index, "nav_from_returns"] >= 1:
        peak_date = str(before_trough.loc[peak_index, "date"].date())
        peak_nav = float(before_trough.loc[peak_index, "nav_from_returns"])

    # F. 三种口径交叉核对；不把首日收益强行设为零。
    np.testing.assert_allclose(daily["nav_from_returns"], daily["nav"], rtol=0, atol=1e-10)
    np.testing.assert_allclose(daily["nav_from_returns"], daily["equity"] / initial_cash,
                               rtol=0, atol=1e-10)
    core = metrics(daily)
    np.testing.assert_allclose(
        [total_return, annual_return, annual_volatility, max_drawdown_signed],
        [core["total_return"], core["annual_return"], core["annual_volatility"], core["max_drawdown"]],
        rtol=0, atol=1e-10,
    )

    summary = dict(
        source="synthetic teaching data; weekday calendar, not an A-share exchange calendar",
        start=str(daily["date"].iloc[0].date()), end=str(daily["date"].iloc[-1].date()),
        n_days=n_days, annual_sessions=annual_sessions,
        effective_trading_years=float(n_days / annual_sessions),
        initial_cash=float(initial_cash), final_equity=float(daily["equity"].iloc[-1]),
        final_nav=float(daily["nav_from_returns"].iloc[-1]),
        total_return=float(total_return), annual_return=float(annual_return),
        daily_volatility=float(daily_volatility), annual_volatility=float(annual_volatility),
        max_drawdown=float(max_drawdown), max_drawdown_signed=float(max_drawdown_signed),
        drawdown_peak_date=peak_date, drawdown_peak_nav=peak_nav,
        drawdown_trough_date=str(daily.loc[trough_index, "date"].date()),
        drawdown_trough_nav=float(daily.loc[trough_index, "nav_from_returns"]),
        final_drawdown=float(daily["drawdown"].iloc[-1]),
        total_cost=float(daily["cost"].sum()), final_cash=float(daily["cash"].iloc[-1]),
        final_holdings_count=int(daily["holdings_count"].iloc[-1]),
        terminal_valuation="last close; no hypothetical liquidation",
    )
    return daily, summary


def plot_performance(daily, summary, output_path):
    """上方净值、下方回撤，完整展示所有模拟交易日。"""
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    fig, (ax_nav, ax_dd) = plt.subplots(
        2, 1, figsize=(11.5, 7.8), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]}, layout="constrained",
    )
    fig.suptitle("三因子策略：完整历史净值与回撤（模拟数据）", fontsize=17)
    ax_nav.set_title(
        f"2020—2025 年，含教学交易成本；累计收益 {summary['total_return']:.2%}",
        loc="left", fontsize=11, pad=12,
    )
    ax_nav.plot(daily["date"], daily["nav_from_returns"], color="#3268A8", linewidth=1.5,
                label="账户净值")
    ax_nav.plot(daily["date"], daily["running_peak"], color="#747D86", linestyle="--",
                linewidth=1.2, label="截至当日的历史高点")
    ax_nav.axhline(1, color="#9FA6AD", linestyle=":", linewidth=0.8)
    ax_nav.set_ylabel("净值（初始资金 = 1）")
    ax_nav.set_ylim(daily["nav_from_returns"].min() - 0.11, daily["nav_from_returns"].max() + 0.13)
    ax_nav.legend(loc="upper right", frameon=False, fontsize=10)
    if summary["drawdown_peak_date"] is not None:
        peak_date = pd.Timestamp(summary["drawdown_peak_date"])
        ax_nav.scatter(peak_date, summary["drawdown_peak_nav"], s=35, color="#3268A8", zorder=5)
        ax_nav.annotate(
            f"回撤前高 {peak_date:%Y-%m-%d}\n净值 {summary['drawdown_peak_nav']:.4f}",
            xy=(peak_date, summary["drawdown_peak_nav"]), xytext=(14, 27), textcoords="offset points",
            fontsize=10, arrowprops={"arrowstyle": "->", "color": "#747D86"},
        )
    trough_date = pd.Timestamp(summary["drawdown_trough_date"])
    ax_nav.scatter(trough_date, summary["drawdown_trough_nav"], marker="v", s=45,
                   color="#B46A31", zorder=5)
    ax_nav.annotate(
        f"回撤谷底 {trough_date:%Y-%m-%d}\n净值 {summary['drawdown_trough_nav']:.4f}",
        xy=(trough_date, summary["drawdown_trough_nav"]), xytext=(-165, -35), textcoords="offset points",
        fontsize=10, arrowprops={"arrowstyle": "->", "color": "#747D86"},
    )
    ax_nav.annotate(
        f"期末 {summary['final_nav']:.4f}", xy=(daily["date"].iloc[-1], summary["final_nav"]),
        xytext=(-100, 30), textcoords="offset points", fontsize=10,
        arrowprops={"arrowstyle": "->", "color": "#747D86"},
    )
    ax_dd.plot(daily["date"], daily["drawdown"], color="#3268A8", linewidth=1.1)
    ax_dd.fill_between(daily["date"], daily["drawdown"], 0, color="#3268A8", alpha=0.18)
    ax_dd.axhline(0, color="#747D86", linewidth=0.8)
    ax_dd.scatter(trough_date, summary["max_drawdown_signed"], marker="v", s=40,
                  color="#B46A31", zorder=5)
    ax_dd.annotate(
        f"最大回撤幅度 {summary['max_drawdown']:.2%}",
        xy=(trough_date, summary["max_drawdown_signed"]), xytext=(-60, -9),
        textcoords="offset points", ha="center", va="top", fontsize=10,
        arrowprops={"arrowstyle": "->", "color": "#747D86"},
    )
    ax_dd.set_ylim(summary["max_drawdown_signed"] - 0.055, 0.025)
    ax_dd.set_ylabel("相对历史高点的回撤")
    ax_dd.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ticks = pd.date_range(daily["date"].iloc[0], daily["date"].iloc[-1], freq="YS")
    ticks = ticks.union(pd.DatetimeIndex([daily["date"].iloc[0], daily["date"].iloc[-1]]))
    ax_dd.set_xticks(ticks)
    ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax_dd.set_xlim(daily["date"].iloc[0] - pd.Timedelta(days=20),
                   daily["date"].iloc[-1] + pd.Timedelta(days=20))
    ax_dd.set_xlabel("日期（模拟工作日日历；期末按收盘估值，仍有持仓）")
    for ax in (ax_nav, ax_dd):
        ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="both", labelsize=10)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main():
    # 1. 定位项目与输入；不用重新生成数据，不改上一课文件。
    project_dir = Path(__file__).resolve().parents[1]
    run_dir = project_dir / "runs" / "first_demo_20261107"
    prices, universe, calendar, _ = load_dataset(run_dir / "input")

    # 2. 恢复完整区间；2019 年行情保留在 prices 中，只用于滚动历史预热。
    config = load_config(project_dir / "configs" / "baseline.json")
    config["calendar_dates"] = calendar.strftime("%Y-%m-%d").tolist()

    # 3. 沿用同一套因子与成交规则，连续运行 2020-01-01 到 2025-12-31。
    factors = compute_factors(prices, universe, config)
    result = run_backtest(prices, factors, calendar, config)

    # 4. 展开四项指标的计算过程。
    daily, summary = calculate_performance(result.daily, config["initial_cash"])

    # 5. 对账：每日权益包含现金与实际持仓；成交严格晚于信号。
    invested = result.positions.groupby("date")["market_value"].sum()
    stock_values = daily["date"].map(invested).fillna(0)
    np.testing.assert_allclose(daily["equity"], daily["cash"] + stock_values, rtol=0, atol=1e-7)
    assert (daily["cash"] >= 0).all()
    assert (result.trades["date"] > result.trades["signal_date"]).all()
    summary["execution_days_with_trades"] = int(result.trades["date"].nunique())
    summary["trade_count"] = len(result.trades)
    summary["rejected_orders"] = int(result.orders["status"].eq("rejected").sum())

    # 6. 若上一课文件存在，核对重叠区间完全衔接。
    previous_path = run_dir / "lesson14_daily_rebalance" / "daily.csv"
    if previous_path.exists():
        previous = pd.read_csv(previous_path, parse_dates=["date"])
        current = daily.loc[daily["date"].isin(previous["date"]), previous.columns].reset_index(drop=True)
        pd.testing.assert_frame_equal(current, previous, check_exact=False, rtol=0, atol=1e-8)

    # 7. 独立保存本课结果；百分比仍存为小数，显示时才格式化。
    output_dir = run_dir / "lesson15_full_backtest"
    output_dir.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_dir / "daily.csv", index=False, date_format="%Y-%m-%d")
    for name in ["trades", "orders", "positions"]:
        getattr(result, name).to_csv(output_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    metric_names = ["total_return", "annual_return", "annual_volatility", "max_drawdown"]
    pd.DataFrame([{name: summary[name] for name in metric_names}]).to_csv(output_dir / "metrics.csv", index=False)
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "config_snapshot.json", {k: v for k, v in config.items() if k != "calendar_dates"})
    plot_performance(daily, summary, output_dir / "full_history_nav_drawdown.png")

    print("人工行情与工作日日历；2019 年预热，2020—2025 年连续回测。")
    print(f"账户日收益条数：{summary['n_days']}；252 日口径年数：{summary['effective_trading_years']:.6f}")
    print(f"累计收益：{summary['total_return']:.6%}")
    print(f"复合年化收益（252 日口径）：{summary['annual_return']:.6%}")
    print(f"日波动率（样本标准差）：{summary['daily_volatility']:.6%}")
    print(f"年化波动率：{summary['annual_volatility']:.6%}")
    print(f"最大回撤幅度（正数）：{summary['max_drawdown']:.6%}")
    print(f"回撤峰值：{summary['drawdown_peak_date']}，净值 {summary['drawdown_peak_nav']:.9f}")
    print(f"回撤谷底：{summary['drawdown_trough_date']}，净值 {summary['drawdown_trough_nav']:.9f}")
    print(f"期末权益：{summary['final_equity']:,.6f}；期末净值：{summary['final_nav']:.9f}")
    print(f"期末现金：{summary['final_cash']:,.6f}；股票数量：{summary['final_holdings_count']}")
    print(f"有成交的执行日：{summary['execution_days_with_trades']}；成交笔数：{summary['trade_count']}")
    print("本课结果目录：", output_dir)


if __name__ == "__main__":
    main()
