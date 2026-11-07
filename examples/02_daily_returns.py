"""第二课：用复权收盘价计算一只模拟股票的简单日收益率。"""

from pathlib import Path
import pandas as pd

# 沿用上一课的读取、选股和排序。
project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
symbol = "SYN001"
stock = prices.loc[prices["symbol"] == symbol].copy()
stock = stock.sort_values("date").reset_index(drop=True)

# 对齐市场日历：缺失的交易日保留空价格，不能跳过缺口或自动补价。
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
stock = stock.set_index("date").reindex(calendar["date"]).reset_index()

# 本课核心：今天的复权收盘价 / 上一个交易日的复权收盘价 - 1。
stock["prev_adj_close"] = stock["adj_close"].shift(1)
stock["daily_return"] = stock["adj_close"] / stock["prev_adj_close"] - 1

# 单独增加一列百分数，便于阅读；daily_return 仍保存原始小数。
stock["daily_return_pct"] = stock["daily_return"] * 100
columns = ["date", "adj_close", "prev_adj_close", "daily_return", "daily_return_pct"]
print("模拟股票：", symbol)
print("daily_return_pct 的单位为 %；NaN 表示缺失，不能当作零收益。")
print(stock[columns].head(6).to_string(index=False))

# pandas 的简写；fill_method=None 明确不自动补缺失价格。
stock["return_shortcut"] = stock["adj_close"].pct_change(fill_method=None)
max_difference = (stock["daily_return"] - stock["return_shortcut"]).abs().max()
print("\n展开公式与 pct_change 的最大差异：", max_difference)
print("行情记录数：", len(stock))
print("日收益缺失数：", int(stock["daily_return"].isna().sum()))
