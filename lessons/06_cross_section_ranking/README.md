# 第 06 步：我在同一日期比较 40 只股票的动量

<!-- SNAPSHOT_NOTE -->
## 我的数据准备说明

我在本页记录的是完整快照上的实际运行。如果我从 GitHub 克隆源码，我先在仓库根目录运行 `python publication/restore_snapshot.py`，恢复同版本的 `data/` 与 `runs/`，再执行本步。[完整数据与大型结果索引](../../publication/ASSET_INDEX.md)保留全部路径和哈希；本页图表与 Notebook 已保存输出可直接阅读。


## 我的目标与两种比较方向

我在上一节只看 `SYN001` 随时间变化的动量。本步我把同一套公式逐只应用于 40 只人工股票，然后选定同一个日期，按动量从高到低排序。这让我从“这只股票最近涨跌多少”走向“这只股票相对其他股票处在什么位置”。

我区分两个方向：沿同一股票的日期观察，是时间序列比较；固定同一日期、比较多只股票，是横截面比较。我不能把不同日期算出的动量随意放在同一个排名中，因为它们对应不同的市场时点和信息集合。

我的输入仍是固定人工样本，当前选定 `2020-01-31`。这个日期属于模拟工作日日历，不代表真实 A 股当天开市，也不是实际交易建议。脚本只展示前十名，尚未分配资金、发出订单或扣除成本。

我已完成 [第 05 步](../05_momentum_factor/README.md)，在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe examples/06_cross_section_ranking.py
```

## 我固定因子与排名规则

我对每只股票 i 使用同一个历史公式：

$$
M_{i,t}^{(20)}=\frac{P_{i,t}}{P_{i,t-20}}-1.
$$

我仍要求相应 21 个日历价格点全部有效。当前动量方向暂定为“较高值排前”，这是一个需要未来检验的研究假设。排名本身只是一种历史特征的整理，不证明排在前面的股票随后收益更高。

我的展示顺序是：先按动量降序，再按代码升序。第二个条件只是解决并列分数时的确定顺序，不表示代码更小的股票具有更强金融信号。我在本节使用的 `rank=1,2,...` 是展示序号；下一节计算 Spearman 秩相关时，真正的并列值需要平均秩，不能直接沿用代码打破并列后的展示序号。

## 我为什么先按股票分组

```python
factor_tables = []
for symbol, stock in prices.groupby("symbol", sort=True):
    stock = stock.sort_values("date").set_index("date")
    stock = stock.reindex(calendar["date"]).reset_index()
    stock["symbol"] = symbol
