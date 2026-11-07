# 第 19 步：我把教学过程整理成可复现、可核对的交付

<!-- SNAPSHOT_NOTE -->
## 我的数据准备说明

我在本页记录的是完整快照上的实际运行。如果我从 GitHub 克隆源码，我先在仓库根目录运行 `python publication/restore_snapshot.py`，恢复同版本的 `data/` 与 `runs/`，再执行本步。[完整数据与大型结果索引](../../publication/ASSET_INDEX.md)保留全部路径和哈希；本页图表与 Notebook 已保存输出可直接阅读。


## 我的目标：把“已经跑过”变成可以检查的证据

我在前 18 步已经完成数据读取、收益和因子计算、检验、选股、交易记账、历史绩效、基准与成本对照、分段检查和真实快照回放。最后一步我不增加一个复杂模型，也不再以更高收益作为完成标准。我把入口、环境、数据身份、参数、账户审计、测试日志、图表、方法边界和文件清单放在一起，使项目迁移到另一个目录后仍能检查和重新运行。

我把交付分成两层：第一层是已经完成的原教学工程及其 ZIP 验收；第二层是当前公开仓库 `ThreshoLdnnis/QuantitativeTeamProject1` 的文档组织与发布。我在本次仓库中新增每步独立 README 和 notebook，是为了完整记录此前的学习流程，不把文档生成冒称为新增的实证结果或实盘验证。

## 我的目录与前置环境

我先定位仓库根目录：它包含 `pyproject.toml`、`configs`、`src`、`examples`、`data`、`runs` 和 `lessons`。脚本通过 `Path(__file__).resolve().parents[1]` 定位项目，不依赖我个人电脑的绝对路径。记录文件里可能保存原运行机器的路径；那是历史来源字段，不应该成为另一台机器的代码依赖。

我在新机器或新解压目录创建独立环境，不复制原 `.venv`：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
```

如果我没有 Python Launcher，我把第一行换成本机已安装解释器的完整路径，例如 PowerShell 中的 `& 'C:\实际安装位置\python.exe' -m venv .venv`。Windows 应用商店别名不是可靠的已安装解释器。后续我显式调用 `.venv\Scripts\python.exe`，避免激活状态和系统 PATH 引入歧义。

我的已验证直接依赖记录在 [requirements-tested.txt](../../requirements-tested.txt)：Python 3.12.14 环境下使用 NumPy 2.3.5、pandas 3.0.1、Matplotlib 3.11.2。这个文件不是完整传递依赖锁。`.[plots]` 包含课程绘图依赖；只安装核心包不足以运行全部图片课程。已有真实快照的离线复现不需要 AKShare，新的联网下载才使用可选 `market` 依赖。

## 我区分三种第十九步运行方式

我阅读 [完整脚本](../../examples/19_finalize_project.py) 后，根据目的选择一种方式，而不是无意义地连续重复重跑：

```powershell
# 我校验现成成果，更新总览与证据，不创建ZIP
.\.venv\Scripts\python.exe examples/19_finalize_project.py --verify-only
```

```powershell
# 我校验现成成果、更新总览与清单，并创建新ZIP
.\.venv\Scripts\python.exe examples/19_finalize_project.py
```

```powershell
# 我从当前固定快照重跑模拟流水线及01-18，再校验并打包
.\.venv\Scripts\python.exe examples/19_finalize_project.py --rebuild
```

`--verify-only` 不是完全只读：它仍会更新测试日志、环境、总览和清单，只是不重跑实验、不创建 ZIP。`--rebuild` 可能运行数分钟，会覆盖约定输出目录，所以我在保留自定义试验时先另存。已有模拟输入时，它复用当前快照；输入元数据不存在时，脚本按固定种子 `20261102` 初始化模拟数据。

当前公开仓库的整理过程中，我不把“新 README/notebook 已写入”当成再次执行 `--rebuild` 的证据。完整重跑、仅校验、notebook 语法验证和公开发布是不同操作，我分别记录实际执行范围。尤其是 notebook 文件存在，不等于所有单元在新环境中已经按序执行。

## 我的运行入口为什么不拼接 shell 字符串

第十九步通过参数列表调用同一个解释器：

```python
environment["PYTHONPATH"] = str(root / "src")
completed = subprocess.run(
    [sys.executable, *map(str, args)], cwd=root, env=environment,
    capture_output=True, text=True, encoding="utf-8", errors="replace",
)
```

我在第一行明确子进程使用当前项目源码；参数列表把脚本与参数分开，不把路径和命令拼成可能被 shell 再解释的字符串。`cwd=root` 让所有相对文件名从项目根目录解析。`sys.executable` 确保父子运行使用同一个环境。UTF-8 日志避免中文终端编码差异掩盖错误。

脚本把标准输出与错误输出保存为每步日志，非零返回码立即停止交付。重跑逻辑先核对第 01—18 步编号是否完整，再按顺序执行；这种顺序保护第 11 读第 10、第 13 读第 12、第 17 读第 16 等文件依赖。我不在前一课失败后继续生成一套看似完整的新报告。

## 我验收的五类事实

### 我确认测试确实执行，而不是只有一句“通过”

```python
match = re.search(r"Ran (\d+) tests?", log)
if match is None or int(match.group(1)) == 0:
    raise ValueError("未确认执行了核心测试")
