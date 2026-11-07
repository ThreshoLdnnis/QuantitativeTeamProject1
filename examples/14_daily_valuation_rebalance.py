"""第十四课：逐日估值、权重漂移、第二次调仓及明确标注的拒卖示例。"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
from ashare_lab.config import load_config
from ashare_lab.data import load_dataset, write_json
from ashare_lab.factors import compute_factors, monthly_signal_dates
from ashare_lab.backtest import run_backtest

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def target_list(factors, signal_date, top_n):
    """只按信号日的完整分数确定名单；没有读取执行日价格或状态。"""
    cross = factors.loc[factors["date"] == signal_date].dropna(subset=["composite"])
    target = cross.sort_values(["composite", "symbol"], ascending=[False, True]).head(top_n).copy()
    if target.empty:
        raise ValueError("信号日没有完整因子，无法生成本课目标名单。")
    target["target_weight"] = 1 / len(target)
    return target


def audit_rebalance(result, prices, days, execution_date, targets):
    """还原调仓前开盘、调仓后开盘和收盘三次估值及现金账。"""
    previous_date = days[days.get_loc(execution_date) - 1]
    previous_day = result.daily.loc[result.daily["date"] == previous_date].iloc[0]
    current_day = result.daily.loc[result.daily["date"] == execution_date].iloc[0]
    previous = result.positions.loc[result.positions["date"] == previous_date,
                                    ["symbol", "quantity"]].rename(columns={"quantity": "before_quantity"})
    after = result.positions.loc[result.positions["date"] == execution_date,
                                ["symbol", "quantity"]].rename(columns={"quantity": "after_quantity"})
    symbols = sorted(set(previous["symbol"]) | set(after["symbol"]) | set(targets["symbol"]))
    marks = prices.loc[prices["date"] == execution_date, ["symbol", "adj_open", "adj_close"]]
    weights = pd.DataFrame({"symbol": symbols}).merge(previous, on="symbol", how="left", validate="one_to_one")
    weights = weights.merge(after, on="symbol", how="left", validate="one_to_one")
    weights = weights.merge(targets[["symbol", "target_weight"]], on="symbol", how="left", validate="one_to_one")
    weights = weights.merge(marks, on="symbol", how="left", validate="one_to_one")
    # 这里填零只表示不存在旧持仓/新持仓/目标，不填补任何行情价格。
    for column in ["before_quantity", "after_quantity", "target_weight"]:
        weights[column] = weights[column].fillna(0)
    if weights[["adj_open", "adj_close"]].isna().any().any():
        raise ValueError("核对表缺少价格，不能填价后继续估值。")

    weights["before_open_value"] = weights["before_quantity"] * weights["adj_open"]
    weights["after_open_value"] = weights["after_quantity"] * weights["adj_open"]
    weights["after_close_value"] = weights["after_quantity"] * weights["adj_close"]
    before_open_equity = previous_day["cash"] + weights["before_open_value"].sum()
    after_open_equity = current_day["cash"] + weights["after_open_value"].sum()
    weights["before_open_weight"] = weights["before_open_value"] / before_open_equity
    weights["after_open_weight"] = weights["after_open_value"] / after_open_equity
    weights["after_close_weight"] = weights["after_close_value"] / current_day["equity"]
    weights["target_value_at_open"] = weights["target_weight"] * before_open_equity
    weights["quantity_change"] = weights["after_quantity"] - weights["before_quantity"]

    trades = result.trades.loc[result.trades["date"] == execution_date]
    orders = result.orders.loc[result.orders["date"] == execution_date]
    sells = trades.loc[trades["side"] == "sell"]
    buys = trades.loc[trades["side"] == "buy"]
    commission = trades["commission"].sum()
    tax = trades["tax"].sum()
    slippage = trades["slippage_cost"].sum()
    cost = commission + tax + slippage

    # 现金账只扣成交额、佣金和税；滑点已经体现在成交价，不能再次扣现金。
    expected_cash = (previous_day["cash"] + sells["notional"].sum()
                     - buys["notional"].sum() - commission - tax)
    assert np.isclose(expected_cash, current_day["cash"], rtol=0, atol=1e-7)
    assert np.isclose(after_open_equity, before_open_equity - cost, rtol=0, atol=1e-7)
    assert np.isclose(current_day["equity"], current_day["cash"] + weights["after_close_value"].sum(), rtol=0, atol=1e-7)
    summary = dict(date=str(execution_date.date()), previous_close_equity=float(previous_day["equity"]),
        before_open_equity=float(before_open_equity), after_open_equity=float(after_open_equity),
        close_equity=float(current_day["equity"]), nav=float(current_day["nav"]),
        daily_return=float(current_day["return"]), cash=float(current_day["cash"]),
        commission=float(commission), sell_tax=float(tax), slippage=float(slippage), total_cost=float(cost),
        sell_count=len(sells), buy_count=len(buys), rejected_orders=int(orders["status"].eq("rejected").sum()),
        holdings_count=int(current_day["holdings_count"]))
    ledger = pd.DataFrame([
        ("cash", "调仓前现金", float(previous_day["cash"])),
        ("cash", "卖出成交额", float(sells["notional"].sum())),
        ("cash", "买入成交额", -float(buys["notional"].sum())),
        ("cash", "佣金", -float(commission)),
        ("cash", "卖出税", -float(tax)),
        ("cash_total", "调仓后现金", float(current_day["cash"])),
        ("equity", "调仓前开盘权益", float(before_open_equity)),
        ("equity", "佣金", -float(commission)),
        ("equity", "卖出税", -float(tax)),
        ("equity", "滑点", -float(slippage)),
        ("equity", "调仓后持仓日内市值变化", float(current_day["equity"] - after_open_equity)),
        ("equity_total", "收盘权益", float(current_day["equity"])),
    ], columns=["section", "category", "amount"])
    return weights, ledger, summary


def save_result(result, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name in ["daily", "trades", "orders", "positions"]:
        getattr(result, name).to_csv(folder / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    # 每个交易日核对权益恒等式，价格缺失则由引擎直接报错。
    invested = result.positions.groupby("date")["market_value"].sum().reindex(result.daily["date"], fill_value=0)
    assert np.allclose(result.daily["equity"], result.daily["cash"].to_numpy() + invested.to_numpy(), rtol=0, atol=1e-7)
    assert (result.daily["cash"] >= -1e-7).all()
    assert (result.trades["date"] > result.trades["signal_date"]).all()


def main():
    project_dir = Path(__file__).resolve().parents[1]
    run_dir = project_dir / "runs" / "first_demo_20261107"
    prices, universe, days, _ = load_dataset(run_dir / "input")
    config = load_config(project_dir / "configs" / "baseline.json")
    config["calendar_dates"] = days.strftime("%Y-%m-%d").tolist()
    factors = compute_factors(prices, universe, config)

    # 1. 接续上一课目标组合的信号日期，找到第二次月末信号与执行日。
    prior_targets = pd.read_csv(run_dir / "lesson12_equal_weight_selection" / "target_portfolio.csv",
                                dtype={"symbol": "string"}, parse_dates=["date", "execution_date"])
    first_signal = prior_targets["date"].iloc[0]
    signals = monthly_signal_dates(days)
    second_signal = signals[signals.get_loc(first_signal) + 1]
    first_execution = days[days.get_loc(first_signal) + 1]
    second_execution = days[days.get_loc(second_signal) + 1]
    lesson_config = dict(config, start=str(first_signal.date()), end=str(second_execution.date()),
                        splits={"lesson": [str(first_signal.date()), str(second_execution.date())]})

    # 2. 接上已实现的引擎：逐日估值，只有到执行日才先卖后买。
    result = run_backtest(prices, factors, days, lesson_config)
    first_targets = target_list(factors, first_signal, config["top_n"])
    second_targets = target_list(factors, second_signal, config["top_n"])
    assert set(first_targets["symbol"]) == set(prior_targets["symbol"])
    weights, ledger, summary = audit_rebalance(result, prices, days, second_execution, second_targets)
    output_dir = run_dir / "lesson14_daily_rebalance"
    save_result(result, output_dir)
    weights.to_csv(output_dir / "rebalance_weights.csv", index=False)
    ledger.to_csv(output_dir / "rebalance_ledger.csv", index=False)
    second_targets.to_csv(output_dir / "second_signal_targets.csv", index=False, date_format="%Y-%m-%d")
    write_json(output_dir / "rebalance_summary.json", summary)

    # 3. 2 月持仓数量不变；收益、净值和权重随收盘价格变化。
    middle = result.trades.loc[(result.trades["date"] > first_execution) &
                                (result.trades["date"] < second_execution)]
    assert middle.empty

    # 4. 单独的反事实教学示例：复制行情，只禁止 SYN034 在第二执行日卖出。
    # 这不是原始数据中的事件，也不会修改 input/prices.csv。
    removed = sorted(set(first_targets["symbol"]) - set(second_targets["symbol"]))
    blocked_summary = None
    if removed:
        blocked_symbol = "SYN034" if "SYN034" in removed else removed[0]
        modified = prices.copy()
        mask = modified["date"].eq(second_execution) & modified["symbol"].eq(blocked_symbol)
        assert mask.sum() == 1 and bool(modified.loc[mask, "can_sell"].iloc[0])
        modified.loc[mask, "can_sell"] = False
        scenario = run_backtest(modified, factors, days, lesson_config)
        scenario_dir = output_dir / "blocked_sell_demo"
        save_result(scenario, scenario_dir)
        scenario_weights, scenario_ledger, blocked_summary = audit_rebalance(
            scenario, modified, days, second_execution, second_targets)
        scenario_weights.to_csv(scenario_dir / "rebalance_weights.csv", index=False)
        scenario_ledger.to_csv(scenario_dir / "rebalance_ledger.csv", index=False)
        write_json(scenario_dir / "summary.json", blocked_summary)
        write_json(scenario_dir / "scenario_note.json", {
            "kind": "counterfactual_teaching_override", "symbol": blocked_symbol,
            "date": str(second_execution.date()), "override": "can_sell=False",
            "source_unchanged": True, "claim": "Artificial example, not an observed market event.",
        })
        blocked_order = scenario.orders.loc[scenario.orders["date"].eq(second_execution) &
                                            scenario.orders["symbol"].eq(blocked_symbol)]
        assert len(blocked_order) == 1
        assert blocked_order["status"].iloc[0] == "rejected"
        assert blocked_order["filled_quantity"].iloc[0] == 0
        kept = scenario_weights.loc[scenario_weights["symbol"].eq(blocked_symbol)].iloc[0]
        assert kept["before_quantity"] > 0
        assert np.isclose(kept["before_quantity"], kept["after_quantity"], rtol=0, atol=1e-10)

    # 5. 画基准场景的连续净值；反事实场景单独保存，不混入这条曲线。
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    fig, ax = plt.subplots(figsize=(11, 5.5), layout="constrained")
    daily = result.daily
    ax.plot(daily["date"], daily["nav"], color="#3268A8", marker="o", markersize=3.6, linewidth=1.5)
    ax.axhline(1, color="#747D86", linestyle="--", linewidth=0.9)
    ax.set_ylim(min(0.995, daily["nav"].min() - 0.006), daily["nav"].max() + 0.012)
    for date, text, offset in [
        (first_execution, "首次开盘买入", (22, -40)),
        (second_execution, "第二次开盘调仓", (-145, 62)),
    ]:
        nav = daily.loc[daily["date"] == date, "nav"].iloc[0]
        ax.scatter(date, nav, color="#B46A31", s=42, zorder=5)
        ax.annotate(f"{text} {date:%m-%d}\n收盘净值 {nav:.6f}", xy=(date, nav),
                    xytext=offset, textcoords="offset points", fontsize=10,
                    arrowprops={"arrowstyle": "->", "color": "#747D86"})
    tick_indices = sorted({0, len(daily) // 4, len(daily) // 2, len(daily) * 3 // 4, len(daily) - 1})
    ax.set_xticks(daily["date"].iloc[tick_indices])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.set_xlim(daily["date"].iloc[0] - pd.Timedelta(days=0.5),
                daily["date"].iloc[-1] + pd.Timedelta(days=0.5))
    ax.set_title("三因子组合：首次买入到第二次调仓（模拟数据）", fontsize=16, pad=14)
    ax.set_ylabel("组合净值（初始资金 = 1，含教学交易费用）")
    ax.set_xlabel("交易日（持仓按每日收盘估值；最后一天仍持有股票）")
    ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(output_dir / "daily_nav.png", dpi=180)
    plt.close(fig)

    print("全部为模拟行情、复权价格小数持仓单位；费率为固定教学参数。")
    print("\n每日权益与净值：")
    print(result.daily.to_string(index=False))
    print("\n第二次目标名单：", second_targets["symbol"].tolist())
    print("保留：", sorted(set(first_targets["symbol"]) & set(second_targets["symbol"])))
    print("换出：", removed)
    print("换入：", sorted(set(second_targets["symbol"]) - set(first_targets["symbol"])))
    print("\n第二次调仓核对：", summary)
    print("\n当天订单：")
    print(result.orders.loc[result.orders["date"] == second_execution].to_string(index=False))
    if blocked_summary is not None:
        print("\n人为拒卖示例（原始行情未改动）：", blocked_summary)
    print("\n本课结果目录：", output_dir)


if __name__ == "__main__":
    main()