```

我创建列表来收集每只股票的小表。`groupby("symbol")` 保证每次计算只面对一个代码，`sort=True` 让分组按代码有序出现。它不是“按代码挑出表现好的一组”，而是防止同一滚动公式跨越股票边界。

循环里先按日期排序，再设日期索引，随后对齐同一份独立日历。重新赋值 `stock["symbol"]=symbol`，是在对齐补出缺失行后明确它属于哪只股票；这不填补价格，也不把未知行情变成已知。我的特征仍只使用当前行及此前的历史数据。

如果我在 73,080 行混合表上直接做 `shift(20)`，很容易把另一只股票的价格当成本股历史价格。即使算出的数字看起来平滑，也没有正确的金融含义。分组、时间排序和独立日历是公式成立的前提，不能靠最终收益好看来替代。

## 我在每组复用完整窗口规则

```python
close = stock["adj_close"].where(stock["adj_close"] > 0)
stock["start_date"] = stock["date"].shift(lookback)
stock["price_20_sessions_ago"] = close.shift(lookback)
valid_price_count = close.rolling(lookback + 1, min_periods=lookback + 1).count()
stock["momentum_20"] = (close / stock["price_20_sessions_ago"] - 1).where(
    valid_price_count == lookback + 1
)
```

我先把非正价格排除。`start_date` 和历史价格使用相同的位移，所以后续能把一个排名值追溯到具体起止日期。`valid_price_count` 要求连续 21 个有效价格位置，避免中间缺口被端点比值掩盖。最后保存的动量仍是小数，没有在计算过程中混入百分数。

```python
factor_values = pd.concat(factor_tables, ignore_index=True)
signal_date = pd.Timestamp("2020-01-31")
snapshot = factor_values.loc[factor_values["date"] == signal_date].copy()
ranked = snapshot.dropna(subset=["momentum_20"]).copy()
```

`concat` 按行拼接各股因子表，`ignore_index=True` 重新生成统一行标签。整张表含多个历史日期没有问题，关键是每个因子值都只由当时及此前的数据生成。随后我选定日期，只比较该截面，并排除无法计算动量的记录。我没有用未来收益筛选当前名单，也没有把缺失因子补为零后参加排名。

## 我怎样建立确定的展示顺序

```python
ranked = ranked.sort_values(
    ["momentum_20", "symbol"], ascending=[False, True]
).reset_index(drop=True)
ranked["rank"] = range(1, len(ranked) + 1)
ranked["momentum_20_pct"] = ranked["momentum_20"] * 100
```

`False` 对应动量降序，`True` 对应代码升序，两个布尔值分别作用于两个排序字段。重排行标签后，我用 `range` 生成从 1 开始的展示名次。百分数列只用于打印，不参与排序计算。若我只打印 `head(10)`，它不会把内存里的其他 30 只股票删除；截面与有效样本数仍应单独记录。

## 我的实际截面结果

当前 `2020-01-31` 截面有 **40 条记录、40 个有效动量、0 个缺失动量**。我的前十名如下，百分数为实际小数因子乘 100 后的适度舍入展示：

| 展示名次 | 人工代码 | 20 日动量 |
| --- | --- | ---: |
| 1 | SYN037 | 15.703985% |
| 2 | SYN008 | 10.858528% |
| 3 | SYN034 | 8.161741% |
| 4 | SYN025 | 1.816338% |
| 5 | SYN029 | 1.328662% |
| 6 | SYN001 | -0.354572% |
| 7 | SYN018 | -0.420423% |
| 8 | SYN004 | -0.770839% |
| 9 | SYN011 | -1.953194% |
| 10 | SYN015 | -2.787643% |

我观察到前十名中有负动量，这并不矛盾：排名表达的是相对位置，不要求绝对上涨。`SYN001` 过去 20 个模拟交易区间略有下跌，但仍优于当前样本中多数股票。反过来，某只股票上涨也不意味着它在当期横截面里排前。

这张表不是策略收益表。第一名的 15.703985% 描述已经发生的历史窗口，不是之后一个月会赚到的数字。我不能把它直接当预期收益，更不能把前十名历史涨幅平均后称为选股回测收益。

## 我把 SYN001 的排名追溯到原始价格

| 我追溯的字段 | 实际记录 |
| --- | ---: |
| 当前信号日期 | 2020-01-31 |
| 窗口起点 | 2020-01-03 |
| 起点复权收盘价 | 21.59631562275345 |
| 终点复权收盘价 | 21.51974115509771 |
| 20 日动量小数 | -0.00354571904733 |
| 动量百分数 | -0.3545719047% |
| 当日展示名次 | 6 / 40 |

我用价格比再次复算 `21.51974115509771/21.59631562275345-1`，得到与表中一致的动量。这个检查把“排名第六”重新连接回我已经熟悉的一只股票、一段日期和两个价格，避免排序以后只剩名次而失去数据来源。

全历史因子表有 **73,080 条记录**，其中 **800 条动量缺失**，有效 **72,280 条**。当前人工数据中，每只股票最初 20 行都在预热，`40×20=800`，因此这个缺失总量与规则一致。若换成真实数据，我不能照搬“全部缺失都只是预热”的结论，还要核对每股覆盖、停牌、价格和成员资格。

## 我说明当前股票池与相对名次的限制

当前四十只人工股票从生成开始就属于固定样本，因此本节没有解决真实历史成员资格问题。真实研究中，我需要知道某只股票在信号时点是否存在、是否属于研究范围，以及退市或被剔除的股票是否仍保留在历史样本里。我不能因为某只股票后来的数据齐全、今天仍能找到，就倒推它在所有过去日期都应该进入同一股票池。

名次也依赖当期比较对象。第六名在四十只股票中的位置，不能直接与第六名在三百只股票中的位置视为同一强弱。即使原始动量完全没变，股票池扩大或缩小也会改变相对顺序。因此我保存截面总数、有效数和缺失数，不能只复制前十行而不交代母样本。

我还不把名次之间的差当作相等的经济差距。第一名和第二名可能相差很大，第六名和第七名可能仅差一点；展示序号并没有保留这些距离信息。后续选择标准化分数、秩或原始值时，我会说明它们各自表达什么。本节同时保存动量小数与排名，正是为了让相对位置仍能追溯到实际因子值。

## 我记录的常见错误

| 我的错误 | 为什么会错 | 我的修正 |
| --- | --- | --- |
| 我把所有日期的动量一起排前十 | 混合了不同信息时点 | 我先固定一个截面日期 |
| 我对全表直接位移 | 历史价格可能来自别的股票 | 我先按代码分组再计算 |
| 我删除缺价日期后再数 20 行 | 20 行不再等于约定日历中的 20 个区间 | 我先对齐独立日历 |
| 我把缺失动量补 0 | 未知值会获得一个虚假的中间位置 | 我排除无效值并报告数量 |
| 我把展示名次用于并列秩相关 | 代码顺序被错误解释为信号强弱 | 我在统计相关时按分数重新计算平均秩 |
| 我把 Top 10 当成已经买入 | 当前脚本没有资金、订单或成本 | 我把排名与实际成交分开 |

## 我的验收记录、结论与下一步

我能解释时间序列与横截面的区别，能把每个排名追溯到该股历史窗口，能核对有效样本数和预热缺失，并能说明负动量为什么仍可能排在前列。本步的结论只是“我已经生成同一信息时点下可复现的历史特征排序”。

我的下一步是 [第 07 步脚本：未来收益与 Rank IC](../../examples/07_forward_returns_rank_ic.py)。我需要建立从信号之后开始的未来标签，再检验当前排名与未来收益排名的关系；在完成这一步之前，我不会把历史排名写成预测成功。

<!-- GENERATED_FULL_SOURCE_START -->

## 我的完整脚本源码

我把本步完整实现保留在 [06_cross_section_ranking.py](../../examples/06_cross_section_ranking.py)。精选代码解释在前文，以下代码与脚本文件一致。

```python
"""第六课：逐股票计算动量，再在同一天做横截面排名。"""

