# 第 05 步：第一个滚动因子——20 日动量

<!-- SNAPSHOT_NOTE -->
## 数据准备

本页记录的是完整快照上的实际运行。从 GitHub 克隆源码后，先在仓库根目录运行 `python publication/restore_snapshot.py`，恢复同版本的 `data/` 与 `runs/`，再执行本步。[完整数据与大型结果索引](../../publication/ASSET_INDEX.md)保留全部路径和哈希；本页图表与 Notebook 已保存输出可直接阅读。


## 目标与研究假设

前面已经计算了从固定起点到当天的累计收益，本步开始构建随日期变化的特征。第一个因子是 20 个模拟交易区间的动量：在每个当前日期，比较今天与 20 个交易区间前的复权收盘价。

我把“近期上涨较多的股票，之后可能继续相对走强”写成需要检验的假设，没有把它当作已被当前数据证明的结论。20 日窗口较短，真实市场也可能出现反转；本步只实现和核对历史特征，尚未使用未来收益检验有效性，更没有完成策略交易。

前置内容是 [第 03 步](../03_cumulative_returns/README.md) 的复利公式与独立日历对齐。在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe examples/05_momentum_factor.py
```

输入仍是固定人工样本的 `SYN001`，不会因为计算结果为负而换股票。脚本只打印中间表和核对结果，不修改原始行情。

## 公式、时点与窗口数量

设 `P_t` 为当前日期复权收盘价，20 日动量为：

$$
M_t^{(20)}=\frac{P_t}{P_{t-20}}-1
=\prod_{j=t-19}^{t}(1+r_j)-1.
$$

从 `t-20` 到 t 含有 **21 个价格点、20 个相邻收益区间**。这就是“20 日动量需要 21 个收盘价”的原因，不是窗口参数写错。这里的 20 指输入日历中的交易区间，不是直接从日历日期减去 20 个自然日，也不是拿 20 个价格只构成 19 段变化。

因子在 t 日收盘后才包含完整的 t 日价格，所以后续若拿它选股，不能假设已经按 t 日收盘价成交。这里先明确这一信息可得时点；后续订单执行会使用下一交易日开盘。

## 历史价格处理

```python
lookback = 20
close = stock["adj_close"].where(stock["adj_close"] > 0)
stock["price_20_sessions_ago"] = close.shift(lookback)
```

`lookback` 是显式设置的研究参数，不是程序从最终测试收益中挑选的最优数字。第二行只保留正价格；无效的非正数变成缺失，避免除以零或解释负股价。第三行让当前行读取 20 个日历位置之前的历史价格。

计算前已筛选单股、按日期排序，并对齐独立日历，因此 `shift(20)` 才能解释为 20 个模拟交易区间前。若先删除缺价日期再做位移，窗口可能偷偷跨过缺口；对多股混合表做位移，还可能引用另一只股票的价格。

## 完整窗口检查

```python
valid_price_count = close.rolling(
    window=lookback + 1,
    min_periods=lookback + 1,
).count()
stock["momentum_20"] = close / stock["price_20_sessions_ago"] - 1
stock["momentum_20"] = stock["momentum_20"].where(
    valid_price_count == lookback + 1
)
```

`rolling` 为当前及此前连续 21 个日历位置建立窗口，`count()` 统计有效价格数量。`min_periods=21` 要求有足够历史才参与当前检查。随后先计算端点价格比，再用 `.where(...)` 保留完整有效窗口。

数学上，只用端点价格也能定义一个区间价格变化。但本项目额外要求中间 21 个价格全部有效，目的是保持与 20 个日收益连乘的一致性，并且不悄悄绕过未知交易日。这个要求是当前研究的数据完整性规则，不是所有动量研究都必须采取的唯一做法。方法说明中需要保留这个约定，避免将实现习惯误认为普遍定理。

如果窗口中间缺一日，即使两个端点都有价格，本项目仍将该日动量留空，既不补 0，也不用未来价格填补或通过缩短窗口凑出一个数字。若真实停牌有可靠估值记录，可以在数据层先建立明确规则；本步不自行猜测。

## 新增字段

| 字段 | 含义 |
| --- | --- |
| `price_20_sessions_ago` | 与当前行对齐的 20 个模拟交易区间前的复权收盘价 |
| `momentum_20` | 完整窗口下的历史累计简单收益，小数形式 |
| `momentum_20_pct` | 动量乘 100 的阅读列，数字单位为百分数 |
| `valid_price_count` | 内存中的完整性核对序列，不是另一个预测因子 |

动量与上一节的固定起点累计收益需要区分：固定起点累计收益的分母一直是首日价格；滚动动量的分母会随 t 向前移动。两者都用价格比，但回答的是不同问题。

## 第一个有效窗口

| 核对项目 | 当前固定人工样本结果 |
| --- | ---: |
| 首个有效索引 | 20，索引从 0 开始 |
| 起点 | 2019-01-01 |
| 终点 | 2019-01-29 |
| 起点复权收盘价 | 26.327305296402876 |
| 终点复权收盘价 | 24.687272370585195 |
| 价格记录数 | 21 |
| 相邻收益区间数 | 20 |
| 20 日动量 | -0.06229399125180357 |
| 百分数展示 | -6.2293991252% |

先计算 `24.687272370585195/26.327305296402876-1`，得到约 -6.229399%。它说明当前人工股票在这个历史窗口里下跌，不说明它未来一定上涨或下跌。

前 20 行没有足够历史，动量为空；第 21 个价格点、即索引 20 才首次有效。当前单股总行数 1,827，动量缺失 **20** 行，有效 **1,807** 行。这个缺失数量与预热长度一致；若换一份数据后缺失更多，还要排查中间行情和非正价格，不能把所有缺失都归因于正常预热。

## 用日收益连乘核对

```python
daily_return = close / close.shift(1) - 1
window_returns = daily_return.iloc[start_index + 1:first_index + 1]
momentum_from_returns = (1 + window_returns).prod(skipna=False) - 1
```

从起点之后第一段收益开始截取，所以左端是 `start_index+1`；Python 切片不包含右端，因此右边写 `first_index+1` 才会纳入终点那一段收益。这个细节与“21 个价格、20 段收益”完全对应。

当前日收益连乘结果为 **-0.06229399125180368**，与价格比差约 **1.1102230246251565×10^-16**。直接把这 20 个日收益相加则约为 **-5.7259007533%**，不是正确窗口回报。这个对照延续了上一节的复利概念，而不是引入一套新算法。

## 特征数值与研究判断

动量是过去一段时间的相对价格变化，不是便宜或昂贵的估值指标。一只股票不会仅因名义价格较高就得到更高分；同样涨一元的两只不同价格股票，也不能视为具有相同动量。价格比消除了直接比较绝对价差的量纲问题，但不会消除行业、市值、风险和市场环境等差异，后续仍可能需要相应对照。

二十个区间是第一版固定研究规则，本步并未证明这个窗口最优。以后若比较其他窗口，需要先记录比较范围和选择依据，并留意反复试验带来的选择偏差；不能在已经查看的测试结果上反复调整，最后只留下最好的一次。当前脚本的任务是把一个定义清楚的基线做对。

历史动量与未来收益使用不同的字段名。当前值即使很大，仍只表明过去涨得多；它是否预测之后回报，需要下一阶段单独构造标签来检验。若未来检验没有支持趋势延续，合理结论可以是“这组数据不支持当前假设”，而不是在同一测试样本上立即反向并宣称发现稳定规律。

## 常见错误与核对方法

| 错误操作 | 为什么会错 | 核对方法 |
| --- | --- | --- |
| 把 `shift(20)` 换成自然日期减 20 天 | 自然日与交易区间不一致 | 查看窗口实际起止日期和价格记录数 |
| 只取 20 个价格算 20 段收益 | 20 个价格只有 19 段相邻变化 | 分别数价格点与收益区间 |
| 用负的位移生成“历史因子” | 负位移会把未来价格带到当前行 | 只允许当前及此前数据参与特征 |
| 把缺失动量填为 0 | 未知被伪装成确定的零涨幅 | 保留空值并记录有效样本数 |
| 只看端点而忽略项目的完整窗口规则 | 与后续连乘和缺失口径不一致 | 检查有效价格数量是否为 21 |
| 看到负动量便临时改方向 | 观察一个历史特征不等于检验方向 | 将方向作为后续预先说明的研究假设 |

## 验收记录与下一步

本步已将第一个有效窗口的索引、日期、价格点数量、公式和连乘结果逐项对上，也解释了为何最初 20 行为空。结论仅是“20 日动量已按明确定义正确计算”，尚不能据此判断“动量可以赚钱”。

下一步进入 [第 06 步](../06_cross_section_ranking/README.md)，对每只人工股票分别计算同一因子，再把同一天的股票放到一起排序。单股历史变化会转成一个横截面的相对位置，但预测能力仍需未来标签检验。

<!-- GENERATED_FULL_SOURCE_START -->

## 完整脚本源码

本步完整实现见 [05_momentum_factor.py](../../examples/05_momentum_factor.py)。前文解释了关键代码，以下保留与脚本文件一致的完整源码。

```python
"""第五课：SYN001 的 20 个模拟交易区间动量因子。"""