```

我在命令成功返回后仍检查日志包含非零测试数量。原教学交付有 35 项 unittest：11 项成交与指标，13 项数据与配置，11 项因子与研究。它们覆盖信号后下一开盘成交、买前与旧仓隔夜收益、拒单、现金缩放、首笔成本、缺失持仓价格、未来扰动、完整交易日窗口、边界标签清除、并列值和 SQLite 唯一键。

这些测试验证的是实现是否符合已写明的规则，不证明未覆盖的真实交易条件正确，也不自动证明我已经能脱离代码独立完成全部计算。

### 我确认输入身份，而不是只看文件名

`source_audit` 调用 `load_dataset`，先验证价格、日期、标记、主键与日历，再核对真实原始响应的 61 份 SHA-256。它也与第 18 步保存的标准化四文件哈希比对。我保留模拟与真实数据两套来源，不将人工股票输出混进真实结果表。

模拟输入为 40 股、73080 行、1827 个含预热的模拟工作日；真实输入为 30 股、50927 行、1699 个供应商历史日历交易日。正式模拟账户有 1566 日，正式真实账户有 727 日。输入期与评价期不是同一个概念，不能只用总行数猜绩效区间。

### 我确认账户金额与收益都能互相解释

```python
identity_error = daily["equity"] - daily["cash"] - stock_market_value
np.testing.assert_allclose(identity_error, 0, rtol=0, atol=1e-7)
np.testing.assert_allclose((1 + daily["return"]).cumprod(skipna=False),
                           daily["nav"], rtol=0, atol=1e-10)
```

我在第一组检查现金加实际持仓市值等于权益；第二组检查日收益增长倍数能还原净值。我还核对逐笔佣金、税与滑点之和对应每日 `cost`，以及成交严格晚于信号。第十九步覆盖 14 条主要账户路径：第 15 步策略一条，第 16 步六条，第 18 步七条。

我对第 17 步只连乘三段增长倍数并核对费用和，不把局部最大回撤简单相加或取最大值来冒充全期回撤。跨段首日收益仍保留，起点是前一交易日的实际权益。

### 我确认文档能从结论回到数据

总览从现有 CSV 读取数字，而不是凭记忆重新填写。图来自已经保存并检查的课程 PNG，复制后再次比较哈希。我用相对链接连接到指标、账户、方法和失败记录，使目录移动后仍可以定位材料。

本地链接检查只确认目标存在且没有越出交付目录；它不证明外部网站始终可用，也不是 HTML 布局的目视验收。我把这几种验证清楚区分，不用一个“链接通过”替代所有展示质量检查。

### 我确认包内文件与清单是同一批内容

我对每个纳入文件记录相对路径、字节数和 SHA-256。清单自身被排除在自己的哈希列表之外：若把自身也加入，写入新哈希就会再次改变文件，形成自引用循环。

```python
entries = [dict(path=path.relative_to(root).as_posix(),
                bytes=path.stat().st_size, sha256=sha256(path))
           for path in project_files(root) if path != manifest_path]
for entry in entries:
    bundle.write(root / entry["path"], f"{prefix}/{entry['path']}")
