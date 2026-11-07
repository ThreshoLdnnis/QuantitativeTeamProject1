# QuantitativeTeamProject1

## 金融修道第二期：如何从零到一搭建 A 股多因子选股与回测系统

这份项目记录了我从基础 Python 出发，逐步搭建量化选股与回测系统的过程，包含 **第 0 步的环境准备 + 第 1—19 步完整操作流程**。每一步都有独立的 README 和可运行 Notebook，保留公式推导、代码解释、实际数值、图表与验收记录。实现中的假设和限制，以及没有跑赢基准的结果，也一并记录。

完整流程：**环境 → 行情 → 收益与回撤 → 动量 → IC 与分组 → 三因子处理 → 综合选股 → 成交与现金 → 全期回测 → 基准和成本 → 分段检查 → 真实行情回放 → 交付复现**。

## 阅读顺序

- 从 [第 0 步](lessons/00_environment/README.md)确认环境和数据位置，再按编号向后推进。
- README 提供详细讲解和学习记录，Notebook 保存实际执行输出，并提供按顺序运行的完整代码。
- [完整快照索引](publication/ASSET_INDEX.md)说明大表、原始快照和 SQLite 的位置；完整数据与结果放在 [v1.0.1 Release](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.1)。源码、全部图文教材、Notebook、图表和小型结果表可在仓库内直接浏览。

| 步骤 | 学习内容 | README | Notebook |
| --- | --- | --- | --- |
| 00 | 第 00 步：环境准备与项目路线 | [详细讲解](lessons/00_environment/README.md) | [运行与输出](lessons/00_environment/lesson.ipynb) |
| 01 | 第 01 步：读取单只股票与 13 个行情字段 | [详细讲解](lessons/01_read_prices/README.md) | [运行与输出](lessons/01_read_prices/lesson.ipynb) |
| 02 | 第 02 步：用复权收盘价计算简单日收益率 | [详细讲解](lessons/02_daily_returns/README.md) | [运行与输出](lessons/02_daily_returns/lesson.ipynb) |
| 03 | 第 03 步：累计收益与理论持有净值 | [详细讲解](lessons/03_cumulative_returns/README.md) | [运行与输出](lessons/03_cumulative_returns/lesson.ipynb) |
| 04 | 第 04 步：净值、回撤与最深下跌区间 | [详细讲解](lessons/04_nav_drawdown/README.md) | [运行与输出](lessons/04_nav_drawdown/lesson.ipynb) |
| 05 | 第 05 步：第一个滚动因子——20 日动量 | [详细讲解](lessons/05_momentum_factor/README.md) | [运行与输出](lessons/05_momentum_factor/lesson.ipynb) |
| 06 | 第 06 步：同一日期的 40 股动量排名 | [详细讲解](lessons/06_cross_section_ranking/README.md) | [运行与输出](lessons/06_cross_section_ranking/lesson.ipynb) |
| 07 | 第 07 步：原始动量与未来收益的配对 | [详细讲解](lessons/07_forward_returns_rank_ic/README.md) | [运行与输出](lessons/07_forward_returns_rank_ic/lesson.ipynb) |
| 08 | 第 08 步：从单期 IC 到月度研究记录 | [详细讲解](lessons/08_monthly_ic_icir/README.md) | [运行与输出](lessons/08_monthly_ic_icir/lesson.ipynb) |
| 09 | 第 09 步：原始动量的五分组收益检验 | [详细讲解](lessons/09_quintile_returns/README.md) | [运行与输出](lessons/09_quintile_returns/lesson.ipynb) |
| 10 | 第 10 步：波动率与相对成交量因子 | [详细讲解](lessons/10_volatility_activity/README.md) | [运行与输出](lessons/10_volatility_activity/lesson.ipynb) |
| 11 | 第 11 步：同日 MAD 截断、标准化与方向统一 | [详细讲解](lessons/11_factor_preprocessing/README.md) | [运行与输出](lessons/11_factor_preprocessing/lesson.ipynb) |
| 12 | 第 12 步：三因子等权合成与目标持仓 | [详细讲解](lessons/12_equal_weight_selection/README.md) | [运行与输出](lessons/12_equal_weight_selection/lesson.ipynb) |
| 13 | 第 13 步：从目标名单到首次成交与持仓记账 | [详细讲解](lessons/13_first_execution/README.md) | [运行与输出](lessons/13_first_execution/lesson.ipynb) |
| 14 | 第 14 步：连续估值与第二次月度调仓 | [详细讲解](lessons/14_daily_valuation_rebalance/README.md) | [运行与输出](lessons/14_daily_valuation_rebalance/lesson.ipynb) |
| 15 | 第 15 步：完整历史回测与四项绩效指标 | [详细讲解](lessons/15_full_history_performance/README.md) | [运行与输出](lessons/15_full_history_performance/lesson.ipynb) |
| 16 | 第 16 步：同池、同费率基准与成本路径对照 | [详细讲解](lessons/16_benchmark_cost_comparison/README.md) | [运行与输出](lessons/16_benchmark_cost_comparison/lesson.ipynb) |
| 17 | 第 17 步：连续账户的事后分段稳定性检查 | [详细讲解](lessons/17_split_stability/README.md) | [运行与输出](lessons/17_split_stability/lesson.ipynb) |
| 18 | 第 18 步：真实 A 股快照核对与教学回放 | [详细讲解](lessons/18_real_market_data/README.md) | [运行与输出](lessons/18_real_market_data/lesson.ipynb) |
| 19 | 第 19 步：教学项目的复现、验收与交付 | [详细讲解](lessons/19_finalize_project/README.md) | [运行与输出](lessons/19_finalize_project/lesson.ipynb) |