from pathlib import Path
import pandas as pd

# 沿用前几课：读取、筛选单只股票、按日期排序并对齐日历。
project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
symbol = "SYN001"
stock = prices.loc[prices["symbol"] == symbol].copy()
stock = stock.sort_values("date").reset_index(drop=True)
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
stock = stock.set_index("date").reindex(calendar["date"]).reset_index()

# 1. 回看 20 个日历中的交易区间；非正价格视为无效。
lookback = 20
close = stock["adj_close"].where(stock["adj_close"] > 0)

# 2. 在今天这一行，放入 20 个交易区间前的价格。
stock["price_20_sessions_ago"] = close.shift(lookback)

# 3. 本项目额外要求：包含当日在内的 21 个价格全部有效。
valid_price_count = close.rolling(
    window=lookback + 1,
    min_periods=lookback + 1,
).count()

# 4. 动量就是这 20 个交易区间的累计简单收益率。
stock["momentum_20"] = close / stock["price_20_sessions_ago"] - 1

# 5. 中间缺失价格的窗口保留为空；不补零，也不跳过缺失交易日。
stock["momentum_20"] = stock["momentum_20"].where(valid_price_count == lookback + 1)

# 6. 百分数列用于阅读，计算仍使用原始小数列 momentum_20。
stock["momentum_20_pct"] = stock["momentum_20"] * 100
columns = ["date", "adj_close", "price_20_sessions_ago", "momentum_20", "momentum_20_pct"]
print("模拟股票：", symbol)
print("以下索引从 0 开始；momentum_20_pct 的数字单位为 %。")
print(stock[columns].head(23).to_string(index=True))