```

我在清单的每一行保存 `path/bytes/sha256` 三项，随后按相同相对路径写入包内。ZIP 路径使用项目目录名作前缀，内部保持相对结构。清单另加一次，不能重复加入。这是完整打包函数中的精选片段，打开、关闭与复核压缩包仍由完整脚本负责。

## 我为什么还要检查 ZIP，而不是只检查工作目录

我的打包逻辑排除 `.venv`、`__pycache__`、`.git`、`*.pyc`、`*.egg-info` 和已有 ZIP，避免把本机环境或旧交付递归包进去。输出先写到临时文件，再逐项检查 ZIP CRC，并对压缩包中每个清单文件重新计算 SHA-256。全部一致后才替换正式 ZIP。

我同时生成包外 `.sha256` 和交付记录。包外记录保存 ZIP 整体哈希、大小、文件数与核对状态；它不再被放回正在计算哈希的同一个 ZIP。解压目录重命名后，新包前缀和记录中的清单路径都由当前目录名生成，避免写死本机工程名称。

这些检查保护的是“交出去的文件与验收时记录的是同一批内容”。它们不能证明文件里的每个金融假设都成立，所以方法边界仍必须与包一起保留。

## 我记录原教学交付的完成事实，但不混同本次仓库体积

原教学工程在 2026-11-07 完成顺序重跑与验收记录：35 项核心测试通过，14 条账户路径通过，228 个本地引用检查通过。旧 ZIP 有 411 个文件，大小 `111713738` 字节，约 106.54 MiB，不包含 `.venv`。旧包整体 SHA-256 记录为：

```text
8cb089d03f27738904abae2c6548f20ae13880b8b27751260f542d7d078e0656
```

原交付随后还做了另一目录解压与单独环境验证，安装相同直接依赖后运行了第 17 步绘图和第 19 步 `--verify-only`；记录显示没有安装 AKShare，导入的模块来自迁移后的源码目录。这支持“现成快照可离线迁移复现”的有限结论，不是对所有操作系统或未来依赖版本的保证。

我现在给公开仓库增加七篇本阶段 README、前面步骤的文档以及 notebook，文件集合和总大小都会变化。**411 文件、106.54 MiB 和上面的 ZIP 哈希仅属于原交付，不能充当当前 GitHub 仓库或新打包文件的大小与哈希。** 新仓库的发布状态、commit、清单和 notebook 验证范围应以本次发布证据为准。我也不把旧测试结果冒称为新文档每个代码单元都经过执行。

## 我的结课结果与尚未完成的研究条件

我可以从 [第 15 步摘要](../../runs/first_demo_20261107/lesson15_full_backtest/summary.json)、[第 16 步六组指标](../../runs/first_demo_20261107/lesson16_benchmark_cost/metrics.csv)、[第 17 步跨段核对](../../runs/first_demo_20261107/lesson17_split_stability/reconciliation.csv) 和 [第 18 步真实结果](../../runs/lesson18_real_market/strategy_benchmark_metrics.csv)复核本轮结论：模拟一倍策略累计约 -3.5632%，同池基准约 14.1581%；固定 30 股真实教学回放累计约 27.0063%，基准约 19.7282%。不同样本、区间和交易假设下的数字不能直接相互证明。

我保留真实固定网格缺口 43、eligible 缺口 37、研究段缺口 0 的区别；真实 `status_known` 仍未知，`--allow-unknown-status` 只是显式教学假设。后复权小数单位不是原始股数账户，固定费率不是历史收费表，期末仍持仓而未假设清仓。完整历史已经查看，分段统计不是新的未见测试。

我的教学闭环完成不等于完成完整 A 股实证论文。动态历史股票池、退市/ST/IPO 资格、停复牌和开盘涨跌停、企业行动现金流、整手与最低佣金、容量冲击和新时期检验仍需后续工作。2020—2025 年真实区间缺价失败记录保留，没有因较短教学区间可运行就被改写为成功。

我把最终验收落到能够解释的具体问题：一只股票的日收益如何形成；一个因子用了哪些历史；一个未来标签何时开始结束；一次成交如何影响现金与数量；一个跨年首日损益如何保留；一项回撤从哪个峰值到哪个谷底；一份报告结论能回到哪张 CSV。我的文档记录这些过程与证据，不虚构已经独立掌握、稳定盈利或完成实盘。

[我的第十九步脚本](../../examples/19_finalize_project.py) · [完整复现与验收指南](../../docs/06_19课复现与交付指南.md) · [教学项目总览](../../docs/07_教学项目总览.md)

<!-- GENERATED_FULL_SOURCE_START -->

## 我的完整脚本源码

我把本步完整实现保留在 [19_finalize_project.py](../../examples/19_finalize_project.py)。精选代码解释在前文，以下代码与脚本文件一致。

```python
r"""第十九课：复现、校验、更新总览与交付包。

默认：校验已有课程结果、更新 Markdown 总览和清单、生成新版 ZIP。
--verify-only：执行校验、更新总览和清单，不创建 ZIP。
--rebuild：先从快照顺序运行模拟流水线及 01-18 课，再执行上述流程。
"""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import pandas as pd

from ashare_lab.backtest import metrics
from ashare_lab.data import load_dataset, sha256, write_json


