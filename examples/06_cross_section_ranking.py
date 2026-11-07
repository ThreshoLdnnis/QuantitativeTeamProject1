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
