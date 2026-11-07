# 第 00 步：环境准备与项目路线

<!-- SNAPSHOT_NOTE -->
## 数据准备

本页记录的是完整快照上的实际运行。从 GitHub 克隆源码后，先在仓库根目录运行 `python publication/restore_snapshot.py`，恢复同版本的 `data/` 与 `runs/`，再执行本步。[完整数据与大型结果索引](../../publication/ASSET_INDEX.md)保留全部路径和哈希；本页图表与 Notebook 已保存输出可直接阅读。


## 目标与完成标准

这次项目从数据出发，完整走到研究结论，最终成果需要包含可核对的过程和证据。开始这个项目时，我只有基础 Python 知识，量化研究还要从零学起，因此先解决三个具体问题：实际运行哪一个 Python；读取哪一份数据、采用哪一组规则；换一个环境怎样重新得到同一批主要结果。

完整实践路径是：读取行情 → 正确计算收益 → 构建因子 → 检验因子与未来收益的关系 → 形成目标组合 → 模拟订单和现金 → 评价收益与风险 → 接入真实教学数据 → 保存证据与打包。前 01—17 步主要使用人工数据，第 18 步接入已经下载的真实行情，第 19 步整理校验和交付。前几步的单股净值与后续组合回测采用不同的起点和会计规则，阅读时需要分别理解，不能直接混成一个结果。

工程验收要求代码、输入、配置、输出和版本能够对应；研究验收则进一步要求说清数据范围、时间可得性、交易假设和统计证据。模拟数据可以检验程序，不能支持“中国 A 股因子有效”这样的结论。

## 仓库结构

| 位置 | 用途 |
| --- | --- |
| `src/ashare_lab` | 核心实现：数据、因子、检验、回测、报告和命令行入口 |
| `examples/01_...py` 到 `19_...py` | 按编号展开逐步练习，观察中间表和账户核对 |
| `configs/baseline.json` | 固定人工数据实验的研究日期、窗口、方向、选股数量和成本 |
| `configs/market_teaching.json` | 固定真实教学实验的 2023—2025 年区间和分区规则 |
| `runs/first_demo_20261107/input` | 为 01—17 步提供统一的人工行情、日历、股票池与说明 |
| `data/market_teaching` | 真实快照、原始响应、成员表和取数记录，无需另行下载即可读取 |
| `runs` | 保存每次实验结果；与程序源码分开管理，重跑前保留有价值的实验记录 |
| `tests`、`sql`、`docs` | 保存关键行为测试、数据库查询练习和方法边界 |
| `lessons` | 记录每一步的目标、公式、解释、实际数值和验收 |

配置说明实验规则，源码负责执行规则，`runs` 则保留一次实验的证据。修改参数时，要保存新配置或新运行目录，使规则与结果始终能够对应。策略表现应由程序重新计算，不能通过手工修改结果 CSV 来“修正”。

## 环境准备与运行命令

在仓库根目录打开 PowerShell。这个目录应能看到 `pyproject.toml`，因为安装命令中的 `.` 指向当前目录。

先选择本机实际可用的 Python 3.12：存在 Python Launcher 时采用第一种；没有 `py` 而存在 `python3.12` 时采用第二种；其余情况使用真实安装路径。三种方式是替代关系，不需要全部执行。

```powershell
# 方式一：本机存在 Python Launcher
py -3.12 -m venv .venv
```

```powershell
# 方式二：本机存在 python3.12 命令
python3.12 -m venv .venv
```

```powershell
# 方式三：我将示例路径替换为本机实际解释器路径
& 'C:\我的Python安装目录\python.exe' -m venv .venv
```

`.venv` 是为当前项目创建的独立环境，不是源数据的一部分。迁移项目时应在本机重新创建 `.venv`，不直接复制其他机器的环境。后续命令直接指定环境中的解释器，无需先执行激活脚本，也能避免调用到系统中的其他 Python。

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
```

这条安装命令可以逐项理解：`-m` 让前面的 Python 运行一个模块；`pip` 是安装包的工具；`-r` 读取已验证的直接依赖版本；`-e` 安装当前项目的开发版本；`.` 是当前仓库；`[plots]` 增加课堂绘图所需的依赖。修改 `src` 中的普通代码以后，开发安装可以直接读取这些修改；若改变包的依赖或安装元数据，则仍需要重新安装。

各个工具承担不同任务：NumPy 处理数值数组，pandas 处理表格与时间序列，Matplotlib 生成图表，SQLite 保存可查询的数据。SQLite 接口由 Python 标准库提供，第一轮学习因此无需另搭数据库服务器。已有真实快照的读取与复现不要求安装 AKShare；只有重新下载数据时才需要可选的 `market` 依赖。

本次已有环境记录为 Python **3.12.14**、NumPy **2.3.5**、pandas **3.0.1**、Matplotlib **3.11.2**。`requirements-tested.txt` 记录的是直接依赖，不是包含所有间接依赖及系统组件的完整锁文件。复现时应以实际运行留下的环境记录核对版本；安装成功并不意味着环境完全相同。

## 固定人工数据实验

这里使用固定输出目录，因为现有 01—17 步脚本都从 `runs/first_demo_20261107/input` 读取数据。日期字符串在这里也是一个约定的目录名；它并不改变研究区间。

```powershell
.\.venv\Scripts\python.exe -m ashare_lab demo --config configs/baseline.json --out runs/first_demo_20261107 --seed 20261102
```

各参数的作用是：`demo` 生成人工数据并运行整条流水线；`--config` 指向规则文件；`--out` 指向证据目录；`--seed` 固定随机数起点。默认样本为 40 只人工股票，输入从 2019 年开始，2019 年提供正式区间之前的滚动历史，正式评价使用 2020—2025 年。相同种子用于重复当前生成规则；若生成器或依赖发生改动，仍需核对输入哈希，确认得到的是否为同一份数据。

我在原有快照中实际核对到 **73,080 行、13 列、40 个代码**；单只 `SYN001` 有 **1,827 行**，从 2019-01-01 到 2025-12-31。这里采用工作日日历，包含中国节假日，因此 2019-01-01 的人工记录不能当成真实 A 股交易证据。真实数据的日历另由供应商快照提供。

命令行依次显示五个阶段：计算历史因子与截面分数；构造完整未来标签并做时间分区；运行基准、单因子、多因子和成本对照；保存 SQLite 与复现记录；生成 HTML 报告。看到 `完成: ...report.html` 后，流水线已结束；接下来仍要打开报告和关键核对记录，检查结果是否完整。

主要产物包括 `report.html`、`research.sqlite`、`factors.csv`、`labels.csv`、`ic_summary.csv`、`metrics.csv`，以及各策略的 `daily_*.csv`、`trades_*.csv`、`orders_*.csv`、`positions_*.csv`。`manifest.json` 记录输入、代码、配置哈希和依赖版本；哈希用于发现文件变化，不能自动证明数据源没有错误。

## 测试与交付

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe examples/01_read_prices.py
```

