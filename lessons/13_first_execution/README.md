# 第 13 步：从目标名单到首次成交与持仓记账

<!-- SNAPSHOT_NOTE -->
## 数据准备说明

本页记录完整快照上的实际运行。通过 GitHub 克隆源码后，先在仓库根目录运行 `python publication/restore_snapshot.py`，恢复同版本的 `data/` 与 `runs/`，再执行本步。[完整数据与大型结果索引](../../publication/ASSET_INDEX.md)保留全部路径和哈希；本页图表与 Notebook 已保存输出可直接阅读。


## 目标：从选股分数走向账户记账

第 12 步已经得到三因子综合分数、前十名股票和每只 10% 的目标权重。本步只处理第一次执行：2020-01-31 收盘形成目标，2020-02-03 开盘尝试买入，再按当天收盘价格计算权益。“想买多少”“允许买多少”“资金够买多少”和“最后持有多少”分别保存。综合分数是排序依据，目标权重是计划，成交与持仓才决定账户损益。

本步使用人工行情。`SYN034` 等代码不对应真实上市公司，日历也只是包含节假日的工作日序列。数量采用复权价格下可分割的小数单位，用于理解现金记账；这些单位不等同于交易所原始股数，这次执行也属于模拟，不是实盘成交。

## 前置文件与运行方式

所有命令在仓库根目录，也就是包含 `pyproject.toml` 的目录执行。前面的步骤已经创建 `.venv` 并安装依赖；在新环境中，先执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
```

本步沿用以下前置文件，保持同一批数据，不重新随机生成样本：

| 输入 | 本步使用的内容 |
| --- | --- |
| [目标名单](../../runs/first_demo_20261107/lesson12_equal_weight_selection/target_portfolio.csv) | 10 个代码、10% 权重、100 万参考资金、执行日期 |
| [完整综合排名](../../runs/first_demo_20261107/lesson12_equal_weight_selection/composite_ranking.csv) | 信号日全部股票的 `composite`，用于确认名单没有被执行日行情改写 |
| [固定模拟输入](../../runs/first_demo_20261107/input/metadata.json) | 同一批模拟价格、市场日历和股票池的来源说明 |
| [固定配置](../../configs/baseline.json) | 初始资金、前十名规则和教学费率 |

运行本步脚本：

```powershell
.\.venv\Scripts\python.exe examples/13_first_execution.py
```

如果第 12 步的结果尚未生成，先按第 10、11、12 步的顺序运行相应脚本。当前教学脚本使用固定目录 `runs/first_demo_20261107`，不会自动读取另行生成的 `runs/my_demo`。重跑本步会覆盖本步的五份结果文件，因此自定义实验另存目录。

![第十二步综合排名图](../../runs/first_demo_20261107/lesson12_equal_weight_selection/composite_selection.png)

这张已有图解释当前名单的形成依据，不表示成交价，也不展示本步收益。阅读时，我把选股依据和交易结果分开核对。

## 时间轴与成交时点检查

时间轴有三个节点：信号日收盘、下一交易日开盘、执行日收盘。2020-01-31 的价格与成交量可以参与收盘后评分，但不能据此回头按当天收盘价建仓。2020-02-03 的开盘价用于模拟成交，收盘价只用于本日最终估值。首次买入前账户里没有股票，因此 1 月 31 日收盘到 2 月 3 日开盘的涨跌不属于新持仓。

下一交易日通过日历查找，不能简单把日期加一。脚本中的关键检查是：

```python
location = calendar.get_loc(signal_date)
if location + 1 >= len(calendar) or calendar[location + 1] != execution_date:
    raise ValueError("执行日必须是信号日之后的下一个交易日。")
```

先用 `get_loc` 找到信号日在市场日历中的位置，再检查后一个位置是否等于保存的执行日。这个检查保证交易时点一致，不衡量预测准确率。随后从完整排名中按 `composite` 降序、代码升序取前十名，并与目标 CSV 的顺序核对；下一天是否上涨不参与替换名单。

## 资金公式：先计算需求，再按现金缩量

设初始现金为 (C_0=1,000,000)，每只股票的名义目标市值为 (V_i=100,000)。复权开盘价为 (P_i^o)，滑点率为 (s=0.0005)，佣金率为 (c=0.0003)。先计算不含费用的目标单位数和含滑点成交价：

$$
q_i^*=\frac{V_i}{P_i^o},\qquad P_i^{fill}=P_i^o(1+s).
$$

直接买足全部目标数量时，所需现金是：

$$
C_{need}=\sum_i q_i^*P_i^{fill}(1+c)=1,000,800.15.
$$

需求超过现金，因此对可执行买单统一缩放：

$$
\alpha=\min(1,C_0/C_{need})=0.9992004897281440,
\qquad q_i=\alpha q_i^*.
$$

缩量后无需从账户外补入手续费，也不会使现金变成负数。这个场景中十只股票的模拟 `can_buy` 都为真，`status_known` 也为真，所以全部进入资金需求计算。真实数据里的未知状态不适用于本人工场景；本步配置 `allow_unknown_status=False`，要求模拟状态明确。

本步复用已经测试过的核心引擎，使首次执行与后续回测采用相同的成交公式：

```python
config.update(start=str(signal_date.date()), end=str(execution_date.date()),
              top_n=len(targets), allow_unknown_status=False)
