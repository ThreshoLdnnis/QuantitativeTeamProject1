# QuantitativeTeamProject1

## 我从零到一搭建 A 股多因子选股与回测系统

我把这次项目逐步整理成了 **第 0 步的环境准备 + 第 1—19 步完整操作流程**。每一步都有独立的 README、完整可运行 Notebook、公式、代码解释、实际数值与验收记录。我保留推导过程和实现边界，也保留没有跑赢基准的结果。

我的完整流程是：**环境 → 行情 → 收益与回撤 → 动量 → IC 与分组 → 三因子处理 → 综合选股 → 成交与现金 → 全期回测 → 基准和成本 → 分段检查 → 真实行情回放 → 交付复现**。

## 怎样阅读这份项目

- 先从 [第 0 步](lessons/00_environment/README.md)确认环境和数据位置，再按编号向后推进。
- README 是我的详细操作记录，Notebook 保存实际执行输出，并提供按顺序运行的完整代码。
- [完整快照索引](publication/ASSET_INDEX.md)说明大表、原始快照和 SQLite 的位置；我把完整数据与结果放在 [v1.0.0 Release](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.0)。源码、全部图文教材、Notebook、图表和小型结果表在仓库内直接浏览。

| 步骤 | 我的学习内容 | README | Notebook |
| --- | --- | --- | --- |
| 00 | 第 00 步：先建立可复现的环境与项目地图 | [我的记录](lessons/00_environment/README.md) | [运行与输出](lessons/00_environment/lesson.ipynb) |
| 01 | 第 01 步：读取一只股票，逐项解释 13 个行情字段 | [我的记录](lessons/01_read_prices/README.md) | [运行与输出](lessons/01_read_prices/lesson.ipynb) |
| 02 | 第 02 步：从复权收盘价计算简单日收益率 | [我的记录](lessons/02_daily_returns/README.md) | [运行与输出](lessons/02_daily_returns/lesson.ipynb) |
| 03 | 第 03 步：用连乘构造累计收益与理论持有净值 | [我的记录](lessons/03_cumulative_returns/README.md) | [运行与输出](lessons/03_cumulative_returns/lesson.ipynb) |
| 04 | 第 04 步：绘制净值与回撤，定位一次最深下跌 | [我的记录](lessons/04_nav_drawdown/README.md) | [运行与输出](lessons/04_nav_drawdown/lesson.ipynb) |
| 05 | 第 05 步：构建第一个滚动因子——20 日动量 | [我的记录](lessons/05_momentum_factor/README.md) | [运行与输出](lessons/05_momentum_factor/lesson.ipynb) |
| 06 | 第 06 步：在同一日期比较 40 只股票的动量 | [我的记录](lessons/06_cross_section_ranking/README.md) | [运行与输出](lessons/06_cross_section_ranking/lesson.ipynb) |
| 07 | 第 07 步：我怎样把原始动量与未来收益正确配对 | [我的记录](lessons/07_forward_returns_rank_ic/README.md) | [运行与输出](lessons/07_forward_returns_rank_ic/lesson.ipynb) |
| 08 | 第 08 步：我怎样把单期 IC 扩展成月度研究记录 | [我的记录](lessons/08_monthly_ic_icir/README.md) | [运行与输出](lessons/08_monthly_ic_icir/lesson.ipynb) |
| 09 | 第 09 步：我怎样用五分组观察原始动量与未来收益 | [我的记录](lessons/09_quintile_returns/README.md) | [运行与输出](lessons/09_quintile_returns/lesson.ipynb) |
| 10 | 第 10 步：我怎样补齐波动率和相对成交量两个原始因子 | [我的记录](lessons/10_volatility_activity/README.md) | [运行与输出](lessons/10_volatility_activity/lesson.ipynb) |
| 11 | 第 11 步：我怎样做同日 MAD 截断、标准化和方向统一 | [我的记录](lessons/11_factor_preprocessing/README.md) | [运行与输出](lessons/11_factor_preprocessing/lesson.ipynb) |
| 12 | 第 12 步：我怎样合成三个因子并形成第一张目标持仓表 | [我的记录](lessons/12_equal_weight_selection/README.md) | [运行与输出](lessons/12_equal_weight_selection/lesson.ipynb) |
| 13 | 第 13 步：把目标名单变成首次成交与持仓账 | [我的记录](lessons/13_first_execution/README.md) | [运行与输出](lessons/13_first_execution/lesson.ipynb) |
| 14 | 第 14 步：让持仓连续存在，并完成第二次月度调仓 | [我的记录](lessons/14_daily_valuation_rebalance/README.md) | [运行与输出](lessons/14_daily_valuation_rebalance/lesson.ipynb) |
| 15 | 第 15 步：把连续账户扩展到完整历史，并亲自定义四项绩效 | [我的记录](lessons/15_full_history_performance/README.md) | [运行与输出](lessons/15_full_history_performance/lesson.ipynb) |
| 16 | 第 16 步：用同池、同费率的基准比较策略，并重跑成本路径 | [我的记录](lessons/16_benchmark_cost_comparison/README.md) | [运行与输出](lessons/16_benchmark_cost_comparison/lesson.ipynb) |
| 17 | 第 17 步：保留连续账户的边界收益，做事后分段稳定性检查 | [我的记录](lessons/17_split_stability/README.md) | [运行与输出](lessons/17_split_stability/lesson.ipynb) |
| 18 | 第 18 步：核对真实 A 股快照，并在明确假设下复现教学回放 | [我的记录](lessons/18_real_market_data/README.md) | [运行与输出](lessons/18_real_market_data/lesson.ipynb) |
| 19 | 第 19 步：教学过程的可复现、可核对的交付 | [我的记录](lessons/19_finalize_project/README.md) | [运行与输出](lessons/19_finalize_project/lesson.ipynb) |

