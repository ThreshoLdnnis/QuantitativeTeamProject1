"""第三课：复利累计收益与单只模拟股票的理论持有净值。"""

from pathlib import Path
import pandas as pd

# 沿用前两课：读取数据、筛选一只股票、对齐模拟交易日历。
project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
symbol = "SYN001"
stock = prices.loc[prices["symbol"] == symbol].copy()
stock = stock.sort_values("date").reset_index(drop=True)
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
stock = stock.set_index("date").reindex(calendar["date"]).reset_index()

# 本课交叉核对需要完整价格；真实缺失行情应先调查，不能自动补价。
if stock.empty or stock["adj_close"].isna().any() or (stock["adj_close"] <= 0).any():
    raise ValueError("本课需要完整且为正的复权收盘价，请先检查股票代码和缺失行情。")

# 1. 日收益率；第一天没有前一日价格，所以仍然保留 NaN。
stock["daily_return"] = stock["adj_close"] / stock["adj_close"].shift(1) - 1

# 2. 把日收益率转换为财富增长倍数，例如 +3% 对应 1.03。
growth_factor = 1 + stock["daily_return"]

# 3. 以第一天收盘为估值起点，起点净值设为 1。
# 这里只设置连乘起点，没有把第一天的未知日收益改成 0。
growth_factor.iloc[0] = 1.0

# 4. 按时间顺序连乘。若中途出现未知值，不跳过它继续计算。
stock["nav"] = growth_factor.cumprod(skipna=False)

# 5. 净值减去初始的 1，就是从起点至当天的累计收益率。
stock["cumulative_return"] = stock["nav"] - 1

# 6. 假设初始资金为 1 万元，后续没有追加或取出资金。
# 这是连续持有这只股票、忽略费用的理论财富序列。
initial_capital = 10_000.0
stock["wealth"] = initial_capital * stock["nav"]

# 7. 仅作反例：把每天的简单收益率直接相加，会得到不同结果。
stock["wrong_sum_of_returns"] = stock["daily_return"].cumsum()

columns = ["date", "adj_close", "daily_return", "nav", "cumulative_return", "wealth"]
print("模拟股票：", symbol)
print("起点为第一天收盘，nav = 1；收益率列保存小数。")
print(stock[columns].head(6).to_string(index=False))

print("\n只看起点后的前两个收益区间：")
row = stock.iloc[2]
print(f"日期：{row['date'].date()}")
print(f"正确累计收益：{row['cumulative_return']:.6%}")
print(f"错误的直接相加：{row['wrong_sum_of_returns']:.6%}")

# 8. 完整、统一复权口径下，净值还应等于当日价格 / 起点价格。
nav_from_price = stock["adj_close"] / stock["adj_close"].iloc[0]
max_difference = (stock["nav"] - nav_from_price).abs().max()
print("\n连乘净值与价格比净值的最大差异：", max_difference)
print("第一天的日收益仍为缺失值：", bool(pd.isna(stock["daily_return"].iloc[0])))
print("\n期末结果：")
print(stock[columns].tail(1).to_string(index=False))
