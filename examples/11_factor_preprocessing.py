"""第十一课：同日 MAD 去极值、Z-score 标准化和预设方向统一；模拟数据。"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
from ashare_lab.config import load_config

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def preprocess_factor(values, direction, mad_scale=3.0):
    """仅处理一个日期的一个因子，返回逐股票步骤表及截面统计量。"""
    clean = values.replace([np.inf, -np.inf], np.nan).astype(float)
    valid = clean.dropna()
    median = valid.median()
    mad = (valid - median).abs().median()

    # MAD 为零时跳过截断，避免把非恒定截面全部压成同一个值。
    clipped = clean.copy()
    lower, upper = np.nan, np.nan
    if mad > 0:
        distance = mad_scale * 1.4826 * mad
        lower, upper = median - distance, median + distance
        clipped = clean.clip(lower=lower, upper=upper)

    mean = clipped.mean()
    std = clipped.std(ddof=0)
    z_before_direction = pd.Series(np.nan, index=values.index, dtype=float)
    status = "insufficient_valid"
    if len(valid) >= 2:
        # 数值精度容差，匹配项目核心模块的恒定截面处理。
        tolerance = np.finfo(float).eps * max(1.0, abs(float(mean)))
        if std <= tolerance:
            z_before_direction.loc[valid.index] = 0.0
            status = "constant_cross_section"
        else:
            z_before_direction.loc[valid.index] = (clipped.loc[valid.index] - mean) / std
            status = "ok"
    score = direction * z_before_direction

    stages = pd.DataFrame({"raw": clean, "clipped": clipped,
                           "z_before_direction": z_before_direction, "score": score})
    stats = dict(n_valid=len(valid), median=median, mad=mad, lower_bound=lower,
        upper_bound=upper, n_clipped=int((clean.notna() & clean.ne(clipped)).sum()),
        clipped_mean=mean, clipped_std=std, direction=direction,
        score_mean=score.mean(), score_std=score.std(ddof=0), status=status)
    return stages, stats


def main():
    project_dir = Path(__file__).resolve().parents[1]
    run_dir = project_dir / "runs" / "first_demo_20261107"
    raw = pd.read_csv(run_dir / "lesson10_raw_factors" / "raw_factors.csv",
                      dtype={"symbol": "string"}, parse_dates=["date"])
    config = load_config(project_dir / "configs" / "baseline.json")
    signal_date = pd.Timestamp("2020-01-31")

    # 1. 只取当天截面，不把其他日期或未来测试期的统计量用于标准化。
    snapshot = raw.loc[raw["date"] == signal_date].sort_values("symbol").reset_index(drop=True)
    if snapshot.empty or snapshot["symbol"].duplicated().any():
        raise ValueError("当天截面为空或股票代码重复，请检查上一课输出。")
    specs = {"momentum": "momentum_20", "volatility": "volatility_20", "activity": "activity_5_20"}
    processed = snapshot[["date", "symbol", *specs.values()]].copy()
    stage_tables, statistic_rows = [], []

    # 2. 同一天内，各因子各自处理；方向来自预先固定的配置。
    for factor, column in specs.items():
        direction = config["directions"][factor]
        stages, stats = preprocess_factor(snapshot[column], direction, config["mad_scale"])
        processed[f"clipped_{factor}"] = stages["clipped"]
        processed[f"z_before_{factor}"] = stages["z_before_direction"]
        # z_* 字段是已统一方向的分数，命名与项目核心模块保持一致。
        processed[f"z_{factor}"] = stages["score"]
        stage_tables.append(stages.assign(date=signal_date, symbol=snapshot["symbol"],
                                          factor=factor, direction=direction))
        statistic_rows.append(dict(factor=factor, **stats))
    all_stages = pd.concat(stage_tables, ignore_index=True)
    statistics = pd.DataFrame(statistic_rows)

    # 3. 保存每一步中间值；本课尚未求三因子的合成分数。
    output_dir = run_dir / "lesson11_preprocessing"
    output_dir.mkdir(parents=True, exist_ok=True)
    processed.to_csv(output_dir / "processed_snapshot.csv", index=False, date_format="%Y-%m-%d")
    statistics.to_csv(output_dir / "cross_section_stats.csv", index=False)
    all_stages.to_csv(output_dir / "factor_steps.csv", index=False, date_format="%Y-%m-%d")

    # 4. 左图展示动量截断；右图展示 SYN001 统一方向后的三个分数。
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    fig, (ax_raw, ax_score) = plt.subplots(1, 2, figsize=(11.8, 4.8), layout="constrained")
    ordered = processed.sort_values(["momentum_20", "symbol"]).reset_index(drop=True)
    positions = np.arange(1, len(ordered) + 1)
    upper = statistics.loc[statistics["factor"] == "momentum", "upper_bound"].iloc[0]
    ax_raw.plot(positions, ordered["momentum_20"], color="#747D86", marker="o",
                markersize=3.3, linewidth=1.1, linestyle="--", label="原始动量")
    ax_raw.plot(positions, ordered["clipped_momentum"], color="#3268A8", marker="o",
                markersize=3, linewidth=1.4, label="MAD 截断后")
    ax_raw.axhline(upper, color="#B46A31", linewidth=1, linestyle=":", label=f"上限 {upper:.2%}")
    ax_raw.axhline(0, color="#AEB7BF", linewidth=0.7)
    ax_raw.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax_raw.set_title("动量因子：保留股票，截断极端数值", fontsize=12)
    ax_raw.set_xlabel("按原始动量从低到高排序的股票序号")
    ax_raw.set_ylabel("20 日动量")
    ax_raw.set_xticks([1, 10, 20, 30, 40])
    ax_raw.legend(loc="upper left", frameon=False, fontsize=9)

    focus = processed.loc[processed["symbol"] == "SYN001"].iloc[0]
    scores = [focus["z_momentum"], focus["z_volatility"], focus["z_activity"]]
    ax_score.bar(["动量", "波动率", "活跃度"], scores, color="#3268A8", width=0.6)
    ax_score.axhline(0, color="#747D86", linewidth=0.9)
    for index, value in enumerate(scores):
        ax_score.annotate(f"{value:+.4f}", xy=(index, value), xytext=(0, 5 if value >= 0 else -6),
                          textcoords="offset points", ha="center",
                          va="bottom" if value >= 0 else "top", fontsize=10)
    ax_score.set_ylim(min(scores) - 0.45, max(scores) + 0.4)
    ax_score.set_title("SYN001：方向统一后的分数", fontsize=12)
    ax_score.set_ylabel("分数（无量纲，不是收益率）")
    ax_score.set_xlabel("预设方向：动量 +1，波动率 -1，活跃度 -1")
    for ax in (ax_raw, ax_score):
        ax.grid(axis="y", color="#DCE2E8", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("2020-01-31 同日因子预处理（40 只模拟股票）", fontsize=16)
    fig.savefig(output_dir / "factor_preprocessing.png", dpi=180)
    plt.close(fig)

    print("模拟数据；只使用当天截面；预设方向属于研究假设。")
    print("\n截面统计（阈值与原因子单位相同）：")
    print(statistics.to_string(index=False))
    print("\nSYN001 各步骤：")
    print(all_stages.loc[all_stages["symbol"] == "SYN001",
          ["factor", "raw", "clipped", "z_before_direction", "direction", "score"]].to_string(index=False))
    print("\n发生数值截断的动量股票：")
    mask = processed["momentum_20"].ne(processed["clipped_momentum"])
    print(processed.loc[mask, ["symbol", "momentum_20", "clipped_momentum", "z_momentum"]].to_string(index=False))
    print("\n本课结果目录：", output_dir)


if __name__ == "__main__":
    main()