## 环境安装与复现

项目已在 Python 3.12 环境验证。Windows PowerShell 的完整操作如下；没有 `py` 时，可使用第 0 步记录的解释器绝对路径方法。

```powershell
git clone https://github.com/ThreshoLdnnis/QuantitativeTeamProject1.git
cd QuantitativeTeamProject1
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
.\.venv\Scripts\python.exe publication/restore_snapshot.py
.\.venv\Scripts\python.exe examples/19_finalize_project.py --verify-only
```

运行 Notebook 时，另外安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebooks.txt
.\.venv\Scripts\python.exe -m jupyter lab
```

安装后可直接打开 `lessons/NN_*/lesson.ipynb`。Notebook 会从当前目录向上定位仓库，并设置脚本路径；第 19 步 Notebook 固定使用校验模式，避免无意重复打包。

完整重跑已有输入和第 01—18 课：

```powershell
.\.venv\Scripts\python.exe examples/19_finalize_project.py --rebuild
```

## 结果与解释范围

| 实验 | 区间 | 三因子累计收益 | 同池基准累计收益 | 解释范围 |
| --- | --- | --- | --- | --- |
| 人工数据 | 2020—2025 | −3.5632% | +14.1581% | 用于验证工程与评估方法，不能作为 A 股市场结论 |
| 固定 30 股真实快照 | 2023—2025 | +27.0063% | +19.7282% | 在教学成交假设下回放已查看的样本，不能据此认定策略有效 |

模拟策略在开发和验证区间落后、测试区间领先；真实快照中 2025 年仍落后于基准。历史交易状态未知、固定幸存股票池、后复权小数单位、固定教学费用等限制均随各步记录保留。

整理结果时，我特别区分累计收益、年化、波动、回撤、收益差百分点与财富比值，并将理论标签、IC、分组检验和实际模拟账户分别解释。这里的“测试”年份已经被查看过，本次整理属于复现与事后检查。

## 程序、文档与运行证据

- [可复用程序](src/ashare_lab/)与[课程脚本](examples/)
- [固定规则](configs/)、[自动测试](tests/)、[SQL 练习](sql/worksheet.sql)
- [Notebook 执行记录](publication/notebook_validation.json)与[发布校验](publication/validation.json)
- [方法总览](docs/07_教学项目总览.md)与[历史交付记录](publication/history/previous_delivery.json)

讲解以项目实际代码和快照结果为依据；已有结果不代表实盘验证、独立掌握或未见样本外验证。动态历史股票池、可靠的历史可成交状态、企业行动现金账、整手/最低佣金/容量与冲击、独立新时期评估等仍是后续研究工作。