IGNORED_PARTS = {".venv", "__pycache__", ".git", ".pytest_cache", ".ruff_cache"}
ARCHIVE_NAME = "A股多因子研究系统_教学完整版.zip"


def run_logged(root, args, log_path):
    """显式参数列表，不拼 shell 命令；失败保留日志并停止交付。"""
    print("运行：", " ".join(str(x) for x in args), flush=True)
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run([sys.executable, *map(str, args)], cwd=root, env=environment,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        print(completed.stdout + completed.stderr, flush=True)
        raise RuntimeError(f"命令失败，日志：{log_path}")
    return completed.stdout + completed.stderr


def rebuild(root, evidence_dir):
    """课程路径固定；已有输入保持不变，缺少输入时才生成固定种子样本。"""
    run_dir = root / "runs" / "first_demo_20261107"
    args = ["-m", "ashare_lab"]
    if (run_dir / "input" / "metadata.json").exists():
        args += ["run", "--data", str(run_dir / "input"), "--config", "configs/baseline.json", "--out", str(run_dir)]
    else:
        args += ["demo", "--config", "configs/baseline.json", "--out", str(run_dir), "--seed", "20261102"]
    run_logged(root, args, evidence_dir / "rebuild_logs" / "00_pipeline.log")
    lessons = sorted(p for p in (root / "examples").glob("[0-9][0-9]_*.py") if int(p.name[:2]) < 19)
    if [int(p.name[:2]) for p in lessons] != list(range(1, 19)):
        raise ValueError("第 01-18 课脚本不完整。")
    for path in lessons:
        run_logged(root, [path.relative_to(root)], evidence_dir / "rebuild_logs" / f"{path.stem}.log")
    write_json(evidence_dir / "rebuild_completed.json", dict(
        completed_at_utc=datetime.now(timezone.utc).isoformat(), status="passed", lessons=list(range(1, 19)),
        log_sha256={path.name: sha256(path) for path in sorted((evidence_dir / "rebuild_logs").glob("*.log"))},
    ))


def run_tests(root, evidence_dir):
    log = run_logged(root, ["-m", "unittest", "discover", "-s", "tests", "-v"], evidence_dir / "tests.log")
    match = re.search(r"Ran (\d+) tests?", log)
    if match is None or int(match.group(1)) == 0:
        raise ValueError("未确认执行了核心测试，停止交付。")
    return dict(status="passed", tests_run=int(match.group(1)), log="tests.log")


def source_audit(root):
    rows = []
    for folder in [root / "runs" / "first_demo_20261107" / "input", root / "data" / "market_teaching"]:
        prices, universe, calendar, metadata = load_dataset(folder)
        count = 0
        for name, expected in metadata.get("source_files", {}).items():
            if sha256(folder / "raw" / name) != expected:
                raise ValueError(f"原始快照哈希变化：{name}")
            count += 1
        rows.append(dict(dataset=folder.relative_to(root).as_posix(), kind=metadata["kind"],
                         price_rows=len(prices), symbols=int(prices["symbol"].nunique()),
                         calendar_sessions=len(calendar), verified_raw_files=count))
    market = root / "data" / "market_teaching"
    method = json.loads((root / "runs" / "lesson18_real_market" / "methodology.json").read_text(encoding="utf-8"))
    for name, expected in method["snapshot_input_sha256"].items():
        if sha256(market / name) != expected:
            raise ValueError(f"第 18 课输入快照变化：{name}")
    return rows


def audit_account(name, folder, suffix, initial_cash=1_000_000):
    def read(field):
        return pd.read_csv(folder / f"{field}{suffix}.csv", parse_dates=["date"], float_precision="round_trip")
    daily, positions, trades = read("daily"), read("positions"), read("trades")
    trades["signal_date"] = pd.to_datetime(trades["signal_date"])
    if daily.empty or daily["date"].duplicated().any() or not daily["date"].is_monotonic_increasing:
        raise ValueError(f"{name}: 日期不完整或排序错误。")
    invested = positions.groupby("date")["market_value"].sum()
    identity_error = daily["equity"] - daily["cash"] - daily["date"].map(invested).fillna(0)
    np.testing.assert_allclose(identity_error, 0, rtol=0, atol=1e-7)
    np.testing.assert_allclose(daily["nav"], daily["equity"] / initial_cash, rtol=0, atol=1e-10)
    np.testing.assert_allclose((1 + daily["return"]).cumprod(skipna=False), daily["nav"], rtol=0, atol=1e-10)
    np.testing.assert_allclose(daily["cost"].sum(), trades[["commission", "tax", "slippage_cost"]].sum().sum(),
                               rtol=0, atol=1e-7)
    assert (daily["cash"] >= 0).all()
    assert (trades["date"] > trades["signal_date"]).all()
    return dict(case=name, days=len(daily), max_equity_identity_error=float(identity_error.abs().max()),
                total_return=float(metrics(daily)["total_return"]), checks="passed")


def account_audits(root):
    demo = root / "runs" / "first_demo_20261107"
    rows = [audit_account("lesson15_strategy", demo / "lesson15_full_backtest", "")]
    for multiplier in [0, 1, 2]:
        for portfolio in ["strategy", "benchmark"]:
            name = f"{portfolio}_cost{multiplier}"
            rows.append(audit_account(f"lesson16_{name}", demo / "lesson16_benchmark_cost" / name, ""))
    market = root / "runs" / "lesson18_real_market" / "experiment"
    for name in ["benchmark", "momentum", "volatility", "activity", "multifactor", "multifactor_cost0", "multifactor_cost2"]:
        rows.append(audit_account(f"lesson18_{name}", market, f"_{name}"))
    periods = pd.read_csv(demo / "lesson17_split_stability" / "metrics.csv", float_precision="round_trip")
    for portfolio, name in [("strategy", "lesson16_strategy_cost1"), ("benchmark", "lesson16_benchmark_cost1")]:
        selected = periods.loc[periods["portfolio"].eq(portfolio)]
        expected = next(row["total_return"] for row in rows if row["case"] == name)
        np.testing.assert_allclose((1 + selected["total_return"]).prod() - 1, expected, rtol=0, atol=1e-10)
    return rows


def environment_record():
    versions = {}
    for name in ["numpy", "pandas", "matplotlib", "pip"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    if any(versions[name] is None for name in ["numpy", "pandas", "matplotlib"]):
        raise ValueError('请先安装 requirements-tested.txt 和 ".[plots]"，再完成课程交付。')
    return dict(python=platform.python_version(), executable=sys.executable, platform=platform.platform(),
                dependencies=versions, note="Recorded installed direct versions, not a full transitive lock.")


def md_table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |",
                       *["| " + " | ".join(map(str, row)) + " |" for row in rows]])


