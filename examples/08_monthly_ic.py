"""第八课：原始动量的月度 Rank IC、平均 IC、未年化 ICIR；模拟数据。"""

from pathlib import Path
import pandas as pd
import matplotlib
from ashare_lab.config import load_config

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
days = pd.DatetimeIndex(calendar["date"])
config = load_config(project_dir / "configs" / "baseline.json")
lookback = config["lookback"]

# 1. 复用前两课：每只股票单独计算过去 20 个交易区间的原始动量。
factor_tables = []
for symbol, stock in prices.groupby("symbol", sort=True):
    stock = stock.sort_values("date").set_index("date").reindex(days).reset_index()
    stock["symbol"] = symbol
    close = stock["adj_close"].where(stock["adj_close"] > 0)
    count = close.rolling(lookback + 1, min_periods=lookback + 1).count()
    stock["momentum_20"] = (close / close.shift(lookback) - 1).where(count == lookback + 1)
    factor_tables.append(stock[["date", "symbol", "momentum_20"]])
factor_values = pd.concat(factor_tables, ignore_index=True)

# 2. 取每个月的最后一个模拟交易日，保留末尾不完整月份以便记录原因。
month_ends = pd.Series(days, index=days).groupby(days.to_period("M")).last()
signal_dates = pd.DatetimeIndex(month_ends.to_numpy())


def next_session(date):
    """没有下一交易日时返回缺失日期，不制造未来价格。"""
    if pd.isna(date):
        return pd.NaT
    position = days.get_loc(date)
    return days[position + 1] if position + 1 < len(days) else pd.NaT


# 3. 每个信号日重复上一课的标签、配对、排名和相关计算。
records = []
for i, signal_date in enumerate(signal_dates):
    if not pd.Timestamp(config["start"]) <= signal_date <= pd.Timestamp(config["end"]):
        continue
    split = next((name for name, bounds in config["splits"].items()
                  if pd.Timestamp(bounds[0]) <= signal_date <= pd.Timestamp(bounds[1])), None)
    next_signal = signal_dates[i + 1] if i + 1 < len(signal_dates) else pd.NaT
    entry_date = next_session(signal_date)
    exit_date = next_session(next_signal)
    record = dict(date=signal_date, entry_date=entry_date, exit_date=exit_date,
                  split=split, ic=float("nan"), n=0, status="ok")

    # 4. 不完整的持有期、跨样本分界的标签保留空 IC，并记录原因。
    if pd.isna(entry_date):
        record["status"] = "incomplete_entry"
    elif pd.isna(exit_date):
        record["status"] = "incomplete_exit"
    elif split is None:
        record["status"] = "outside_split"
    else:
        begin, end = map(pd.Timestamp, config["splits"][split])
        if not begin <= signal_date <= entry_date <= exit_date <= end:
            record["status"] = "cross_split"

    if record["status"] != "ok":
        records.append(record)
        continue

    snapshot = factor_values.loc[factor_values["date"] == signal_date].copy()
    entry = prices.loc[prices["date"] == entry_date, ["symbol", "adj_open"]].rename(
        columns={"adj_open": "entry_open"})
    exit_ = prices.loc[prices["date"] == exit_date, ["symbol", "adj_open"]].rename(
        columns={"adj_open": "exit_open"})
    paired = snapshot.merge(entry, on="symbol", how="left", validate="one_to_one")
    paired = paired.merge(exit_, on="symbol", how="left", validate="one_to_one")
    paired = paired.dropna(subset=["momentum_20", "entry_open", "exit_open"]).copy()
    paired = paired.loc[(paired["entry_open"] > 0) & (paired["exit_open"] > 0)].copy()
    paired["forward_return"] = paired["exit_open"] / paired["entry_open"] - 1
    record["n"] = len(paired)
    if len(paired) < 5:
        record["status"] = "insufficient_pairs"
    elif paired["momentum_20"].nunique() < 2 or paired["forward_return"].nunique() < 2:
        record["status"] = "constant_rank"
    else:
        factor_rank = paired["momentum_20"].rank(method="average", ascending=False)
        return_rank = paired["forward_return"].rank(method="average", ascending=False)
        record["ic"] = factor_rank.corr(return_rank)
    records.append(record)

ic_table = pd.DataFrame(records).sort_values("date").reset_index(drop=True)

