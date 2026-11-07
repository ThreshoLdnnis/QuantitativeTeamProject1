"""第四课：绘制单只模拟股票的净值与回撤，计算最大回撤。"""

from pathlib import Path
import pandas as pd
import matplotlib

# 直接保存图片，脚本可以在终端运行。
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

# 沿用前几课：读取、筛选、按独立的模拟交易日历对齐。
project_dir = Path(__file__).resolve().parents[1]
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"
prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])
symbol = "SYN001"
stock = prices.loc[prices["symbol"] == symbol].copy()
stock = stock.sort_values("date").reset_index(drop=True)
calendar = pd.read_csv(data_path.with_name("calendar.csv"), parse_dates=["date"])
stock = stock.set_index("date").reindex(calendar["date"]).reset_index()
if stock.empty or stock["adj_close"].isna().any() or (stock["adj_close"] <= 0).any():
    raise ValueError("本课需要完整且为正的复权收盘价，请先检查股票代码和缺失行情。")

# 1. 本课仍以首日收盘为起点，持续持有这只股票，不计费用。
stock["daily_return"] = stock["adj_close"] / stock["adj_close"].shift(1) - 1
growth_factor = 1 + stock["daily_return"]
growth_factor.iloc[0] = 1.0
stock["nav"] = growth_factor.cumprod(skipna=False)
stock["cumulative_return"] = stock["nav"] - 1

# 2. 截至每一天的历史最高净值；只能用该日及之前的数据。
stock["running_peak"] = stock["nav"].cummax(skipna=False)

# 3. 每日回撤是负数或零；最大回撤幅度以正数展示。
stock["drawdown"] = stock["nav"] / stock["running_peak"] - 1
max_drawdown_signed = stock["drawdown"].min()
max_drawdown = -max_drawdown_signed

# 4. 找到最深回撤的谷底，以及发生在它之前的峰值。
trough_index = stock["drawdown"].idxmin()
peak_index = stock.loc[:trough_index, "nav"].idxmax()
peak = stock.loc[peak_index]
trough = stock.loc[trough_index]
final_return = stock["cumulative_return"].iloc[-1]

# 5. 两幅图共用日期轴，上方净值、下方回撤。
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 11
fig, (ax_nav, ax_dd) = plt.subplots(
    2, 1, figsize=(11, 7.2), sharex=True,
    gridspec_kw={"height_ratios": [2, 1]}, layout="constrained",
)
fig.suptitle(f"{symbol}：净值曲线与回撤（模拟数据）", fontsize=17)
ax_nav.set_title(
    f"期末累计收益率 {final_return:.2%}    最大回撤幅度 {max_drawdown:.2%}",
    loc="left", fontsize=11, pad=10,
)

# 6. 净值实线与截至当日的历史高点虚线。
ax_nav.plot(stock["date"], stock["nav"], color="#3268A8", linewidth=1.6, label="净值 NAV")
ax_nav.plot(stock["date"], stock["running_peak"], color="#747D86", linewidth=1.2,
            linestyle="--", label="截至当日的历史高点")
ax_nav.axhline(1.0, color="#9FA6AD", linewidth=0.8, linestyle=":")
ax_nav.set_ylabel("净值（首日 = 1）")
ax_nav.set_ylim(0, max(1.25, stock["nav"].max() * 1.16))
ax_nav.legend(loc="upper right", frameon=False, fontsize=10)

# 峰值和谷值标记，仅用于定位本次最大回撤。
ax_nav.scatter(peak["date"], peak["nav"], color="#3268A8", marker="o", s=40, zorder=5)
ax_nav.scatter(trough["date"], trough["nav"], color="#B46A31", marker="v", s=50, zorder=5)
ax_nav.annotate(
    f"前高 {peak['date']:%Y-%m-%d}\n净值 {peak['nav']:.4f}",
    xy=(peak["date"], peak["nav"]), xytext=(22, 20), textcoords="offset points",
    fontsize=10, arrowprops={"arrowstyle": "->", "color": "#747D86"},
)
ax_nav.annotate(
    f"谷底 {trough['date']:%Y-%m-%d}\n净值 {trough['nav']:.4f}",
    xy=(trough["date"], trough["nav"]), xytext=(-175, -35), textcoords="offset points",
    fontsize=10, arrowprops={"arrowstyle": "->", "color": "#747D86"},
)

# 7. 回撤以小数计算，坐标轴再格式化为百分比。
ax_dd.plot(stock["date"], stock["drawdown"], color="#3268A8", linewidth=1.1)
ax_dd.fill_between(stock["date"], stock["drawdown"], 0, color="#3268A8", alpha=0.18)
ax_dd.axhline(0, color="#747D86", linewidth=0.8)
ax_dd.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
ax_dd.set_ylabel("相对历史高点的回撤")
ax_dd.set_ylim(min(-0.05, max_drawdown_signed * 1.12), 0.04)
ax_dd.scatter(trough["date"], trough["drawdown"], color="#B46A31", marker="v", s=45, zorder=5)
ax_dd.annotate(
    f"最大回撤幅度 {max_drawdown:.2%}",
    xy=(trough["date"], trough["drawdown"]), xytext=(-190, 70), textcoords="offset points",
    fontsize=10, arrowprops={"arrowstyle": "->", "color": "#747D86"},
)

# 稀疏日期刻度，并保留起点和终点。
date_ticks = pd.date_range(stock["date"].iloc[0], stock["date"].iloc[-1], freq="2YS")
date_ticks = date_ticks.union(pd.DatetimeIndex([stock["date"].iloc[0], stock["date"].iloc[-1]]))
ax_dd.set_xticks(date_ticks)
ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
ax_dd.set_xlim(stock["date"].iloc[0], stock["date"].iloc[-1])
ax_dd.set_xlabel("日期（模拟工作日日历，单只股票持续持有，不计费用）")
for ax in (ax_nav, ax_dd):
    ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#B5BDC5")
    ax.tick_params(axis="both", labelsize=10)

# 8. 保存图片；关闭画布以释放内存，不修改原始行情。
output_dir = data_path.parent.parent / "figures"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / f"{symbol}_nav_drawdown.png"
fig.savefig(output_path, dpi=180)
plt.close(fig)

print("模拟股票：", symbol)
print(f"期末累计收益率：{final_return:.6%}")
print(f"最大回撤幅度（正数）：{max_drawdown:.6%}")
print(f"最深回撤（带负号）：{max_drawdown_signed:.6%}")
print(f"峰值日期：{peak['date']:%Y-%m-%d}，净值：{peak['nav']:.6f}")
print(f"谷值日期：{trough['date']:%Y-%m-%d}，净值：{trough['nav']:.6f}")
print("\n前 6 行：")
print(stock[["date", "nav", "running_peak", "drawdown"]].head(6).to_string(index=False))
print("\n图已保存：", output_path)