def write_overview(root, evidence):
    """总览从 CSV 取数，图直接复制已检查的课程导出。"""
    demo = root / "runs" / "first_demo_20261107"
    sim = pd.read_csv(demo / "lesson16_benchmark_cost" / "metrics.csv")
    periods = pd.read_csv(demo / "lesson17_split_stability" / "comparison.csv")
    real = pd.read_csv(root / "runs" / "lesson18_real_market" / "strategy_benchmark_metrics.csv")
    quality = json.loads((root / "runs" / "lesson18_real_market" / "data_quality.json").read_text(encoding="utf-8"))
    figures = root / "docs" / "figures"
    figures.mkdir(exist_ok=True)
    for source, name in [(demo / "lesson16_benchmark_cost" / "benchmark_cost_comparison.png", "cost_comparison.png"),
                         (demo / "lesson17_split_stability" / "split_stability.png", "split_stability.png"),
                         (root / "runs" / "lesson18_real_market" / "real_market_nav_drawdown.png", "real_market.png")]:
        shutil.copyfile(source, figures / name)
        assert sha256(source) == sha256(figures / name)

    def performance(frame, key, value):
        selected = frame.loc[frame[key].eq(value)].iloc[0]
        dd = selected.get("max_drawdown_amplitude", selected["max_drawdown"])
        return [f"{selected['total_return']:+.4%}", f"{selected['annual_return']:+.4%}",
                f"{selected['annual_volatility']:.4%}", f"{abs(dd):.4%}"]
    sim_table = md_table(["组合（1 倍成本）", "累计收益", "252 日年化", "年化波动", "最大回撤幅度"],
                         [["三因子策略", *performance(sim, "case", "strategy_cost1")],
                          ["同池等权基准", *performance(sim, "case", "benchmark_cost1")]])
    cost_rows = []
    for multiplier in [0, 1, 2]:
        strategy = sim.loc[sim["case"].eq(f"strategy_cost{multiplier}")].iloc[0]
        base = sim.loc[sim["case"].eq(f"benchmark_cost{multiplier}")].iloc[0]
        cost_rows.append([str(multiplier), f"{strategy['total_return']:+.4%}", f"{base['total_return']:+.4%}",
                          f"{strategy['total_cost']:,.2f}"])
    cost_table = md_table(["费用倍数", "策略累计收益", "同档基准累计收益", "策略账面成本（元）"], cost_rows)
    split_table = md_table(["区间", "日数", "策略累计收益", "基准累计收益", "比值相对收益"],
                           [[row.label, row.n_days, f"{row.strategy_total_return:+.4%}",
                             f"{row.benchmark_total_return:+.4%}", f"{row.relative_return:+.4%}"]
                            for row in periods.itertuples()])
    real_all = real.loc[real["split"].eq("all")]
    real_table = md_table(["组合（1 倍成本）", "累计收益", "252 日年化", "年化波动", "最大回撤幅度"],
                          [["三因子策略", *performance(real_all, "strategy", "multifactor")],
                           ["同池等权基准", *performance(real_all, "strategy", "benchmark")]])
    real_year_rows = []
    for phase, label in [("development", "2023 开发"), ("validation", "2024 验证"), ("test", "2025 测试")]:
        rows = real.loc[real["split"].eq(phase)].set_index("strategy")
        real_year_rows.append([label, f"{rows.loc['multifactor', 'total_return']:+.4%}",
                               f"{rows.loc['benchmark', 'total_return']:+.4%}",
                               f"{rows.loc['multifactor', 'relative_return']:+.4%}"])
    real_year_table = md_table(["既定区间", "策略累计收益", "基准累计收益", "比值相对收益"], real_year_rows)
    test_count = evidence["tests"]["tests_run"]
    text = f"""# 教学闭环已跑通，策略有效性仍需进一步验证

我在这份总览中整理 19 课参考实现、输入快照和已运行结果。行情观察截止 2025-12-31；本次交付校验时间为 {evidence['verified_at_utc']}。

## 报告摘要

- 模拟数据验证了完整工程流程，三因子策略累计收益约 −3.56%，同池基准约 +14.16%。无费策略也落后于同档无费基准，不能把差距全部归因于费用。
- 固定 30 股真实行情教学回放在 2023—2025 年累计收益约 +27.01%，同池基准约 +19.73%；2025 年策略落后于基准。成交状态未核实、固定样本偏差等限制仍然影响结果解释。
- 第 01-18 课脚本、两类数据、SQL、研究表、账户记录和报告已保留；{test_count} 项核心测试通过。程序与交付可复现不等于因子有效、实盘可成交或学习者已独立掌握。

## 交付入口

先读 [19 课复现与交付指南](06_19课复现与交付指南.md)，再使用 [第 19 课入口](../examples/19_finalize_project.py)。

- [真实行情完整研究报告](../runs/lesson18_real_market/experiment/report.html)
- [模拟完整研究报告](../runs/first_demo_20261107/report.html)
- [本次校验记录](../runs/lesson19_delivery/verification.json)、[测试日志](../runs/lesson19_delivery/tests.log)、[环境记录](../runs/lesson19_delivery/environment.json)
- [文件哈希清单](../runs/lesson19_delivery/project_manifest.json)

## 我搭建了什么

流水线为：输入快照与数据检查 → 20 日动量、20 日日收益波动、5/20 日均量比 → 截面 MAD 去极值与标准化 → 三因子等权合成 → 月末选前 10 → 次交易日开盘执行 → 每日现金与持仓估值 → IC、分组和绩效报告。

动量方向为 +1，波动和活跃度方向为 −1。方向和等权规则是预设假设。理论标签/IC/分组收益用于事后因子检验；账户净值另行模拟成交、费用和现金，两类结果不能混为一谈。

手续费为单边佣金 3 bps、滑点 5 bps、卖出税 5 bps 的固定教学参数。数量是复权价格下的小数单位；买入前隔夜变化不归新仓所有，已有仓位继续承担隔夜变化。受限卖出保留旧仓，买入按可用现金缩放，拒单不在次日自动重试。期末仍持仓，按收盘估值。

## 模拟实验：工程跑通不代表策略跑赢

本部分为 40 只人工股票，2020—2025 年。日历仅为工作日，包含真实市场假日；不作 A 股市场实证结论。

{sim_table}

同档费用同时作用于策略和基准。成本敏感性分别重新模拟账户，而非从无费终值机械扣除累计费用：

{cost_table}

![模拟基准和成本比较](figures/cost_comparison.png)

来源：[第 16 课指标](../runs/first_demo_20261107/lesson16_benchmark_cost/metrics.csv)、[同档相对比较](../runs/first_demo_20261107/lesson16_benchmark_cost/relative_comparison.csv)、[成本路径对照](../runs/first_demo_20261107/lesson16_benchmark_cost/cost_impact.csv)。收益差采用百分点；比值相对收益为策略净值/基准净值−1，二者分母不同。

## 分段检查：测试期领先尚不足以说明跨期稳定

{split_table}

账户跨段连续持仓，分段净值以首条日收益之前的权益为 1，保留首日损益。各段增长倍数连乘可以还原全期收益；费用可以求和；最大回撤须在完整路径上重算。

![事后分段稳定性](figures/split_stability.png)

三个区间时长不同，收益比较同时看年化、风险与曲线，回撤受观察长度影响。完整历史已经展示过，本次是事后分段检查，不能把 test 标签解释成一次新的未见样本外检验。来源：[第 17 课分段指标](../runs/first_demo_20261107/lesson17_split_stability/metrics.csv)、[边界权益](../runs/first_demo_20261107/lesson17_split_stability/boundaries.csv)、[跨段核对](../runs/first_demo_20261107/lesson17_split_stability/reconciliation.csv)。

## 真实行情：固定股票池与假设成交下的回放

{real_table}

{real_year_table}

![真实行情教学回放](figures/real_market.png)

来源：[真实策略与基准指标](../runs/lesson18_real_market/strategy_benchmark_metrics.csv)、[方法说明](../runs/lesson18_real_market/methodology.json)、[完整流水线](../runs/lesson18_real_market/experiment/report.html)。这一回放使用已查看的快照，尚不能声称新的未见测试。

快照有 {quality['rows']:,} 条价格、30 只手工固定股票及 {quality['calendar_sessions']:,} 个来源日历交易日。完整固定网格缺 {quality['full_fixed_grid_missing_rows']} 条，其中按现有 eligible 定义缺 {quality['missing_eligible_rows']} 条；该定义以首条可见行情起算，不是核实后的上市资格。2023—2025 年为 {quality['study_sessions']} 个交易日、{quality['study_price_rows']:,} 条行情，区间缺口为零。研究区间 {quality['unknown_status_rows_in_study']:,} 行历史成交状态均未知。

2020—2025 年真实运行曾在持有 600009 的 2021-06-10 缺价时停止，见[失败记录](../runs/failed_2020_2025.json)。当前沿用此前按覆盖检查冻结的 2023—2025 年教学区间，更早的缺口仍保留，未伪造估值或删除股票。来源：[质量检查](../runs/lesson18_real_market/data_quality.json)、[逐年覆盖](../runs/lesson18_real_market/yearly_coverage.csv)、[原始文件哈希核对](../runs/lesson18_real_market/source_hash_checks.csv)。

## 验收与适用范围

我在本次验证中检查了核心测试、两类输入快照、14 条主要账户路径的现金与持仓恒等式、收益连乘、费用汇总、成交晚于信号、三段收益复原以及本地文档链接。详细证据位于[校验记录](../runs/lesson19_delivery/verification.json)。原始/规范化数据及代码、配置、报告的文件哈希保存在[清单](../runs/lesson19_delivery/project_manifest.json)；清单自身不作自引用哈希。

仍待后续研究补齐的事项：历史动态股票池、退市/ST/IPO 资格、真实停复牌与开盘涨跌停状态、企业行动现金账、整手与最低佣金、容量和冲击、历史税费变化，以及新的未使用时期检验。固定 30 股存在选择与幸存者偏差。文献综述、完整实证论文和实盘验证不属于本教学交付已完成的范围。

我应能独立解释一只股票、一个因子、一个 IC、一次调仓、一次分段与一份报告。对应练习和验收题见[复现指南](06_19课复现与交付指南.md)及[答辩自查](04_答辩与自查.md)。
"""
    (root / "docs" / "07_教学项目总览.md").write_text(text, encoding="utf-8")


class LocalReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.references.append(value)


def check_local_links(root):
    references, broken = 0, []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.suffix not in {".md", ".html"}:
            continue
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".md":
            content = re.sub(r"```.*?```", "", content, flags=re.S)
            urls = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content)
        else:
            parser = LocalReferences()
            parser.feed(content)
            urls = parser.references
        for url in urls:
            url = url.strip().strip("<>")
            parsed = urlsplit(url)
            if parsed.scheme or url.startswith("#") or not parsed.path:
                continue
            references += 1
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root) or not target.exists():
                broken.append(dict(file=path.relative_to(root).as_posix(), reference=url))
    if broken:
        raise ValueError("本地链接缺失或越出交付目录：" + json.dumps(broken, ensure_ascii=False))
    return dict(checked_local_references=references, broken_local_references=0,
                note="Local target existence only; no external website availability or HTML visual-preview claim.")


def project_files(root):
    return sorted(path for path in root.rglob("*") if path.is_file()
                  and not any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in path.parts)
                  and path.suffix not in {".pyc", ".pyo", ".zip"})


def write_manifest(root, evidence_dir):
    manifest_path = evidence_dir / "project_manifest.json"
    entries = [dict(path=path.relative_to(root).as_posix(), bytes=path.stat().st_size, sha256=sha256(path))
               for path in project_files(root) if path != manifest_path]
    write_json(manifest_path, dict(format_version=1, self_hash_excluded=True,
                                   excluded=[".venv", "__pycache__", "*.pyc", "*.egg-info", ".git", "*.zip"],
                                   file_count=len(entries), files=entries))
    return manifest_path, entries


