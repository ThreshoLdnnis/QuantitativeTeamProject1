"""第十二课：三因子等权合成、综合排名和单日目标组合；模拟数据。"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
from ashare_lab.config import load_config

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCORE_COLUMNS = ["z_momentum", "z_volatility", "z_activity"]


def equal_weight_score(frame):
    """三个分数已经统一方向；缺少任一项就不生成完整总分。"""
    clean = frame[SCORE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    return clean.mean(axis=1, skipna=False)


def main():
    project_dir = Path(__file__).resolve().parents[1]
    run_dir = project_dir / "runs" / "first_demo_20261107"
    processed = pd.read_csv(run_dir / "lesson11_preprocessing" / "processed_snapshot.csv",
                            dtype={"symbol": "string"}, parse_dates=["date"])
    config = load_config(project_dir / "configs" / "baseline.json")
    if processed.empty or processed["date"].nunique() != 1 or processed["symbol"].duplicated().any():
        raise ValueError("本课要求一个日期、每只股票一行的已处理因子截面。")
    signal_date = processed["date"].iloc[0]

    # 1. 三个因子已完成 MAD、Z-score 和方向处理，直接各给 1/3 权重。
    scored = processed.copy()
    scored["composite"] = equal_weight_score(scored)
    for factor in ["momentum", "volatility", "activity"]:
        scored[f"contribution_{factor}"] = scored[f"z_{factor}"] / 3

    # 2. 保留完整总分，按分数降序、股票代码升序稳定排序。
    ranked = scored.dropna(subset=["composite"]).sort_values(
        ["composite", "symbol"], ascending=[False, True]
    ).reset_index(drop=True)
    ranked["composite_rank"] = range(1, len(ranked) + 1)
    if ranked.empty:
        raise ValueError("没有三个因子均有效的股票，不能生成目标组合。")

    # 3. 对比原始动量榜：同一完整因子股票池、同一天。
    momentum_order = ranked.sort_values(
        ["momentum_20", "symbol"], ascending=[False, True]
    )[["symbol"]].reset_index(drop=True)
    momentum_order["momentum_rank"] = range(1, len(momentum_order) + 1)
    ranked = ranked.merge(momentum_order, on="symbol", how="left", validate="one_to_one")

    # 4. 排名前 N 的股票进入目标名单，股票之间目标市值等权。
    targets = ranked.head(config["top_n"]).copy()
    targets["target_weight"] = 1 / len(targets)
    targets["reference_capital"] = config["initial_cash"]
    targets["target_value"] = targets["reference_capital"] * targets["target_weight"]

    # 5. 只查下一交易日日期，没有使用下一天的价格来决定排名。
    calendar = pd.read_csv(run_dir / "input" / "calendar.csv", parse_dates=["date"])
    days = pd.DatetimeIndex(calendar["date"])
    position = days.get_loc(signal_date)
    if position + 1 >= len(days):
        raise ValueError("日历中没有下一执行日，请检查本次信号日期。")
    execution_date = days[position + 1]
    targets["execution_date"] = execution_date
    ranked["selected"] = ranked["symbol"].isin(targets["symbol"])

    # 6. 保存的是目标权重与预算；本课不生成实际成交或原始股数。
    output_dir = run_dir / "lesson12_equal_weight_selection"
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output_dir / "composite_ranking.csv", index=False, date_format="%Y-%m-%d")
    targets.to_csv(output_dir / "target_portfolio.csv", index=False, date_format="%Y-%m-%d")

    # 7. 左图展示前十名，右图逐项解释 SYN001 的综合分数。
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    fig, (ax_rank, ax_parts) = plt.subplots(1, 2, figsize=(11.8, 5.8),
                                           gridspec_kw={"width_ratios": [1.1, 1]}, layout="constrained")
    names = [f"{row.composite_rank}. {row.symbol}" for row in targets.itertuples()]
    ax_rank.barh(names, targets["composite"], color="#3268A8", height=0.65)
    ax_rank.invert_yaxis()
    ax_rank.axvline(0, color="#747D86", linewidth=0.8)
    span = max(0.25, targets["composite"].max() - min(0, targets["composite"].min()))
    ax_rank.set_xlim(min(0, targets["composite"].min()) - span * 0.03,
                     max(0, targets["composite"].max()) + span * 0.23)
    for y, value in enumerate(targets["composite"]):
        ax_rank.annotate(f"{value:.4f}", xy=(value, y), xytext=(5 if value >= 0 else -5, 0),
                         textcoords="offset points", va="center",
                         ha="left" if value >= 0 else "right", fontsize=10)
    ax_rank.set_title(f"综合分数前 {len(targets)} 名", fontsize=12)
    ax_rank.set_xlabel("综合分数（无量纲）")
    ax_rank.grid(axis="x", color="#DCE2E8", linewidth=0.7)

    focus = ranked.loc[ranked["symbol"] == "SYN001"].iloc[0]
    parts = [focus["contribution_momentum"], focus["contribution_volatility"],
             focus["contribution_activity"], focus["composite"]]
    ax_parts.bar(["动量贡献", "波动率贡献", "活跃度贡献", "综合分数"], parts,
                  color=["#3268A8", "#3268A8", "#3268A8", "#747D86"], width=0.6)
    ax_parts.axhline(0, color="#747D86", linewidth=0.9)
    ax_parts.set_ylim(min(parts) - 0.25, max(parts) + 0.25)
    for x, value in enumerate(parts):
        ax_parts.annotate(f"{value:+.4f}", xy=(x, value), xytext=(0, 5 if value >= 0 else -6),
                          textcoords="offset points", ha="center",
                          va="bottom" if value >= 0 else "top", fontsize=10)
    ax_parts.set_title("SYN001：三项贡献相加得到总分", fontsize=12)
    ax_parts.set_ylabel("分数贡献（每项已乘 1/3）")
    ax_parts.grid(axis="y", color="#DCE2E8", linewidth=0.7)
    for ax in (ax_rank, ax_parts):
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"{signal_date:%Y-%m-%d} 三因子等权选股（模拟数据）", fontsize=16)
    fig.savefig(output_dir / "composite_selection.png", dpi=180)
    plt.close(fig)

    view_columns = ["composite_rank", "symbol", *SCORE_COLUMNS, "composite", "momentum_rank"]
    print("模拟数据；三个因子各占 1/3，z_* 已统一方向。综合分数不是收益率。")
    print("信号日收盘：", signal_date.date())
    print("计划执行日开盘：", execution_date.date())
    print("有效综合评分数：", len(ranked))
    print("\n综合前十名：")
    print(targets[view_columns].to_string(index=False))
    print(f"\nSYN001：原始动量第 {focus['momentum_rank']} 名，综合第 {focus['composite_rank']} 名。")
    print(f"综合得分：{focus['composite']:.12f}")
    print("\n目标权重与名义预算（尚未成交）：")
    print(targets[["symbol", "target_weight", "target_value", "execution_date"]].to_string(index=False))
    print("目标权重合计：", targets["target_weight"].sum())
    overlap = set(momentum_order.head(config["top_n"])["symbol"]) & set(targets["symbol"])
    print("与原始动量前十名重合的股票数：", len(overlap))
    print("\n本课结果目录：", output_dir)
    print("目标金额为名义预算；实际持仓还受开盘行情、费用、资金和成交标记约束。")


if __name__ == "__main__":
    main()