# 5. 每个样本区间分别统计；分母只包含有效 IC，不把缺失值补零。
summary_records = []
for split in config["splits"]:
    values = ic_table.loc[ic_table["split"] == split, "ic"].dropna()
    mean_ic = values.mean()
    ic_std = values.std(ddof=1)
    icir = mean_ic / ic_std if ic_std > 0 else float("nan")
    summary_records.append(dict(
        split=split, n_months=len(values), mean_ic=mean_ic, ic_std=ic_std, icir=icir,
        positive_months=int((values > 0).sum()), positive_share=(values > 0).mean(),
    ))
summary = pd.DataFrame(summary_records)

# 6. 按信号年份检查均值，观察整段平均数是否掩盖时期差异。
annual_summary = ic_table.groupby(ic_table["date"].dt.year)["ic"].agg(
    n_months="count", mean_ic="mean", ic_std="std",
).reset_index().rename(columns={"date": "signal_year"})

# 7. 保存本课的可核对结果；完整表保留全部月份和排除原因。
output_dir = data_path.parent.parent / "lesson08_monthly_ic"
output_dir.mkdir(parents=True, exist_ok=True)
ic_table.to_csv(output_dir / "monthly_ic.csv", index=False, date_format="%Y-%m-%d")
summary.to_csv(output_dir / "ic_summary.csv", index=False)
annual_summary.to_csv(output_dir / "annual_ic_summary.csv", index=False)

# 8. 绘制完整月度序列：NaN 月份自然断开，虚线为各样本区间的平均 IC。
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 11
fig, ax = plt.subplots(figsize=(11.5, 5.8), layout="constrained")
ax.plot(ic_table["date"], ic_table["ic"], color="#3268A8", linewidth=1.3,
        marker="o", markersize=3.3, label="每月 Rank IC")
ax.axhline(0, color="#747D86", linewidth=1.0, label="零线")
valid_ic = ic_table["ic"].dropna()
lower = min(-0.4, valid_ic.min() - 0.12)
upper = max(0.4, valid_ic.max() + 0.10)
ax.set_ylim(lower, upper)
split_labels = {"development": "开发期", "validation": "验证期", "test": "测试期"}
for index, (split, bounds) in enumerate(config["splits"].items()):
    block = ic_table.loc[ic_table["split"] == split]
    if block.empty:
        continue
    mean = summary.loc[summary["split"] == split, "mean_ic"].iloc[0]
    ax.hlines(mean, block["date"].min(), block["date"].max(), color="#B46A31",
              linewidth=1.5, linestyle="--", label="分区平均 IC" if index == 0 else None)
    begin, end = map(pd.Timestamp, bounds)
    if index > 0:
        ax.axvline(begin, color="#AEB7BF", linewidth=0.8, linestyle=":")
    if split == "validation":
        ax.axvspan(begin, end, color="#747D86", alpha=0.06)
    ax.text(begin + (end - begin) / 2, lower + (upper - lower) * 0.035,
            split_labels.get(split, split), ha="center", va="bottom", color="#59636D")

tick_indices = sorted({0, len(ic_table) // 3, len(ic_table) * 2 // 3, len(ic_table) - 1})
ax.set_xticks(ic_table["date"].iloc[tick_indices])
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.set_xlim(ic_table["date"].iloc[0], ic_table["date"].iloc[-1])
ax.set_title("原始20日动量：月度 Rank IC（模拟数据）", fontsize=16, pad=15)
ax.set_ylabel("Rank IC（无量纲）")
ax.set_xlabel("信号月份（IC 为事后统计；不完整或跨区间月份留空）")
ax.legend(loc="upper left", frameon=False, fontsize=10, ncols=3)
ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color("#B5BDC5")
fig.savefig(output_dir / "monthly_ic.png", dpi=180)
plt.close(fig)

print("模拟数据；原始动量；月度理论开盘到开盘标签；ICIR 未年化。")
print("\n前 12 个信号月：")
print(ic_table.head(12).to_string(index=False))
print("\n分区汇总（positive_share 为正 IC 月份占比，不是交易胜率）：")
print(summary.to_string(index=False, formatters={"positive_share": "{:.2%}".format}))
print("\n按信号年份汇总：")
print(annual_summary.to_string(index=False))
print("\n月份状态计数：")
print(ic_table["status"].value_counts().to_string())
print("\n结果目录：", output_dir)