# 7. 取第一个有效窗口，明确核对其起点、终点和记录数量。
first_index = stock["momentum_20"].first_valid_index()
if first_index is None:
    raise ValueError("没有完整的 21 个有效价格，请检查股票代码、数据长度和缺失行情。")
start_index = first_index - lookback
window = stock.loc[start_index:first_index, ["date", "adj_close"]]
first = stock.loc[first_index]
start = stock.loc[start_index]
print("\n第一个有效窗口：")
print(f"起点：{start['date']:%Y-%m-%d}，复权收盘价：{start['adj_close']:.12f}")
print(f"终点：{first['date']:%Y-%m-%d}，复权收盘价：{first['adj_close']:.12f}")
print(f"价格记录数：{len(window)}；相邻收益区间数：{len(window) - 1}")
print(f"动量：{first['momentum_20']:.6%}")

# 8. 用上一课的复利公式交叉核对：只连乘这 20 个区间。
daily_return = close / close.shift(1) - 1
window_returns = daily_return.iloc[start_index + 1:first_index + 1]
momentum_from_returns = (1 + window_returns).prod(skipna=False) - 1
print(f"20 个日收益连乘的结果：{momentum_from_returns:.6%}")
print("两种正确算法的差异：", abs(first["momentum_20"] - momentum_from_returns))
print(f"直接相加的错误对照：{window_returns.sum():.6%}")
print("\n动量缺失行数：", int(stock["momentum_20"].isna().sum()))
print("有效动量行数：", int(stock["momentum_20"].notna().sum()))
```

<!-- GENERATED_FULL_SOURCE_END -->

<!-- GENERATED_NAV_START -->

[项目首页](../../README.md) · [本步 Notebook](lesson.ipynb) · [上一步](../04_nav_drawdown/README.md) · [下一步](../06_cross_section_ranking/README.md)

<!-- GENERATED_NAV_END -->
