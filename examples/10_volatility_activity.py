"""第十课：补齐波动率和相对成交量，得到原始三因子表；模拟数据。"""

from pathlib import Path
import pandas as pd
from ashare_lab.config import load_config

project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
days = pd.DatetimeIndex(calendar["date"])
config = load_config(project_dir / "configs" / "baseline.json")
lookback = config["lookback"]
short_window = config["activity_short"]
long_window = config["activity_long"]
if config["activity_mode"] != "relative_volume":
    raise ValueError("本课演示相对成交量，请使用 activity_mode=relative_volume 的配置。")

# 1. 每只股票独立计算；缺失交易日只补日期，不补价格或成交量。
factor_tables = []
for symbol, stock in prices.groupby("symbol", sort=True):
    stock = stock.sort_values("date").set_index("date").reindex(days).reset_index()
    stock["symbol"] = symbol
    close = stock["adj_close"].where(stock["adj_close"] > 0)
    volume = stock["volume"].where(stock["volume"] >= 0)

    # 2. 日收益率和原有的 20 日动量；保持完整的 21 价格窗口要求。
    stock["daily_return"] = close / close.shift(1) - 1
    price_count = close.rolling(lookback + 1, min_periods=lookback + 1).count()
    stock["momentum_20"] = (close / close.shift(lookback) - 1).where(
        price_count == lookback + 1
    )

    # 3. 最近 20 个日收益率的样本标准差，日频、未年化。
    stock["volatility_20"] = stock["daily_return"].rolling(
        window=lookback, min_periods=lookback
    ).std(ddof=1)

    # 4. 相对成交量：5 日均量 / 20 日均量，单位为倍数。
    stock["volume_mean_5"] = volume.rolling(short_window, min_periods=short_window).mean()
    stock["volume_mean_20"] = volume.rolling(long_window, min_periods=long_window).mean()
    stock["activity_5_20"] = stock["volume_mean_5"] / stock["volume_mean_20"].where(
        stock["volume_mean_20"] > 0
    )

    factor_tables.append(stock[[
        "date", "symbol", "daily_return", "momentum_20", "volatility_20",
        "volume_mean_5", "volume_mean_20", "activity_5_20",
    ]])

# 5. 拼接原始因子表，记录三个因子是否同时有效。
raw_factors = pd.concat(factor_tables, ignore_index=True)
factor_columns = ["momentum_20", "volatility_20", "activity_5_20"]
raw_factors["all_factors_valid"] = raw_factors[factor_columns].notna().all(axis=1)

# 6. 本课只观察信号日截面和 SYN001 历史；不对不同单位的原始值直接求和。
signal_date = pd.Timestamp("2020-01-31")
snapshot = raw_factors.loc[raw_factors["date"] == signal_date].sort_values("symbol").copy()
focus_symbol = "SYN001"
focus = raw_factors.loc[raw_factors["symbol"] == focus_symbol].sort_values("date").reset_index(drop=True)
row = snapshot.loc[snapshot["symbol"] == focus_symbol].iloc[0]

# 7. 保存数值原始精度，供下一课去极值、标准化和因子合成使用。
output_dir = data_path.parent.parent / "lesson10_raw_factors"
output_dir.mkdir(parents=True, exist_ok=True)
raw_factors.to_csv(output_dir / "raw_factors.csv", index=False, date_format="%Y-%m-%d")
snapshot.to_csv(output_dir / "snapshot_2020-01-31.csv", index=False, date_format="%Y-%m-%d")

print("全部为模拟数据；本课只计算原始因子，未合成分数。")
print("观察日期：", signal_date.date())
print("当日股票数：", len(snapshot))
print("当日三个因子都有效的股票数：", int(snapshot["all_factors_valid"].sum()))
print(f"\n{focus_symbol}：")
print(f"20 日动量：{row['momentum_20']:.6%}")
print(f"20 日波动率（日收益样本标准差，未年化）：{row['volatility_20']:.6%}")
print(f"相对成交量（5 日均量 / 20 日均量）：{row['activity_5_20']:.6f} 倍")
print(f"5 日均量：{row['volume_mean_5']:.6f} 股")
print(f"20 日均量：{row['volume_mean_20']:.6f} 股")
print("\n预热期结束附近：")
print(focus.loc[17:22, ["date", "momentum_20", "volatility_20", "activity_5_20"]].to_string(index=True))
for name in factor_columns:
    index = focus[name].first_valid_index()
    print(f"{name}：首个有效行索引 {index}，日期 {focus.loc[index, 'date']:%Y-%m-%d}")
print("\n本课结果目录：", output_dir)