先确认测试以 `OK` 结束，再开始逐步课程。测试覆盖的是定义过的行为，例如因子公式、未来数据扰动、下一交易日成交、受限买卖和现金核算；它们不能证明市场中的盈利能力。第 19 步再执行以下命令，对现成成果校验并更新总览：

```powershell
.\.venv\Scripts\python.exe examples/19_finalize_project.py --verify-only
```

`--verify-only` 仍会更新校验记录和总览，不是完全只读。默认不加参数会在校验后打包；`--rebuild` 会用已有模拟输入重跑主流水线和 01—18 步后再打包。需要完整复现时再选择后者，避免无目的地反复运行。

## 常见错误与修正

| 错误操作 | 为什么会错 | 修正方式 |
| --- | --- | --- |
| 使用 Windows 应用商店的 `python.exe` 别名 | 别名不等于真实 Python 安装 | 核对 `sys.executable`，再用真实解释器创建环境 |
| 在 `lessons` 子目录执行 `pip install -e .` | 当前目录没有项目安装配置 | 回到有 `pyproject.toml` 的仓库根目录 |
| 只安装核心依赖就运行绘图课 | 课堂图表还需要 Matplotlib | 安装 `.[plots]` 并核对版本 |
| 把 demo 输出到 `runs/my_demo` 后直接运行旧脚本 | 旧脚本使用固定输入目录 | 按本次约定初始化 `first_demo_20261107` |
| 看到模拟净值上涨便写真实市场结论 | 人工样本不是 A 股观测 | 仅用人工样本解释计算和会计逻辑 |
| 把 `.venv` 上传为可移植环境 | 环境含本机路径和平台信息 | 提交依赖说明和创建命令，不提交整个环境 |

## 验收记录与下一步

环境准备的验收包含三个证据：解释器路径确实位于当前 `.venv`；固定人工输入的规模与种子记录一致；主流水线结束且测试通过。已有成果中的 [模拟报告](../../runs/first_demo_20261107/report.html) 可以离线打开；[真实教学报告](../../runs/lesson18_real_market/experiment/report.html) 属于另一份明确限定范围的实验。

研究边界也需要保留：真实样本是 30 股手工固定池，历史成交状态未核实，后复权小数持仓只是收益代理，完整企业行动账和历史费用表尚未实现，已查看的测试期不能再次称为全新未见样本。下一步进入 [第 01 步](../01_read_prices/README.md)：先把一行行情读懂，而不是立即追求复杂模型。

<!-- GENERATED_FULL_SOURCE_START -->

## 完整脚本源码

本步完整实现见 [environment_check.py](../../publication/environment_check.py)。前文解释了关键代码，以下保留与脚本文件一致的完整源码。

```python
"""我的第 0 步：检查解释器、依赖和项目输入位置。"""
from pathlib import Path
import importlib.metadata
import platform
import sys

project_dir = Path(__file__).resolve().parents[1]
print("我的 Python 版本：", platform.python_version())
print("我的解释器：", sys.executable)
for dependency in ["numpy", "pandas", "matplotlib"]:
    print(f"{dependency} = {importlib.metadata.version(dependency)}")
for relative in ["pyproject.toml", "configs/baseline.json", "examples/01_read_prices.py",
                 "runs/first_demo_20261107/input/metadata.json", "data/market_teaching/metadata.json"]:
    path = project_dir / relative
    if not path.exists():
        raise FileNotFoundError(f"我需要先准备项目文件：{relative}")
    print("已找到：", relative)
```

<!-- GENERATED_FULL_SOURCE_END -->

<!-- GENERATED_NAV_START -->

[项目首页](../../README.md) · [本步 Notebook](lesson.ipynb) · [下一步](../01_read_prices/README.md)

<!-- GENERATED_NAV_END -->