def package_project(root, manifest_path, entries):
    archive = root.parent / ARCHIVE_NAME
    temporary = archive.with_suffix(".zip.tmp")
    prefix = root.name
    print("正在生成并逐文件核对新版交付包……", flush=True)
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for entry in entries:
            bundle.write(root / entry["path"], f"{prefix}/{entry['path']}")
        bundle.write(manifest_path, f"{prefix}/{manifest_path.relative_to(root).as_posix()}")
    with zipfile.ZipFile(temporary) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("ZIP CRC 核对失败。")
        import hashlib
        for entry in entries:
            digest = hashlib.sha256()
            with bundle.open(f"{prefix}/{entry['path']}") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError(f"ZIP 文件哈希不一致：{entry['path']}")
        archive_file_count = len(bundle.infolist())
    temporary.replace(archive)
    digest = sha256(archive)
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    receipt = dict(created_at_utc=datetime.now(timezone.utc).isoformat(), archive=archive.name,
                    bytes=archive.stat().st_size, sha256=digest, archive_file_count=archive_file_count,
                    crc="passed", manifest_file_hashes="passed", virtual_environment_included=False,
                    manifest=f"{prefix}/{manifest_path.relative_to(root).as_posix()}")
    write_json(root.parent / "A股多因子研究系统_教学完整版_交付记录.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="校验并更新总览/清单，不创建 ZIP")
    parser.add_argument("--rebuild", action="store_true", help="先重跑模拟流水线和第 01-18 课")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence_dir = root / "runs" / "lesson19_delivery"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if args.rebuild:
        rebuild(root, evidence_dir)
    environment = environment_record()
    write_json(evidence_dir / "environment.json", environment)
    tests = run_tests(root, evidence_dir)
    evidence = dict(verified_at_utc=datetime.now(timezone.utc).isoformat(), tests=tests,
                    sources=source_audit(root), accounts=account_audits(root),
                    rebuild_requested_this_invocation=args.rebuild,
                    completed_rebuild=(json.loads((evidence_dir / "rebuild_completed.json").read_text(encoding="utf-8"))
                                       if (evidence_dir / "rebuild_completed.json").exists() else None),
                    scope="Teaching implementation and saved experiments; not real execution or strategy-validity proof.")
    write_json(evidence_dir / "verification.json", evidence)
    # 建立清单目标后验证文档链接，最终清单排除自身哈希以避免自引用。
    write_json(evidence_dir / "project_manifest.json", {"status": "building"})
    write_overview(root, evidence)
    evidence["local_links"] = check_local_links(root)
    write_json(evidence_dir / "verification.json", evidence)
    manifest_path, entries = write_manifest(root, evidence_dir)
    print(f"校验通过：{tests['tests_run']} 项测试，{len(evidence['accounts'])} 条账户路径，"
          f"{evidence['local_links']['checked_local_references']} 个本地引用。", flush=True)
    print("总览：", root / "docs" / "07_教学项目总览.md", flush=True)
    if not args.verify_only:
        receipt = package_project(root, manifest_path, entries)
        print(f"交付包：{root.parent / ARCHIVE_NAME}\nZIP 内文件：{receipt['archive_file_count']}；"
              f"大小：{receipt['bytes'] / 1024 ** 2:.2f} MiB；哈希与 CRC 均通过。", flush=True)
    else:
        print("仅校验模式完成；已有 ZIP 不作更新。", flush=True)


if __name__ == "__main__":
    main()
```

<!-- GENERATED_FULL_SOURCE_END -->

<!-- GENERATED_NAV_START -->

[项目首页](../../README.md) · [本步 Notebook](lesson.ipynb) · [上一步](../18_real_market_data/README.md)

<!-- GENERATED_NAV_END -->