## 我怎样复现

我在 Python 3.12 环境验证这份项目。Windows PowerShell 的一条完整路径如下；没有 `py` 时，我在第 0 步记录了真实解释器绝对路径的替代方法。

```powershell
git clone https://github.com/ThreshoLdnnis/QuantitativeTeamProject1.git
cd QuantitativeTeamProject1
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
.\.venv\Scripts\python.exe publication/restore_snapshot.py
.\.venv\Scripts\python.exe examples/19_finalize_project.py --verify-only
```

我运行 Notebook 时另外安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebooks.txt
.\.venv\Scripts\python.exe -m jupyter lab
```

我可以直接打开 `lessons/NN_*/lesson.ipynb`。Notebook 会从当前目录向上定位仓库，并设置脚本路径；第 19 步 Notebook 固定使用校验模式，避免无意重复打包。

完整重跑已有输入和第 01—18 课：

```powershell
.\.venv\Scripts\python.exe examples/19_finalize_project.py --rebuild
```

## 怎样理解结果

| 实验 | 区间 | 三因子累计收益 | 同池基准累计收益 | 我的解释范围 |
| --- | --- | --- | --- | --- |
| 人工数据 | 2020—2025 | −3.5632% | +14.1581% | 我验证工程与评估方法，不把它作为 A 股市场结论 |
| 固定 30 股真实快照 | 2023—2025 | +27.0063% | +19.7282% | 我在教学成交假设下回放已查看的样本，不能据此认定策略有效 |

我的模拟策略在开发和验证区间落后、测试区间领先；真实快照中 2025 年仍落后于基准。历史交易状态未知、固定幸存股票池、后复权小数单位、固定教学费用等限制均随各步记录保留。

我把累计收益、年化、波动、回撤、收益差百分点与财富比值分开计算；我把理论标签/IC/分组检验与实际模拟账户分开解释。这里的“测试”年份已经被查看过，本次整理属于复现与事后检查。

## 保留的工程与证据

- [可复用程序](src/ashare_lab/)与[课程脚本](examples/)
- [固定规则](configs/)、[自动测试](tests/)、[SQL 练习](sql/worksheet.sql)
- [Notebook 执行记录](publication/notebook_validation.json)与[发布校验](publication/validation.json)
- [方法总览](docs/07_教学项目总览.md)与[历史交付记录](publication/history/previous_delivery.json)

我的讲解以项目实际代码和快照结果为依据，不虚构实盘、独立掌握或未见样本外验证。动态历史股票池、可靠的历史可成交状态、企业行动现金账、整手/最低佣金/容量与冲击、独立新时期评估等仍是后续研究工作。
