"""第九课：原始动量五分组、理论组收益与 G5-G1 收益差；模拟数据。"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
from ashare_lab.config import load_config
from ashare_lab.research import build_forward_labels

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
days = pd.DatetimeIndex(calendar["date"])
config = load_config(project_dir / "configs" / "baseline.json")
lookback, n_groups = config["lookback"], 5

# 1. 与前几课相同：只使用各股票当时已经知道的历史行情计算原始动量。
factor_tables = []
for symbol, stock in prices.groupby("symbol", sort=True):
    stock = stock.sort_values("date").set_index("date").reindex(days).reset_index()
    stock["symbol"] = symbol
    close = stock["adj_close"].where(stock["adj_close"] > 0)
    count = close.rolling(lookback + 1, min_periods=lookback + 1).count()
    stock["momentum_20"] = (close / close.shift(lookback) - 1).where(count == lookback + 1)
    factor_tables.append(stock[["date", "symbol", "momentum_20"]])
factor_values = pd.concat(factor_tables, ignore_index=True)

# 2. 复用项目中的标签函数：次日开盘到下次调仓开盘；剔除跨分区及末尾不完整标签。
labels = build_forward_labels(prices, factor_values, days, config)

# 3. 先用信号日因子确定组别，再关联未来收益。未来价格不影响股票的分组。
member_tables, group_records = [], []
for signal_date, period_labels in labels.groupby("date", sort=True):
    split = period_labels["split"].iloc[0]
    cross = factor_values.loc[factor_values["date"] == signal_date].dropna(
        subset=["momentum_20"]
    ).copy()
    if len(cross) < n_groups or cross["momentum_20"].nunique() < 2:
        for group in range(1, n_groups + 1):
            group_records.append(dict(date=signal_date, split=split, group=group,
                n_assigned=0, n_valid=0, group_return=np.nan, status="insufficient_factor"))
        continue

    # 低动量排在前面；并列因子使用平均秩，不用股票代码拆开同分股票。
    rank_low_to_high = cross["momentum_20"].rank(method="average", ascending=True)
    cross["group"] = (
        np.floor((rank_low_to_high - 1) * n_groups / len(cross)) + 1
    ).astype(int)
    paired = cross.merge(period_labels, on=["date", "symbol"], how="left",
                         validate="one_to_one")
    member_tables.append(paired)

    # 4. 每组入场时等权、持有到退出，理论组收益为成员收益的算术平均。
    # 组内任一股票缺失收益时，该组留空；不靠删除缺失成员来重分组或补零。
    for group in range(1, n_groups + 1):
        members = paired.loc[paired["group"] == group]
        n_assigned = len(members)
        n_valid = int(members["forward_return"].notna().sum())
        status = "ok" if n_assigned > 0 and n_valid == n_assigned else "incomplete_group"
        group_return = members["forward_return"].mean() if status == "ok" else np.nan
        group_records.append(dict(date=signal_date, split=split, group=group,
            n_assigned=n_assigned, n_valid=n_valid, group_return=group_return, status=status))

membership = pd.concat(member_tables, ignore_index=True)
group_table = pd.DataFrame(group_records)

# 5. 将每期五组排成五列，只在五组收益都完整的共同月份上作比较。
wide = group_table.pivot(index=["date", "split"], columns="group", values="group_return")
comparison = wide.dropna(subset=[1, 2, 3, 4, 5]).reset_index()
if comparison.empty:
    raise ValueError("没有完整的五分组持有期，请检查因子分散程度、组数和未来收益覆盖。")
comparison["spread"] = comparison[5] - comparison[1]

# 6. 先逐月计算各组收益，再在开发/验证/测试期内对月份取算术平均。
used_groups = group_table.loc[group_table["date"].isin(comparison["date"])].copy()
group_summary = used_groups.groupby(["split", "group"], sort=False).agg(
    n_months=("group_return", "count"), mean_return=("group_return", "mean")
).reset_index()

spread_records = []
for split in config["splits"]:
    values = comparison.loc[comparison["split"] == split, "spread"]
    means = group_summary.loc[group_summary["split"] == split].set_index("group")["mean_return"]
    ordered_means = means.reindex([1, 2, 3, 4, 5])
    monotonic = (bool((ordered_means.diff().dropna() >= 0).all())
                 if ordered_means.notna().all() else None)
    spread_records.append(dict(split=split, n_months=len(values),
        mean_spread=values.mean(), spread_std=values.std(ddof=1),
        positive_months=int((values > 0).sum()), positive_share=(values > 0).mean(),
        increasing_group_means=monotonic))
spread_summary = pd.DataFrame(spread_records)
yearly_spread = comparison.groupby(comparison["date"].dt.year)["spread"].agg(
    n_months="count", mean_spread="mean"
).reset_index().rename(columns={"date": "signal_year"})

# 7. 保存成员、组收益和汇总。完整月度差值表保留被排除月份的空值。
all_months = pd.Series(days, index=days).groupby(days.to_period("M")).last()
all_months = pd.DatetimeIndex(all_months.to_numpy())
review_dates = all_months[(all_months >= pd.Timestamp(config["start"])) &
                         (all_months <= pd.Timestamp(config["end"]))]
monthly = comparison.rename(columns={g: f"G{g}" for g in range(1, 6)})
monthly = monthly.set_index("date").reindex(review_dates).rename_axis("date").reset_index()
monthly["status"] = np.where(monthly["spread"].notna(), "ok", "excluded_label_or_group")
output_dir = data_path.parent.parent / "lesson09_quintile_returns"
output_dir.mkdir(parents=True, exist_ok=True)
for name, frame in {
    "group_membership": membership, "monthly_group_returns": group_table,
    "group_summary": group_summary, "monthly_spread": monthly,
    "spread_summary": spread_summary, "yearly_spread": yearly_spread,
}.items():
    frame.to_csv(output_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")

# 8. 上排对比各阶段五组平均收益；下排保留每月 G5-G1 的波动与空缺。
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 11
fig = plt.figure(figsize=(12, 8.4), layout="constrained")
grid = fig.add_gridspec(2, 3, height_ratios=[1, 1.15])
split_labels = {"development": "开发期", "validation": "验证期", "test": "测试期"}
means_all = group_summary["mean_return"]
lower, upper = min(-0.005, means_all.min() - 0.005), max(0.005, means_all.max() + 0.006)
for column, split in enumerate(config["splits"]):
    ax = fig.add_subplot(grid[0, column])
    block = group_summary.loc[group_summary["split"] == split].set_index("group")
    values = block["mean_return"].reindex([1, 2, 3, 4, 5])
    count = spread_summary.loc[spread_summary["split"] == split, "n_months"].iloc[0]
    ax.bar(range(1, 6), values, color="#3268A8", width=0.65)
    ax.axhline(0, color="#747D86", linewidth=0.8)
    for group, value in values.items():
        if pd.notna(value):
            ax.annotate(f"{value:.2%}", xy=(group, value), xytext=(0, 5 if value >= 0 else -6),
                        textcoords="offset points", ha="center",
                        va="bottom" if value >= 0 else "top", fontsize=10)
    ax.set_title(f"{split_labels.get(split, split)}：{count} 个有效持有期", fontsize=12)
    ax.set_xticks(range(1, 6), [f"G{g}" for g in range(1, 6)])
    ax.set_xlabel("低动量 G1 → 高动量 G5")
    ax.set_ylim(lower, upper)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=1))
    if column == 0:
        ax.set_ylabel("平均持有期收益（非年化）")
    ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

ax = fig.add_subplot(grid[1, :])
# 乘以 100 后以“百分点”显示收益差，避免把理论差值称为真实多空净收益。
ax.plot(monthly["date"], monthly["spread"] * 100, color="#3268A8", marker="o",
        markersize=3, linewidth=1.2, label="每期 G5−G1")
ax.axhline(0, color="#747D86", linewidth=0.9)
for index, (split, bounds) in enumerate(config["splits"].items()):
    block = monthly.loc[monthly["split"] == split]
    mean = spread_summary.loc[spread_summary["split"] == split, "mean_spread"].iloc[0]
    ax.hlines(mean * 100, block["date"].min(), block["date"].max(), color="#B46A31",
              linestyle="--", linewidth=1.3, label="分区平均差值" if index == 0 else None)
    if index > 0:
        ax.axvline(pd.Timestamp(bounds[0]), color="#AEB7BF", linestyle=":", linewidth=0.8)
tick_indices = sorted({0, len(monthly) // 3, len(monthly) * 2 // 3, len(monthly) - 1})
ax.set_xticks(monthly["date"].iloc[tick_indices])
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.set_xlim(monthly["date"].iloc[0], monthly["date"].iloc[-1])
ax.set_ylabel("高组减低组的收益差（百分点）")
ax.set_xlabel("信号月份（空缺未补零；收益为次日开盘到下次调仓开盘的理论毛收益）")
ax.legend(loc="upper left", frameon=False, fontsize=10, ncols=2)
ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("原始动量五分组收益检验（模拟数据、未扣成本）", fontsize=17)
fig.savefig(output_dir / "quintile_returns.png", dpi=180)
plt.close(fig)

print("模拟股票池；组内入场等权，期间持有；各持有期算术平均，非年化、未扣成本。")
print("完整持有期数：", len(comparison))
print("组收益行数：", len(group_table))
print("每组股票数量分布：", group_table["n_assigned"].value_counts().to_dict())
print("\n首期五分组（group_return 为小数收益率）：")
print(group_table.loc[group_table["date"] == comparison["date"].min()].to_string(index=False))
print("\n各分区、各组平均持有期收益（小数）：")
print(group_summary.to_string(index=False))
print("\n高组减低组的差值汇总（小数差值乘 100 为百分点，不是交易胜率）：")
print(spread_summary.to_string(index=False))
print("\n按信号年份统计 G5−G1：")
print(yearly_spread.to_string(index=False))
print("\n本课结果目录：", output_dir)
print("G5−G1 仅为理论收益差，未模拟卖空、保证金、资金占用及交易成本。")
