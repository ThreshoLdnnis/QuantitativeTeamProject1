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
