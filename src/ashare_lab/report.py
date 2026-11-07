"""Self-contained, source-linked Chinese HTML research notebook (no web assets)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html import escape
import math
from pathlib import Path

import numpy as np
import pandas as pd


STRATEGIES = {
    "benchmark": "股票池等权基准",
    "momentum": "动量选股",
    "volatility": "低波动选股",
    "activity": "低活跃度选股",
    "multifactor": "三因子等权",
    "multifactor_cost0": "三因子 · 零成本",
    "multifactor_cost2": "三因子 · 双倍成本",
}
FACTORS = {"momentum": "动量", "volatility": "波动率", "activity": "活跃度", "composite": "三因子合成"}
SPLITS = {"all": "完整研究区间", "development": "开发期", "validation": "验证期", "test": "测试期"}
COLORS = {"benchmark": "#67717c", "momentum": "#356aab", "volatility": "#8a54a2",
          "activity": "#b05d2b", "multifactor": "#17695c"}
FACTOR_COLORS = {"momentum": "#356aab", "volatility": "#8a54a2", "activity": "#b05d2b", "composite": "#17695c"}
MAIN = ["benchmark", "momentum", "volatility", "activity", "multifactor"]


def _strategy_label(strategy):
    if strategy in STRATEGIES:
        return STRATEGIES[strategy]
    if str(strategy).startswith("multifactor_cost"):
        multiplier = str(strategy)[len("multifactor_cost"):]
        return f"三因子 · {multiplier} 倍成本"
    return str(strategy)


def _text(value) -> str:
    return escape(str(value), quote=True)


def _number(value, digits=2) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{value:,.{digits}f}" if math.isfinite(value) else "—"


def _percent(value, digits=2) -> str:
    try:
        return _number(float(value) * 100, digits) + "%" if math.isfinite(float(value)) else "—"
    except (TypeError, ValueError):
        return "—"


def _table(headers, rows, caption="") -> str:
    body = list(rows)
    if not body:
        return '<p class="empty">此区间没有满足要求的完整观测。</p>'
    cap = f'<caption>{_text(caption)}</caption>' if caption else ""
    head = "".join(f'<th scope="col">{_text(h)}</th>' for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in body)
    return f'<div class="table-wrap"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{trs}</tbody></table></div>'


def _legend(items):
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{_text(color)}"></i>{_text(label)}</span>'
        for label, color in items
    ) + "</div>"


def _line_chart(series, title, chart_id, y_label, reference=None, fmt=None):
    """series: (label, color, dates, values); missing points break the path."""
    fmt = fmt or (lambda x: f"{x:.2f}")
    prepared, xs, ys = [], [], []
    for label, color, dates, values in series:
        points = []
        for d, value in zip(dates, values):
            try:
                x, y = pd.Timestamp(d).toordinal(), float(value)
            except (TypeError, ValueError):
                continue
            points.append((x, y))
            if math.isfinite(y):
                xs.append(x)
                ys.append(y)
        prepared.append((label, color, points))
    if not xs or not ys:
        return '<p class="empty">没有可绘制的有效观测。</p>'
    if reference is not None:
        ys.append(reference)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if xmin == xmax:
        xmax = xmin + 1
    span = ymax - ymin
    pad = span * 0.09 if span > 1e-10 else max(abs(ymax) * 0.05, 0.05)
    ymin, ymax = ymin - pad, ymax + pad
    width, height = 960, 330
    left, right, top, bottom = 68, 24, 30, 48
    pw, ph = width - left - right, height - top - bottom
    xp = lambda x: left + (x - xmin) / (xmax - xmin) * pw
    yp = lambda y: top + (ymax - y) / (ymax - ymin) * ph
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{chart_id}-title {chart_id}-desc">',
             f'<title id="{chart_id}-title">{_text(title)}</title>',
             f'<desc id="{chart_id}-desc">{_text(y_label)}；时间从{date.fromordinal(xmin).isoformat()}到{date.fromordinal(xmax).isoformat()}。图例列出所有序列。</desc>',
             f'<text x="{left}" y="16" class="axis-unit">{_text(y_label)}</text>']
    for y in np.linspace(ymin, ymax, 5):
        pos = yp(float(y))
        parts.extend([f'<line x1="{left}" y1="{pos:.2f}" x2="{width-right}" y2="{pos:.2f}" class="grid-line"/>',
                      f'<text x="{left-10}" y="{pos+4:.2f}" text-anchor="end" class="axis-text">{_text(fmt(float(y)))}</text>'])
    if reference is not None and ymin <= reference <= ymax:
        pos = yp(reference)
        parts.append(f'<line x1="{left}" y1="{pos:.2f}" x2="{width-right}" y2="{pos:.2f}" class="reference-line"/>')
    for index, x in enumerate([xmin, (xmin + xmax) // 2, xmax]):
        anchor = "start" if index == 0 else "end" if index == 2 else "middle"
        parts.append(f'<text x="{xp(x):.2f}" y="{height-16}" text-anchor="{anchor}" class="axis-text">{date.fromordinal(x).isoformat()}</text>')
    for label, color, points in prepared:
        segments, current = [], []
        for x, y in points:
            if math.isfinite(y):
                current.append((x, y))
            elif current:
                segments.append(current)
                current = []
        if current:
            segments.append(current)
        for segment in segments:
            path = " ".join(("M" if i == 0 else "L") + f"{xp(x):.2f},{yp(y):.2f}" for i, (x, y) in enumerate(segment))
            weight = 2.7 if "三因子" in label else 1.8
            parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{weight}" stroke-linejoin="round"><title>{_text(label)}</title></path>')
            if len(segment) == 1:
                x, y = segment[0]
                parts.append(f'<circle cx="{xp(x):.2f}" cy="{yp(y):.2f}" r="3" fill="{color}"/>')
    parts.append("</svg>")
    return "".join(parts) + _legend([(s[0], s[1]) for s in prepared])


def _group_chart(group_frame, split):
    if group_frame.empty:
        return '<p class="empty">没有可绘制的分组观测。</p>'
    frame = group_frame.loc[group_frame["split"].eq(split)]
    avg = frame.groupby(["factor", "group"])["forward_return"].mean()
    if avg.empty:
        return '<p class="empty">该样本区间没有完整持有期分组收益。</p>'
    factors = [name for name in FACTORS if name in avg.index.get_level_values("factor")]
    groups = sorted(set(int(g) for g in avg.index.get_level_values("group")))
    values = [float(value) for value in avg if np.isfinite(value)]
    ymin, ymax = min([0.0, *values]), max([0.0, *values])
    span = max(ymax - ymin, 0.002)
    ymin, ymax = ymin - span * 0.12, ymax + span * 0.12
    width, height = 960, 320
    left, right, top, bottom = 68, 24, 30, 48
    pw, ph = width - left - right, height - top - bottom
    yp = lambda y: top + (ymax - y) / (ymax - ymin) * ph
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-labelledby="group-title group-desc">',
             '<title id="group-title">各因子分组的平均理论持有期收益</title>',
             '<desc id="group-desc">分组按有利方向得分从低到高排列。每组并列展示动量、波动率、活跃度和合成因子；不含交易成本。</desc>',
             f'<text x="{left}" y="16" class="axis-unit">平均月度持有期收益 / %</text>']
    for y in np.linspace(ymin, ymax, 5):
        pos = yp(float(y))
        parts.append(f'<line x1="{left}" y1="{pos:.2f}" x2="{width-right}" y2="{pos:.2f}" class="grid-line"/>')
        parts.append(f'<text x="{left-10}" y="{pos+4:.2f}" text-anchor="end" class="axis-text">{y*100:.2f}</text>')
    zero = yp(0)
    parts.append(f'<line x1="{left}" y1="{zero:.2f}" x2="{width-right}" y2="{zero:.2f}" class="reference-line"/>')
    group_width = pw / len(groups)
    bar_width = min(26, group_width * 0.7 / len(factors))
    for i, group in enumerate(groups):
        center = left + (i + 0.5) * group_width
        parts.append(f'<text x="{center:.2f}" y="{height-16}" text-anchor="middle" class="axis-text">G{group}</text>')
        for j, factor in enumerate(factors):
            if (factor, group) not in avg.index:
                continue
            value = float(avg.loc[(factor, group)])
            if not math.isfinite(value):
                continue
            x = center + (j - len(factors) / 2) * bar_width
            y = min(zero, yp(value))
            h = max(abs(yp(value) - zero), 0.6)
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width-2:.2f}" height="{h:.2f}" rx="1" fill="{FACTOR_COLORS[factor]}"><title>{_text(FACTORS[factor])} G{group}: {value*100:.3f}%</title></rect>')
    parts.append("</svg>")
    return "".join(parts) + _legend([(FACTORS[f], FACTOR_COLORS[f]) for f in factors])


def _metric_table(frame, include_strategy=True):
    headers = ["策略", "累计收益", "年化收益", "年化波动", "夏普", "最大回撤", "相对基准收益", "年化双边换手", "成本合计 / 元"]
    rows = []
    for row in frame.to_dict("records"):
        name = _strategy_label(row.get("strategy", ""))
        rows.append([_text(name), _percent(row.get("total_return")), _percent(row.get("annual_return")),
                     _percent(row.get("annual_volatility")), _number(row.get("sharpe")),
                     _percent(row.get("max_drawdown")), _percent(row.get("relative_return")),
                     _number(row.get("annual_turnover")) + " 倍", _number(row.get("total_cost"))])
    return _table(headers, rows)


def _factor_histograms(factor_path, config):
    """Inspect the most recent raw cross-section, with no extra data source."""
    if not factor_path.exists():
        return ""
    frame = pd.read_csv(
        factor_path, usecols=["date", "momentum", "volatility", "activity"], parse_dates=["date"]
    )
    frame = frame.loc[frame["date"] <= pd.Timestamp(config["end"])]
    if frame.empty:
        return ""
    latest = frame["date"].max()
    cross = frame.loc[frame["date"].eq(latest)]
    parts = ['<details><summary>检查最近横截面的原始因子分布</summary>',
             f'<p class="caption">{latest.strftime("%Y-%m-%d")} 的未标准化因子。直方图用于观察尺度、集中程度与异常值，不能证明预测能力。</p>',
             '<svg class="chart" viewBox="0 0 960 285" role="img" aria-labelledby="distribution-title distribution-desc">',
             '<title id="distribution-title">最近横截面的三个原始因子分布</title>',
             '<desc id="distribution-desc">三个面板分别展示动量、日收益波动率和成交活跃度；纵轴为股票数量。</desc>']
    for i, factor in enumerate(["momentum", "volatility", "activity"]):
        values = cross[factor].replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
        left, top, pw, ph = i * 320 + 44, 48, 250, 175
        is_percent = factor != "activity" or config.get("activity_mode") == "turnover"
        unit = "%" if is_percent else "倍"
        shown = values * 100 if is_percent else values
        parts.append(f'<text x="{left}" y="24" class="axis-unit">{_text(FACTORS[factor])} / {unit} · n={len(values)}</text>')
        if len(shown) < 2:
            parts.append(f'<text x="{left+pw/2}" y="140" text-anchor="middle" class="axis-text">有效横截面不足</text>')
            continue
        low, high = float(shown.min()), float(shown.max())
        if high - low < 1e-10:
            pad = max(abs(low) * 0.05, 0.01)
            low, high = low - pad, high + pad
        counts, edges = np.histogram(shown, bins=min(10, max(3, int(np.sqrt(len(shown))))), range=(low, high))
        maximum = max(1, int(counts.max()))
        parts.append(f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" class="reference-line"/>')
        parts.append(f'<line x1="{left}" y1="{top}" x2="{left+pw}" y2="{top}" class="grid-line"/>')
        parts.append(f'<text x="{left-7}" y="{top+4}" text-anchor="end" class="axis-text">{maximum}</text>')
        parts.append(f'<text x="{left-7}" y="{top+ph+4}" text-anchor="end" class="axis-text">0</text>')
        bw = pw / len(counts)
        for j, count in enumerate(counts):
            height = count / maximum * ph
            parts.append(f'<rect x="{left+j*bw+1:.2f}" y="{top+ph-height:.2f}" width="{bw-2:.2f}" height="{height:.2f}" fill="{FACTOR_COLORS[factor]}" opacity=".82"><title>{edges[j]:.3f} 至 {edges[j+1]:.3f}{unit}: {count} 只</title></rect>')
        for j, tick in enumerate([low, (low+high)/2, high]):
            x = left + j * pw / 2
            anchor = "start" if j == 0 else "end" if j == 2 else "middle"
            parts.append(f'<text x="{x}" y="{top+ph+22}" text-anchor="{anchor}" class="axis-text">{tick:.2f}</text>')
    parts.append('<text x="44" y="274" class="axis-unit">纵轴：股票数量；各面板横轴范围独立。</text></svg></details>')
    return "".join(parts)


def _translate_limit(text):
    translations = {
        "SIMULATED DATA": "全部为模拟数据，不能据此判断真实 A 股因子是否有效。",
        "Calendar uses weekdays": "模拟日历采用工作日，包含中国法定节假日；不是真实交易所日历。",
        "Artificial flags": "停牌及买卖受限标记为人工构造，仅用于检验无法成交时的程序行为。",
        "Fixed selected survivors": "固定教学股票池可能存在幸存者偏差和选择偏差，不能代表全 A 股。",
        "Historical ST": "此数据适配器未提供完整历史 ST、退市、IPO 排除记录和开盘成交状态。",
        "can_buy/can_sell": "真实行情中的买卖标记仅依据成交量作假设，未核实历史涨跌停和停牌约束。",
        "Adjusted fractional": "复权价格与可分割份额是经济收益近似，未逐笔核算公司行为现金流和整手交易。",
        "Historical execution status": "部分历史成交状态未知，允许成交的结果属于教学假设。",
        "Eligible symbol/session": "存在股票池成员缺失行情：滚动窗口失效；若已有持仓无法估值，回测会终止。",
    }
    for beginning, translated in translations.items():
        if str(text).startswith(beginning):
            return translated
    return str(text)


def write_report(path, metadata, quality, config, research, results, metrics_frame):
    """Write one standalone UTF-8 HTML file next to the experiment CSVs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    synthetic = metadata.get("kind") == "synthetic"
    banner = ("模拟数据 · 仅验证工程流程，不能用于A股因子有效性结论" if synthetic else
              "真实行情 · 固定教学股票池 / 历史成交状态未核实 / 不能代表全A股")
    subheading = "模拟基线 / 工程验证" if synthetic else "真实行情 / 教学研究基线"
    source = metadata.get("source", "未记录")
    start, end = config.get("start", ""), config.get("end", "")
    first, last = quality.get("first_date", ""), quality.get("last_date", "")
    multi = results.get("multifactor")
    orders = multi.orders if multi is not None else pd.DataFrame()
    rejected = int(orders["status"].eq("rejected").sum()) if "status" in orders else 0
    trades = len(multi.trades) if multi is not None else 0
    nav_series = []
    for strategy in MAIN:
        if strategy in results and not results[strategy].daily.empty:
            frame = results[strategy].daily
            nav_series.append((STRATEGIES[strategy], COLORS[strategy], frame["date"], frame["nav"]))
    nav_chart = _line_chart(nav_series, "五种策略的每日净值", "nav", "净值 / 初始资金 = 1", reference=1.0)
    ic = research.get("ic", pd.DataFrame())
    ic_block = ic.loc[ic["factor"].eq("composite")].sort_values("date") if "factor" in ic else pd.DataFrame()
    ic_chart = _line_chart(
        [("三因子合成 Rank IC", COLORS["multifactor"], ic_block["date"], ic_block["ic"])],
        "三因子合成的月度 Rank IC", "ic", "Rank IC / 无量纲", reference=0.0,
    ) if not ic_block.empty else '<p class="empty">没有满足至少 5 只有效股票要求的完整 IC 观测。</p>'

    metric_sections = []
    ordered_metrics = metrics_frame.copy()
    for split in ["all", *config.get("splits", {}).keys()]:
        subset = ordered_metrics.loc[ordered_metrics["split"].eq(split) & ordered_metrics["strategy"].isin(MAIN)].copy()
        if not subset.empty:
            subset["_order"] = subset["strategy"].map({name: i for i, name in enumerate(MAIN)})
            subset = subset.sort_values("_order")
        bounds = [start, end] if split == "all" else config["splits"][split]
        sessions = int(subset["n_days"].iloc[0]) if not subset.empty and "n_days" in subset else 0
        metric_sections.append(f'<h3>{_text(SPLITS.get(split, split))}<span class="period">{_text(bounds[0])} → {_text(bounds[1])} · {sessions} 个交易日</span></h3>' + _metric_table(subset))

    summaries = research.get("ic_summary", pd.DataFrame())
    summary_rows = []
    for split in config.get("splits", {}):
        for factor in FACTORS:
            subset = summaries.loc[summaries["split"].eq(split) & summaries["factor"].eq(factor)] if not summaries.empty else summaries
            for row in subset.to_dict("records"):
                summary_rows.append([_text(SPLITS.get(split, split)), _text(FACTORS[factor]),
                                     _number(row.get("n"), 0), _number(row.get("mean_ic"), 4),
                                     _number(row.get("ic_std"), 4), _number(row.get("icir"), 3),
                                     _number(row.get("hac_tstat"), 3), _number(row.get("hac_lags"), 0)])
    ic_table = _table(["区间", "因子", "有效月数", "平均 Rank IC", "IC 标准差", "ICIR", "HAC t 值", "HAC 滞后月数"], summary_rows)

    group_frame = research.get("groups", pd.DataFrame())
    group_split = "test"
    if not group_frame.empty and "test" not in set(group_frame["split"]):
        group_split = str(group_frame["split"].iloc[-1])
    group_chart = _group_chart(group_frame, group_split)
    correlation = research.get("correlation", pd.DataFrame())
    correlation_rows = []
    if not correlation.empty:
        averages = correlation.groupby(["factor_a", "factor_b"])["correlation"].mean()
        for left in FACTORS:
            row = [_text(FACTORS[left])]
            for right in FACTORS:
                value = 1.0 if left == right else averages.get((left, right), averages.get((right, left), np.nan))
                row.append(_number(value, 3))
            correlation_rows.append(row)
    correlation_table = _table(["因子得分", *FACTORS.values()], correlation_rows)

    sensitivity = metrics_frame.loc[metrics_frame["strategy"].astype(str).str.startswith("multifactor")].copy()
    scenario_names = ["multifactor" if float(value) == 1 else f"multifactor_cost{float(value):g}"
                      for value in sorted(set([1.0, *config.get("cost_multipliers", [0, 1, 2])]))]
    sens_rows = []
    for split in ["all", *config.get("splits", {}).keys()]:
        for strategy in scenario_names:
            for row in sensitivity.loc[sensitivity["split"].eq(split) & sensitivity["strategy"].eq(strategy)].to_dict("records"):
                sens_rows.append([_text(SPLITS.get(split, split)), _text(_strategy_label(strategy)),
                                  _percent(row.get("total_return")), _percent(row.get("annual_return")),
                                  _number(row.get("sharpe")), _percent(row.get("max_drawdown")), _number(row.get("total_cost"))])
    sensitivity_table = _table(["区间", "成本情景", "累计收益", "年化收益", "夏普", "最大回撤", "成本合计 / 元"], sens_rows)
    quality_pairs = [
        ("数据类型", "模拟数据" if synthetic else "真实行情 · 固定教学股票池"),
        ("行情行数", _number(quality.get("rows"), 0)),
        ("股票数量", _number(quality.get("symbols"), 0)),
        ("输入日历会话数", _number(quality.get("calendar_sessions"), 0)),
        ("重复日期 / 股票键", _number(quality.get("duplicate_keys"), 0)),
        ("股票池有效成员缺失行情", _number(quality.get("missing_eligible_rows"), 0)),
        ("正式研究区间缺失行情", _number(quality.get("missing_eligible_rows_in_study"), 0)),
        ("换手率字段缺失行", _number(quality.get("turnover_missing"), 0)),
        ("历史成交状态未知行", _number(quality.get("unknown_status_rows"), 0)),
        ("不可买 / 不可卖标记行", f'{_number(quality.get("blocked_buy_rows"), 0)} / {_number(quality.get("blocked_sell_rows"), 0)}'),
        ("三因子实际成交笔数 / 拒单数", f"{trades:,} / {rejected:,}"),
    ]
    quality_table = _table(["检查项", "本次记录"], [[_text(k), _text(v)] for k, v in quality_pairs])
    limits = list(dict.fromkeys(_translate_limit(item) for item in quality.get("limitations", metadata.get("limitations", []))))
    limits_html = "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in limits) + "</ul>" if limits else '<p>未记录额外限制；请人工核对数据来源与覆盖范围。</p>'
    source_details = [
        ("来源", source), ("输入数据区间（包含预热）", f"{first} → {last}"),
        ("研究区间", f"{start} → {end}"), ("价格处理", metadata.get("price_adjustment", "未记录")),
        ("股票池说明", metadata.get("universe", "未记录")),
    ]
    if metadata.get("retrieved_at_utc"):
        try:
            captured = datetime.fromisoformat(metadata["retrieved_at_utc"]).astimezone(timezone(timedelta(hours=8)))
            source_details.append(("行情抓取时间（北京时间）", captured.strftime("%Y-%m-%d %H:%M:%S")))
        except (TypeError, ValueError):
            source_details.append(("行情抓取时间（原记录）", metadata["retrieved_at_utc"]))
    if metadata.get("akshare_version"):
        source_details.append(("AKShare 版本", metadata["akshare_version"]))
    source_table = _table(["记录", "内容"], [[_text(k), _text(v)] for k, v in source_details])
    activity_desc = (f'{config.get("lookback",20)} 日平均换手率' if config.get("activity_mode") == "turnover" else
                     f'{config.get("activity_short",5)} 日均量 / {config.get("activity_long",20)} 日均量')
    direction_text = "；".join(f'{FACTORS[name]}偏好{"高" if config["directions"][name] > 0 else "低"}' for name in ["momentum", "volatility", "activity"])
    config_rows = [
        ("动量", f'复权收盘价 P[t] / P[t−{config.get("lookback",20)}] − 1'),
        ("波动率", f'最近 {config.get("lookback",20)} 个日收益的样本标准差（未年化）'),
        ("活跃度", activity_desc),
        ("预先固定方向", direction_text),
        ("预处理与合成", f'中位数 ± {config.get("mad_scale",3)} × 1.4826 × MAD 去极值，横截面 Z-score；三个得分等权'),
        ("选股与调仓", f'每月最后交易日收盘形成信号，下一交易日开盘执行；选前 {config.get("top_n",10)} 只，目标等权'),
        ("佣金 / 单边滑点 / 卖出税", f'{config.get("commission_bps",3)} / {config.get("slippage_bps",5)} / {config.get("sell_tax_bps",5)} bps；1 bps = 0.01%'),
        ("初始资金 / 年无风险利率", f'{_number(config.get("initial_cash",1e6),0)} 元 / {_percent(config.get("annual_risk_free",0))}'),
    ]
    config_table = _table(["规则", "冻结设置"], [[_text(k), _text(v)] for k, v in config_rows])
    evidence_links = [
        ("metrics.csv", "策略绩效表"), ("ic.csv", "逐月 IC"), ("ic_summary.csv", "IC / ICIR 汇总"),
        ("groups.csv", "逐月分组收益"), ("correlation.csv", "因子相关性"), ("labels.csv", "未来收益标签"),
        ("factors.csv", "每日因子与得分"), ("research.sqlite", "SQLite 研究数据库"),
        ("config_snapshot.json", "冻结参数"), ("data_quality.json", "数据质量记录"), ("manifest.json", "输入与代码校验清单"),
    ]
    link_html = "".join(f'<a href="{name}" download>{_text(label)}<span>{name}</span></a>' for name, label in evidence_links)
    trade_links = "".join(
        f'<tr><td>{_text(_strategy_label(name))}</td><td><a href="daily_{_text(name)}.csv" download>每日净值</a></td><td><a href="trades_{_text(name)}.csv" download>成交记录</a></td><td><a href="orders_{_text(name)}.csv" download>订单 / 拒单</a></td><td><a href="positions_{_text(name)}.csv" download>每日持仓</a></td></tr>'
        for name in results
    )
    distribution_chart = _factor_histograms(path.parent / "factors.csv", config)
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>A股多因子研究 · {_text(subheading)}</title>
<style>
:root{{--ink:#1c2c36;--muted:#63717b;--line:#dce3e6;--paper:#fff;--ground:#f4f6f6;--accent:#17695c;--soft:#eaf3ef}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--ground);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:14px;line-height:1.8}}
a{{color:#165f8f;text-underline-offset:3px}}a:hover{{color:#104c40}}.page{{width:min(1180px,calc(100% - 40px));margin:40px auto 56px}}
header{{padding:34px 40px;background:#153d36;color:#fff;border-radius:14px 14px 0 0}}.eyebrow{{font-size:12px;letter-spacing:2px;color:#b9d6c9;margin:0 0 12px}}h1{{font-size:32px;letter-spacing:-.5px;line-height:1.35;margin:0 0 12px;font-weight:700}}header p{{margin:0;color:#d7e6df;max-width:800px}}
.banner{{padding:15px 26px;font-weight:700;background:#fff0d7;color:#6d4611;border:1px solid #e6cfaa;border-top:0;border-radius:0 0 12px 12px;line-height:1.65}}
.snapshot{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0 28px}}.stat{{background:white;border:1px solid var(--line);border-radius:10px;padding:17px 20px}}.stat span{{display:block;color:var(--muted);font-size:12px}}.stat strong{{font-size:21px;display:block;margin:4px 0 1px;letter-spacing:-.3px}}.stat small{{color:var(--muted);font-size:11px}}
nav{{display:flex;flex-wrap:wrap;gap:8px 24px;padding:0 2px 20px;font-size:13px}}nav a{{color:#405c58;text-decoration:none}}
section{{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:30px 34px;margin:0 0 20px;scroll-margin-top:20px}}.section-label{{color:var(--accent);font-size:11px;font-weight:700;letter-spacing:1.5px;margin-bottom:3px}}h2{{font-size:23px;line-height:1.45;margin:0 0 11px;letter-spacing:-.2px}}h3{{font-size:16px;margin:26px 0 10px}}p{{margin:8px 0 14px}}.intro{{color:#4c5e68;max-width:950px}}.caption,.note{{font-size:12px;color:var(--muted);margin:10px 0 0}}.note{{background:#f4f7f5;border-left:3px solid #91b7a7;padding:11px 14px}}.period{{font-size:11px;font-weight:400;color:var(--muted);margin-left:14px;white-space:normal}}
.chart{{display:block;width:100%;height:auto;margin-top:18px;overflow:visible}}.grid-line{{stroke:#e5ebed;stroke-width:1}}.reference-line{{stroke:#83918f;stroke-width:1.2;stroke-dasharray:4 4}}.axis-text{{font-size:11px;fill:#68757e;font-family:inherit}}.axis-unit{{font-size:11px;fill:#52646b;font-family:inherit}}.legend{{display:flex;flex-wrap:wrap;gap:8px 23px;justify-content:center;margin:3px 0 12px;font-size:12px;color:#3b4e58}}.legend span{{display:inline-flex;align-items:center}}.legend i{{height:3px;width:19px;display:inline-block;margin-right:7px;border-radius:2px}}
.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:7px;margin:10px 0 5px}}table{{border-collapse:collapse;width:100%;font-size:12px;line-height:1.6}}caption{{text-align:left;padding:10px 13px;font-weight:600;background:#f3f6f5}}th{{background:#edf3f1;color:#3b5551;font-weight:600;text-align:right;padding:11px 12px;white-space:nowrap}}td{{border-top:1px solid #e6ebed;text-align:right;padding:10px 12px;white-space:nowrap;font-variant-numeric:tabular-nums}}th:first-child,td:first-child{{text-align:left}}tbody tr:nth-child(even){{background:#fafbfb}}tbody tr:hover{{background:#f1f6f3}}.wrap-table td{{white-space:normal;text-align:left;min-width:220px}}.wrap-table td:first-child{{width:23%;min-width:145px;color:#48605b}}.empty{{padding:20px;background:#f7f9f8;color:var(--muted);border-radius:6px;font-size:13px}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.two-col h3{{margin-top:13px}}ul{{padding-left:21px;margin:7px 0 12px}}li{{margin:7px 0}}details{{border-top:1px solid var(--line);padding:14px 0 2px;margin-top:18px}}summary{{cursor:pointer;color:#335f53;font-weight:600}}.evidence-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px}}.evidence-grid a{{background:#f5f8f6;border:1px solid #dce7e1;padding:12px 14px;border-radius:6px;font-size:12px;text-decoration:none}}.evidence-grid span{{display:block;color:#73817b;font-size:10px;font-family:Consolas,monospace;margin-top:2px}}footer{{color:var(--muted);font-size:11px;padding:4px 5px}}.timing{{display:flex;align-items:stretch;gap:12px;margin:16px 0}}.timing div{{flex:1;background:#f1f6f3;border:1px solid #dbe7df;border-radius:7px;padding:12px 15px;font-size:12px}}.timing b{{display:block;font-size:13px;margin-bottom:3px}}.timing .arrow{{flex:0;align-self:center;background:transparent;border:0;padding:0;color:#6e8c7e;font-size:20px}}
@media(max-width:820px){{.page{{width:calc(100% - 24px);margin-top:16px}}header{{padding:26px 24px}}h1{{font-size:27px}}section{{padding:24px 20px}}.snapshot{{grid-template-columns:repeat(2,1fr);gap:10px}}.stat{{padding:13px 15px}}.two-col{{grid-template-columns:1fr;gap:4px}}.evidence-grid{{grid-template-columns:repeat(2,1fr)}}.period{{display:block;margin-left:0;margin-top:3px}}}}
@media(max-width:500px){{.evidence-grid{{grid-template-columns:1fr}}.timing{{flex-direction:column}}.timing .arrow{{display:none}}.banner{{padding:13px 18px;font-size:13px}}.stat strong{{font-size:18px}}nav{{gap:6px 15px}}h2{{font-size:21px}}}}
@media print{{body{{background:#fff}}.page{{width:100%;margin:0}}section{{break-inside:avoid;border-radius:0}}header{{border-radius:0}}nav,details{{display:none}}a{{color:inherit}}.table-wrap{{overflow:visible}}.evidence-grid{{grid-template-columns:repeat(3,1fr)}}}}
</style></head><body><main class="page">
<header><p class="eyebrow">ASHARE FACTOR LAB / RESEARCH BASELINE</p><h1>A股多因子选股与回测</h1><p>{_text(subheading)} · 数据 → 因子 → 检验 → 选股 → 执行 → 复核。所有结果由同一冻结配置生成，不自动判定因子有效或统计显著。</p></header>
<div class="banner" role="note">{_text(banner)}</div>
<div class="snapshot"><div class="stat"><span>研究区间</span><strong>{_text(str(start)[:4])}—{_text(str(end)[:4])}</strong><small>{_text(start)} 至 {_text(end)}</small></div><div class="stat"><span>输入股票数量</span><strong>{_number(quality.get("symbols"),0)} 只</strong><small>股票池范围以输入快照为准</small></div><div class="stat"><span>模型与调仓</span><strong>3 因子 · 月度</strong><small>固定等权 · 选前 {_text(config.get("top_n",10))} 只</small></div><div class="stat"><span>执行记录 · 三因子</span><strong>{trades:,} 笔成交</strong><small>{rejected:,} 笔拒单 · 保留现金与持仓</small></div></div>
<nav aria-label="报告目录"><a href="#performance">01 策略表现</a><a href="#factors">02 因子检验</a><a href="#costs">03 成本敏感性</a><a href="#rules">04 规则与边界</a><a href="#data">05 数据质量</a><a href="#evidence">06 复核文件</a></nav>
<section id="performance"><div class="section-label">01 / PORTFOLIO</div><h2>先比较完整链路的实际结果</h2><p class="intro">五种组合使用同一数据、完整因子可用股票池、月度调仓时点和基础成本设置。基准持有当期可用股票池的等权组合；三个单因子和多因子组合选取排名靠前的股票。</p>{nav_chart}<p class="caption">净值从初始资金 1 开始，包含现金、持仓浮动盈亏、佣金、卖出税和滑点。买不到会保留现金；卖不出会保留旧仓，实际持仓可能偏离目标等权。</p>{''.join(metric_sections)}<p class="note">相对基准收益 = (1 + 策略区间收益) / (1 + 基准区间收益) − 1。分区绩效来自同一条连续持仓回测，进入验证期或测试期时不清仓重启。年化按 252 个交易日；换手为成交买入额与卖出额之和 / 调仓前开盘资产，不除以二。最大回撤以负数表示。</p></section>
<section id="factors"><div class="section-label">02 / FACTOR DIAGNOSTICS</div><h2>因子能否解释下一持有期的收益排名</h2><p class="intro">Rank IC 衡量“本月信号得分排名”与“下一持有期收益排名”的相关性。这里使用预先统一方向的得分；正值表示高分股票当期的未来收益排名更靠前，负值表示相反。</p>{ic_chart}<p class="caption">收益标签从信号日之后的首个交易日开盘，计算到下一个月度调仓执行日开盘；使用复权价格，不扣成本、不处理无法成交，属于理论收益诊断。末尾不完整持有期和跨样本边界标签已剔除；空缺不等于 IC 为零。</p><h3>按时间区间汇总</h3>{ic_table}<p class="note">IC 至少需要 5 只有效股票。ICIR = 平均 IC / IC 的样本标准差，未年化；标准差为零时留空。HAC t 值采用最多 3 个月滞后的 Newey-West 调整，仅作描述，短样本与多重检验仍需进一步核查；此表不自动给出显著性结论。</p><h3>{_text(SPLITS.get(group_split, group_split))} · 分组收益</h3>{group_chart}<p class="caption">按有利方向得分从 G1（低分）到高分组排列。柱高为各月完整持有期理论收益的简单平均，非年化、未扣成本，不是可直接交易的多空组合净值。并列得分保持同组，实际组数可能不足设定值。</p><details><summary>查看因子得分之间的相关性</summary><p class="caption">对完整标签样本，先逐月计算横截面 Rank 相关，再取时间平均。高相关意味着得分信息可能重叠，不等于其中一个因子没有研究价值。</p>{correlation_table}</details>{distribution_chart}</section>
<section id="costs"><div class="section-label">03 / COST SENSITIVITY</div><h2>交易摩擦会改变多少结果</h2><p class="intro">固定股票池、因子方向和选股规则，仅将三因子策略的佣金、滑点、卖出税同时乘以 {_text('、'.join(f'{float(x):g}' for x in sorted(set([1.0,*config.get('cost_multipliers',[0,1,2])]))))}。基础成本为佣金 {_text(config.get("commission_bps",3))} bps / 单边滑点 {_text(config.get("slippage_bps",5))} bps / 卖出税 {_text(config.get("sell_tax_bps",5))} bps。</p>{sensitivity_table}<p class="caption">不同成本会影响可用现金和后续持仓数量，结果由各情景分别重新回测，不能简单从零成本净值减去一笔总费用。成本是假设参数，没有按历史费率变迁、最低佣金、成交容量或冲击成本逐项还原。</p></section>
<section id="rules"><div class="section-label">04 / FROZEN DESIGN</div><h2>规则先固定，再看结果</h2><div class="wrap-table">{config_table}</div><div class="timing"><div><b>月末 T 日收盘后</b>只使用截至 T 的历史行情<br>计算因子、标准化、排名</div><span class="arrow" aria-hidden="true">→</span><div><b>下一交易日开盘</b>按开盘价格与滑点尝试成交<br>先卖后买，受现金与买卖标记约束</div><span class="arrow" aria-hidden="true">→</span><div><b>每日收盘估值</b>现金 + 剩余持仓市值<br>下个月按新信号再次调仓</div></div><div class="two-col"><div><h3>本版已经明确处理</h3><ul><li>信号与成交错开到下一交易日；不会按已知信号日的收盘价成交。</li><li>缺失交易日不会缩短因子窗口；已持仓缺失估值时终止，不隐式填充收益。</li><li>受限买入保留现金，受限卖出保留持仓；未成交订单当日失效，不在次日自动补单。</li><li>研究标签跨开发、验证、测试边界时剔除，最终不完整标签不参与 IC。</li></ul></div><div><h3>解释结果时保留的边界</h3><ul><li>使用复权价格和可分割的经济份额近似；没有整手、最低佣金与公司行为现金流的逐笔核算。</li><li>期末按最后收盘价估值，没有假设卖出全部持仓，因此没有额外收取期末清仓费。</li><li>成交标记只有在历史来源可靠时才能代表真实限制；未知状态的教学假设已在数据区披露。</li><li>不根据最终测试期收益临时改方向、参数或样本。这里的测试期结果是冻结基线读数。</li></ul></div></div></section>
<section id="data"><div class="section-label">05 / DATA EVIDENCE</div><h2>数据覆盖与可信边界</h2><p class="intro">样本范围、复权方式和历史可成交状态会直接影响研究结论。通过格式校验只说明数据满足本程序输入条件，不能替代对历史成员、退市和成交约束的核查。</p><div class="two-col"><div>{quality_table}</div><div><h3>本次必须保留的限制</h3>{limits_html}</div></div><details><summary>查看数据来源与快照记录</summary><div class="wrap-table">{source_table}</div><p class="caption">完整原始记录、依赖版本、输入文件哈希、配置哈希与代码哈希见 manifest.json。AKShare 接口说明见<a href="https://akshare.akfamily.xyz/data/stock/stock.html">官方文档</a>。</p></details></section>
<section id="evidence"><div class="section-label">06 / REPRODUCIBILITY</div><h2>从图表回到每一条记录</h2><p class="intro">以下文件与本页保存在同一实验目录。打开 CSV 可以逐条复核标签、因子、净值和成交；SQLite 可用于练习查询与关联。</p><div class="evidence-grid">{link_html}</div><details><summary>下载各策略的净值、成交与持仓</summary><div class="table-wrap"><table><thead><tr><th scope="col">策略</th><th scope="col">净值</th><th scope="col">成交</th><th scope="col">订单</th><th scope="col">持仓</th></tr></thead><tbody>{trade_links}</tbody></table></div></details><p class="note">本页用于检查研究基线，并不自动支持 H1 / H2 / H3。下一步应先解释样本范围、方向、成本和样本外差异，再把有证据支持的发现写入研究报告。</p></section>
<footer>Ashare Factor Lab · 本页可离线打开，无远程脚本、字体或图表依赖。空缺统计量用“—”表示，不能解释为零。</footer>
</main></body></html>'''
    path.write_text(html, encoding="utf-8")
