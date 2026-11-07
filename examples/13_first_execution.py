"""第十三课：把第十二课的目标名单执行为第一笔成交和持仓记账；模拟数据。

本课只运行首次成交，复用项目回测引擎。单位为复权价格下的小数单位，
不等同于交易所原始股数。下一课继续跟踪这些持仓并处理第二次调仓。
"""

from pathlib import Path

import pandas as pd

from ashare_lab.backtest import run_backtest
from ashare_lab.config import load_config
from ashare_lab.data import load_dataset


def run_first_execution(project_dir):
    """读取已经形成的排名，返回首次成交结果和两套会计核对表。"""
    project_dir = Path(project_dir)
    run_dir = project_dir / "runs" / "first_demo_20261107"
    lesson12 = run_dir / "lesson12_equal_weight_selection"
    targets = pd.read_csv(
        lesson12 / "target_portfolio.csv", dtype={"symbol": "string"},
        parse_dates=["date", "execution_date"],
    )
    ranking = pd.read_csv(
        lesson12 / "composite_ranking.csv", dtype={"symbol": "string"},
        parse_dates=["date"],
    )
    if targets.empty or targets["date"].nunique() != 1 or targets["execution_date"].nunique() != 1:
        raise ValueError("本课要求同一信号日、同一执行日的非空目标名单。")
    if targets["symbol"].duplicated().any():
        raise ValueError("目标名单含有重复股票代码。")
    signal_date = targets["date"].iloc[0]
    execution_date = targets["execution_date"].iloc[0]
    prices, _, calendar, _ = load_dataset(run_dir / "input")
    location = calendar.get_loc(signal_date)
    if location + 1 >= len(calendar) or calendar[location + 1] != execution_date:
        raise ValueError("执行日必须是信号日之后的下一个交易日。")

    # 排名仍来自信号日收盘；下一天行情只用于执行，不能改写选股名单。
    scores = ranking.loc[ranking["date"] == signal_date, ["date", "symbol", "composite"]].copy()
    expected = scores.dropna(subset=["composite"]).sort_values(
        ["composite", "symbol"], ascending=[False, True]
    ).head(len(targets))["symbol"].tolist()
    if expected != targets["symbol"].tolist():
        raise ValueError("目标名单与保存的综合排名不一致，请先重新运行第十二课。")

    config = load_config(project_dir / "configs" / "baseline.json")
    if (targets["reference_capital"] - config["initial_cash"]).abs().max() > 1e-6:
        raise ValueError("目标预算与当前初始资金不同，请先重新运行第十二课。")
    config.update(start=str(signal_date.date()), end=str(execution_date.date()),
                  top_n=len(targets), allow_unknown_status=False)

    # 引擎先尝试按开盘价计算等权目标单位数，再把滑点与佣金纳入可用现金。
    # 首次买入前没有股票，所以不会获得上一收盘到本次开盘之间的涨跌。
    result = run_backtest(prices, scores, calendar, config)
    trades = result.trades
    if trades.empty or not trades["side"].eq("buy").all() or not trades["date"].eq(execution_date).all():
        raise ValueError("本课只接受首次执行日的买入成交，请检查日期和输入文件。")

    opening = prices.loc[prices["date"] == execution_date, ["symbol", "adj_open", "adj_close"]]
    marked = trades.merge(opening, on="symbol", how="left", validate="one_to_one")
    initial = float(config["initial_cash"])
    notional = float(trades["notional"].sum())
    commission = float(trades["commission"].sum())
    tax = float(trades["tax"].sum())
    slippage = float(trades["slippage_cost"].sum())
    intraday_profit = float((marked["quantity"] * (marked["adj_close"] - marked["adj_open"])).sum())
    last_day = result.daily.iloc[-1]

    # 核对一：现金只扣成交金额和费用。成交价已经包含滑点，不能再扣一次。
    cash_from_ledger = initial - notional - commission - tax
    # 核对二：以未加滑点的开盘价估值，权益等于初始资金减成本加日内损益。
    equity_from_ledger = initial - commission - tax - slippage + intraday_profit
    if abs(cash_from_ledger - last_day["cash"]) > 1e-6:
        raise ArithmeticError("现金记账与引擎现金不一致。")
    if abs(equity_from_ledger - last_day["equity"]) > 1e-6:
        raise ArithmeticError("成本和日内损益未能解释收盘权益。")

    # 两个 section 是不同的核对口径，不能把整张表的所有金额一起相加。
    ledger = pd.DataFrame([
        ("cash", "initial_cash", initial, "component"),
        ("cash", "executed_buy_notional", -notional, "component"),
        ("cash", "commission", -commission, "component"),
        ("cash", "sell_tax", -tax, "component"),
        ("cash", "ending_cash", float(last_day["cash"]), "total"),
        ("equity", "initial_equity", initial, "component"),
        ("equity", "commission", -commission, "component"),
        ("equity", "sell_tax", -tax, "component"),
        ("equity", "slippage", -slippage, "component"),
        ("equity", "intraday_pnl", intraday_profit, "component"),
        ("equity", "closing_equity", float(last_day["equity"]), "total"),
    ], columns=["section", "category", "amount", "row_type"])
    return result, ledger


def main():
    project_dir = Path(__file__).resolve().parents[1]
    result, ledger = run_first_execution(project_dir)
    output_dir = project_dir / "runs" / "first_demo_20261107" / "lesson13_first_execution"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in [("daily", result.daily), ("trades", result.trades),
                        ("orders", result.orders), ("positions", result.positions), ("ledger", ledger)]:
        frame.to_csv(output_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")

    day = result.daily.iloc[-1]
    print("模拟数据；本课只记录首次成交，数量为复权价格下的小数单位。")
    print("信号日收盘：", result.trades["signal_date"].iloc[0].date())
    print("执行日开盘：", result.trades["date"].iloc[0].date())
    print("\n实际成交：")
    print(result.trades[["symbol", "quantity", "price", "notional", "commission", "tax", "slippage_cost"]]
          .to_string(index=False, float_format=lambda value: f"{value:.10f}"))
    print(f"\n剩余现金：{day['cash']:.10f}")
    print(f"佣金：{result.trades['commission'].sum():.10f}")
    print(f"滑点损失：{result.trades['slippage_cost'].sum():.10f}")
    print(f"买入印花税：{result.trades['tax'].sum():.10f}")
    print(f"交易成本合计：{day['cost']:.10f}")
    print(f"收盘权益：{day['equity']:.10f}")
    print(f"收盘净值：{day['nav']:.12f}")
    print("\n收盘持仓权重：")
    print(result.positions[["symbol", "quantity", "market_value", "weight"]]
          .to_string(index=False, float_format=lambda value: f"{value:.10f}"))
    print("目标权重为10%；费用和日内价格变化会使收盘权重发生漂移。")
    print("现金只扣成交金额和费用；滑点已经体现在成交价中。")
    print("两个独立核对口径已通过：现金账户、初始权益减成本加日内损益。")
    print("结果目录：", output_dir)


if __name__ == "__main__":
    main()