result = run_backtest(prices, scores, calendar, config)
```

第一行把运行区间限制到信号日与首次执行日，并明确目标数量和状态要求；第二行把价格、信号、完整日历交给同一个引擎。`run_backtest` 返回每日账户、成交、持仓和订单四张表，因此首次买入可以与第 14、15 步的连续账户直接对账。

## SYN034 的逐项手算

保存的模拟价格中，`SYN034` 的开盘价为 `30.842756632269566`，收盘价为 `31.207047767024797`。据此得到：

| 核算字段 | 本次值 |
| --- | ---: |
| 不含费目标数量 (q_i^*) | 3242.252344441026 |
| 含滑点成交价 | 30.858178010586 |
| 资金约束后的成交数量 | 3239.660130387696 |
| 成交金额 `notional` | 99970.0089973008 |
| 佣金 `commission` | 29.9910026992 |
| 以原开盘价衡量的滑点损失 | 49.9600244864 |
| 收盘权重 | 10.0030118866% |

`quantity` 不是整数，是因为教学引擎允许复权单位可分割，并非现实交易所允许任意小数股。买入没有收取卖出税；本项目的 `sell_tax_bps` 只在卖出时作用。固定费率本身是教学参数，不是完整的历史收费表。

## 区分现金账与权益损益账

现金只按实际支付金额变化：

$$
C_{end}=C_0-\sum_i notional_i-\sum_i commission_i.
$$

滑点已经把买入价从 (P_i^o) 推高到 (P_i^{fill})，不能在这个现金公式中再减一次。经济损失则通过另一套权益分解解释：

$$
E_{close}=C_0-commission-slippage
          +\sum_iq_i(P_i^c-P_i^o).
$$

脚本分别核对这两个恒等式：

```python
cash_from_ledger = initial - notional - commission - tax
equity_from_ledger = initial - commission - tax - slippage + intraday_profit
```

第一行是实际现金流口径，第二行是相对未加滑点开盘估值的损益分解。它们保存在 `ledger.csv` 的 `cash`、`equity` 两个 `section`，不能把整张账表所有行相加。`row_type=total` 已经是汇总后的终值，也不能再加进组成项。

## 运行输出与核对结果

这里的“输出”指脚本实际生成的模拟结果，不是预先设定的目标收益。

| 检查项 | 保存结果 |
| --- | ---: |
| 成交笔数 | 10 笔买入 |
| 期末现金 | 0 |
| 佣金 | 299.9100269919 |
| 滑点损失 | 499.6002448640 |
| 买入卖出税 | 0 |
| 经济交易成本合计 | 799.5102718559 |
| 执行后按原开盘价标记的权益 | 999200.4897281440 |
| 持仓开盘到收盘的市值变化 | 11497.3839148395 |
| 收盘权益 | 1010697.8736429836 |
| 收盘净值 | 1.010697873643 |

结果保存为 [daily.csv](../../runs/first_demo_20261107/lesson13_first_execution/daily.csv)、[trades.csv](../../runs/first_demo_20261107/lesson13_first_execution/trades.csv)、[orders.csv](../../runs/first_demo_20261107/lesson13_first_execution/orders.csv)、[positions.csv](../../runs/first_demo_20261107/lesson13_first_execution/positions.csv)、[ledger.csv](../../runs/first_demo_20261107/lesson13_first_execution/ledger.csv)。成交表重点查看 `date`、`signal_date`、`side`、`quantity`、`price`、`notional`、`commission`、`tax`、`slippage_cost`；持仓表用于核对数量、收盘市值与权重；订单表用于区分申请数量与成交数量。

十只股票收盘后并不强制各占 10%。本日最低权重约为 `SYN037` 的 9.8256%，最高约为 `SYN026` 的 10.1094%。等权是执行时的目标市值规则，日内涨跌会造成权重漂移。

## 常见误区与本步验收

目标预算不能直接当作实际成交金额，因为费用使可买数量减少；滑点不能作为两次独立现金扣款，因为成交价已经包含滑点；信号日收盘到执行日开盘的涨幅不能记入首次买入收益，因为那时还没有仓位。为了维持表面上的等权而在收盘时无记录地重新平衡，也会改变已经声明的交易规则。

本步验收包括：成交日期严格晚于信号；名单与第 12 步一致；数量能从预算、开盘价、费率和缩放系数手算复原；现金非负；现金账与权益分解都能解释收盘结果。我更看重这些可以复核的证据，不把“程序已运行”当作已经独立掌握全部交易规则的证明。

本步完成了第一次模拟记账。下一步继续保留这批持仓并逐日估值，在第二次月度调仓时处理旧仓、卖出款、新买单和受限卖出。

[关键代码与完整脚本入口](../../examples/13_first_execution.py) · [下一步：每日估值与第二次调仓](../14_daily_valuation_rebalance/README.md)

<!-- GENERATED_FULL_SOURCE_START -->

## 完整脚本源码

完整实现见 [13_first_execution.py](../../examples/13_first_execution.py)。上文解释关键片段，以下代码与脚本文件一致。

```python
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
```

<!-- GENERATED_FULL_SOURCE_END -->

<!-- GENERATED_NAV_START -->

[项目首页](../../README.md) · [本步 Notebook](lesson.ipynb) · [上一步](../12_equal_weight_selection/README.md) · [下一步](../14_daily_valuation_rebalance/README.md)

<!-- GENERATED_NAV_END -->
