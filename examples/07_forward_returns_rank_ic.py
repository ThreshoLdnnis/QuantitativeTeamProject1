"""第七课：未来收益标签与原始动量的单期 Rank IC；全部为模拟数据。"""

from pathlib import Path
import pandas as pd
from ashare_lab.factors import monthly_signal_dates

project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
days = pd.DatetimeIndex(calendar["date"])
lookback = 20

# 1. 复用上一课：每只股票单独计算，只使用当日及之前的价格。
factor_tables = []
for symbol, stock in prices.groupby("symbol", sort=True):
    stock = stock.sort_values("date").set_index("date").reindex(days).reset_index()
    stock["symbol"] = symbol
    close = stock["adj_close"].where(stock["adj_close"] > 0)
    valid_count = close.rolling(lookback + 1, min_periods=lookback + 1).count()
    stock["momentum_20"] = (close / close.shift(lookback) - 1).where(
        valid_count == lookback + 1
    )
    factor_tables.append(stock[["date", "symbol", "momentum_20"]])
factor_values = pd.concat(factor_tables, ignore_index=True)

# 2. 月末收盘信号 -> 下一交易日开盘 -> 下次调仓执行日开盘。
# monthly_signal_dates 返回具有下一执行日的月末日期。
signal_date = pd.Timestamp("2020-01-31")
signal_dates = monthly_signal_dates(days)
if signal_date not in signal_dates:
    raise ValueError("请选择模拟日历中具有下一执行日的月末信号日期。")
signal_index = signal_dates.get_loc(signal_date)
if signal_index + 1 >= len(signal_dates):
    raise ValueError("没有完整的下一持有期，不能构造未来收益标签。")
next_signal_date = signal_dates[signal_index + 1]
entry_date = days[days.get_loc(signal_date) + 1]
exit_date = days[days.get_loc(next_signal_date) + 1]

# 3. 从信号日确定研究对象，再取未来的理论入场、退出价格。
snapshot = factor_values.loc[factor_values["date"] == signal_date].copy()
entry_prices = prices.loc[prices["date"] == entry_date, ["symbol", "adj_open"]].rename(
    columns={"adj_open": "entry_open"}
)
exit_prices = prices.loc[prices["date"] == exit_date, ["symbol", "adj_open"]].rename(
    columns={"adj_open": "exit_open"}
)

# 4. 按股票代码配对，不能假定不同日期的行顺序相同。
paired = snapshot.merge(entry_prices, on="symbol", how="left", validate="one_to_one")
paired = paired.merge(exit_prices, on="symbol", how="left", validate="one_to_one")
paired = paired.dropna(subset=["momentum_20", "entry_open", "exit_open"]).copy()
paired = paired.loc[(paired["entry_open"] > 0) & (paired["exit_open"] > 0)].copy()

# 5. 未来收益只用于事后检验，不放回 signal_date 的动量计算。
# 该标签为复权开盘到开盘的理论毛收益，未计成本、停牌或成交限制。
paired["forward_return"] = paired["exit_open"] / paired["entry_open"] - 1
if (len(paired) < 5 or paired["momentum_20"].nunique() < 2
        or paired["forward_return"].nunique() < 2):
    raise ValueError("有效样本不足或排序变量为常数，不能报告有效 Rank IC。")

# 6. 对同一批有效配对股票排名；并列时使用平均名次。
# 两边都从大到小排，第 1 名都是数值最高者。
paired["factor_rank"] = paired["momentum_20"].rank(method="average", ascending=False)
paired["return_rank"] = paired["forward_return"].rank(method="average", ascending=False)

# 7. 两列秩的 Pearson 相关就是 Spearman/Rank IC，无需 SciPy。
rank_ic = paired["factor_rank"].corr(paired["return_rank"])

# 以下只用于展示；计算中的收益仍然保存为小数。
paired["momentum_pct"] = paired["momentum_20"] * 100
paired["forward_return_pct"] = paired["forward_return"] * 100
view = paired.sort_values(["factor_rank", "symbol"]).reset_index(drop=True)
columns = ["symbol", "momentum_pct", "factor_rank", "forward_return_pct", "return_rank"]
print("全部为模拟数据。momentum_pct、forward_return_pct 两列的单位为 %。")
print("信号日收盘：", signal_date.date())
print("理论入场日开盘：", entry_date.date())
print("下一信号日收盘：", next_signal_date.date())
print("理论退出日开盘：", exit_date.date())
print("有效配对股票数：", len(paired))
print("因缺失或无效价格排除的股票数：", len(snapshot) - len(paired))
print("\n原始动量前 10 名与后续表现：")
print(view[columns].head(10).to_string(index=False))
print(f"\n单期原始动量 Rank IC：{rank_ic:.6f}")
focus = paired.loc[paired["symbol"] == "SYN001"].iloc[0]
print(f"\nSYN001：入场价 {focus['entry_open']:.12f}，退出价 {focus['exit_open']:.12f}")
print(f"理论未来收益：{focus['forward_return']:.6%}")
print(f"因子排名：{focus['factor_rank']:g}；未来收益排名：{focus['return_rank']:g}")
print("\n单期模拟相关不能证明显著性，也不是策略净收益或胜率。")