from pathlib import Path
import pandas as pd

project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
lookback = 20

# 1. 每次取出一只股票的历史，复用上一课的计算方法。
factor_tables = []
for symbol, stock in prices.groupby("symbol", sort=True):
    stock = stock.sort_values("date").set_index("date")
    stock = stock.reindex(calendar["date"]).reset_index()
    stock["symbol"] = symbol  # 标明所属股票；不填补任何缺失价格。
    close = stock["adj_close"].where(stock["adj_close"] > 0)
    stock["start_date"] = stock["date"].shift(lookback)
    stock["price_20_sessions_ago"] = close.shift(lookback)
    valid_price_count = close.rolling(lookback + 1, min_periods=lookback + 1).count()
    stock["momentum_20"] = (close / stock["price_20_sessions_ago"] - 1).where(
        valid_price_count == lookback + 1
    )
    factor_tables.append(stock[[
        "date", "symbol", "start_date", "adj_close", "price_20_sessions_ago", "momentum_20",
    ]])

# 2. 将各股票的小表按行拼接，得到全部日期、全部股票的因子表。
factor_values = pd.concat(factor_tables, ignore_index=True)

# 3. 只选同一天；本日期属于模拟工作日日历，不是实际交易安排。
signal_date = pd.Timestamp("2020-01-31")
snapshot = factor_values.loc[factor_values["date"] == signal_date].copy()
ranked = snapshot.dropna(subset=["momentum_20"]).copy()
if ranked.empty:
    raise ValueError("该日没有有效因子，请检查日历、预热长度和缺失行情。")

# 4. 动量从高到低；同分时按代码排序，保证展示顺序确定。
# rank 是展示的顺序号；同分后按代码排序不代表信号强度不同。
ranked = ranked.sort_values(
    ["momentum_20", "symbol"], ascending=[False, True]
).reset_index(drop=True)
ranked["rank"] = range(1, len(ranked) + 1)
ranked["momentum_20_pct"] = ranked["momentum_20"] * 100

# 5. 前十行仅用于展示排序，未在本脚本执行任何组合交易。
columns = ["rank", "symbol", "momentum_20_pct"]
print("数据类型：40 只人工股票；动量百分数列的单位为 %。")
print("横截面日期：", signal_date.date())
print("当日记录数：", len(snapshot))
print("当日有效因子数：", len(ranked))
print("当日缺失因子数：", int(snapshot["momentum_20"].isna().sum()))
print("\n当日动量前 10 名：")
print(ranked[columns].head(10).to_string(index=False))

# 6. 回到熟悉的 SYN001，解释它在同日股票池中的相对位置。
focus_symbol = "SYN001"
focus = ranked.loc[ranked["symbol"] == focus_symbol].iloc[0]
print(f"\n{focus_symbol}：第 {focus['rank']} 名，20 日动量 {focus['momentum_20']:.6%}")
print(f"计算区间：{focus['start_date']:%Y-%m-%d} 至 {focus['date']:%Y-%m-%d}")
print(f"起点价格 {focus['price_20_sessions_ago']:.12f}，终点价格 {focus['adj_close']:.12f}")
print("\n全部历史因子记录数：", len(factor_values))
print("全部历史缺失因子数：", int(factor_values["momentum_20"].isna().sum()))
```

<!-- GENERATED_FULL_SOURCE_END -->

<!-- GENERATED_NAV_START -->

[项目首页](../../README.md) · [本步 Notebook](lesson.ipynb) · [上一步](../05_momentum_factor/README.md) · [下一步](../07_forward_returns_rank_ic/README.md)

<!-- GENERATED_NAV_END -->
