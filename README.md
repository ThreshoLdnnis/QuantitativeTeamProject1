<p align="center">
  <img src="assets/readme-cover.jpg" alt="金融修道第二期项目封面" width="100%">
</p>

<h1 align="center">QuantitativeTeamProject1</h1>

<p align="center">
  <strong>A 股多因子选股与回测</strong><br>
  金融修道 · 第二期<br>
  <sub>Python · SQLite · 因子研究 · 组合回测</sub>
</p>

<p align="center">
  <strong>简体中文</strong> · <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="#从这里开始">开始学习</a> ·
  <a href="#成员实操资料">成员实操</a> ·
  <a href="#课程路线">课程目录</a> ·
  <a href="#回测结果">回测结果</a>
</p>

这个项目从一张行情表开始，逐步做到因子研究、选股、调仓和回测。最初只有基础 Python，量化知识是沿着项目一点点补上的。这里留下了每一步的公式、代码、图表和运行结果，也记录了策略落后于基准的阶段。

全套教程包含 **环境准备 + 19 步实践**，每课都有讲解和可运行 Notebook。读完后，可以用同一份数据从空工程重新做一遍，检验自己是否真正理解了整条流程。

## 从这里开始

| 跟着教程学习 | 独立完成实操 |
| --- | --- |
| 从 [第 00 课：环境准备](lessons/00_environment/README.md) 开始，按顺序读讲解、运行 Notebook。 | 领取 [成员实操资料](member_practice/market_v1.0.0/)，先读字典与任务，再自己建库、写查询、做研究。 |
| 适合有基础 Python、刚接触量化的读者。 | 三位成员使用同一版本的输入，各自完成完整项目。 |

## 成员实操资料

实操文件集中在 **[member_practice/market_v1.0.0](member_practice/market_v1.0.0/)**。数据、规则和任务由负责人统一发放，数据库、SQL、因子、回测与报告由每个人独立完成。

本次使用固定的 **30 只 A 股教学股票**。输入历史为 2019–2025 年，正式评价区间为 2023–2025 年。行情原取数日期是 **2026-11-02**，观察截止 **2025-12-31**；这些文件沿用已有快照，没有重新取数。

| 文件 | 用途 |
| --- | --- |
| [prices.csv](member_practice/market_v1.0.0/prices.csv) | 行情表，50,927 行，每行是一只股票在一天的记录。 |
| [calendar.csv](member_practice/market_v1.0.0/calendar.csv) | 交易日历，1,699 个交易日，用来对齐窗口和执行日期。 |
| [universe.csv](member_practice/market_v1.0.0/universe.csv) | 股票池资格表，50,970 行，保留 `eligible=0` 的记录。 |
| [数据字典](member_practice/market_v1.0.0/04_数据字典.md) | 字段、类型、单位、复权、前导零和缺失值。 |
| [来源与使用说明](member_practice/market_v1.0.0/05_数据来源与使用说明.md) | 数据从哪里来、怎样使用、哪些局限需要说明。 |
| [统一参数说明](member_practice/market_v1.0.0/06_统一参数说明.md) | 因子、标准化、选股、调仓、基准和费用口径。 |
| [任务与提交要求](member_practice/market_v1.0.0/07_任务与提交要求.md) | 独立建库、Q01–Q10 练习、研究流程和提交清单。 |
| [metadata.json](member_practice/market_v1.0.0/metadata.json) | 程序可读的原始来源记录。 |
| [market_teaching.json](member_practice/market_v1.0.0/market_teaching.json) | 三人共同使用的冻结参数。 |
| [哈希核验说明](member_practice/market_v1.0.0/08_哈希核验说明.md) | 收到文件后怎样核对版本。 |
| [文件哈希清单](member_practice/market_v1.0.0/09_文件哈希清单.txt) | 11 份固定文件的 SHA-256。 |
| [校验文件.py](member_practice/market_v1.0.0/校验文件.py) | 核验程序，只使用 Python 标准库。 |
| [发放公告](member_practice/market_v1.0.0/00_发放公告.txt) | 负责人单独发给成员的版本、摘要和操作命令。 |

通过克隆仓库或下载仓库 ZIP 取得整个目录。单独保存文件时保留原名，放在同一文件夹；个人代码、SQLite、日志和结果放到其中的 `work/`。

在仓库根目录执行以下命令即可核验这套资料，Python 3.10 及以上可运行：

```powershell
cd member_practice/market_v1.0.0
python '.\校验文件.py' --expected-manifest-sha256 2bc3d368c5eb9228de256ea228a942374c6e1b9010ebe762b910fe84793482cf
```

工具应显示“通过”并正常退出。发放标识为 `QTP1-MARKET-FILES-1.0.0`，上面的摘要对应文件哈希清单本身。每次正式运行和提交前重新核验；需要修订输入时，由负责人统一发新版本。

原始文件按哈希核对，自建 SQLite 按表内内容验收。哈希只能发现文件差异，独立完成情况还要看能否从空库重建、讲清代码和解释结果。

## 运行参考项目

参考项目已在 **Python 3.12** 环境验证，直接依赖版本记录在 `requirements-tested.txt`。Windows PowerShell：

```powershell
git clone https://github.com/ThreshoLdnnis/QuantitativeTeamProject1.git
cd QuantitativeTeamProject1
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
.\.venv\Scripts\python.exe publication/restore_snapshot.py
.\.venv\Scripts\python.exe examples/19_finalize_project.py --verify-only
```

教程与 Notebook 更新至 [v1.0.1](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.1)，完整数据和计算结果沿用 [v1.0.0 固定快照](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.0)。恢复脚本核对快照哈希后提取 `data/` 与 `runs/`，保留当前源码和教材；大表、SQLite 及原始快照的位置见 [完整快照索引](publication/ASSET_INDEX.md)。成员实操的三张 CSV 已直接放在仓库中，可从实操目录开始。

<details>
<summary><strong>打开 Notebook，或完整重跑参考流程</strong></summary>

安装 Notebook 依赖并启动 Jupyter：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebooks.txt
.\.venv\Scripts\python.exe -m jupyter lab
```

按顺序打开 `lessons/NN_*/lesson.ipynb`。Notebook 会向上定位仓库并设置脚本路径。第 19 课使用校验模式，方便核对交付结果。

用已有输入重跑第 01–18 课：

```powershell
.\.venv\Scripts\python.exe examples/19_finalize_project.py --rebuild
```

没有 `py` 命令时，按 [第 00 课](lessons/00_environment/README.md) 使用解释器绝对路径。

</details>

## 课程路线

1. **00–04：读懂数据和收益。** 配好环境，读取行情，计算日收益、累计收益、净值和最大回撤。
2. **05–09：研究第一个因子。** 从 20 日动量走到截面排名、未来收益标签、IC 与五分组检验。
3. **10–17：把信号变成组合。** 处理三个因子，合成分数，记录成交与现金，比较基准、成本和分段表现。
4. **18–19：回到真实数据并交付。** 核对真实行情快照，复现结果，整理验收和运行记录。

<details>
<summary><strong>查看全部 20 课的讲解与 Notebook</strong></summary>

| 步骤 | 内容 | 讲解 | Notebook |
| --- | --- | --- | --- |
| 00 | 环境准备与项目路线 | [讲解](lessons/00_environment/README.md) | [Notebook](lessons/00_environment/lesson.ipynb) |
| 01 | 读取单只股票与 13 个行情字段 | [讲解](lessons/01_read_prices/README.md) | [Notebook](lessons/01_read_prices/lesson.ipynb) |
| 02 | 用复权收盘价计算简单日收益率 | [讲解](lessons/02_daily_returns/README.md) | [Notebook](lessons/02_daily_returns/lesson.ipynb) |
| 03 | 累计收益与理论持有净值 | [讲解](lessons/03_cumulative_returns/README.md) | [Notebook](lessons/03_cumulative_returns/lesson.ipynb) |
| 04 | 净值、回撤与最深下跌区间 | [讲解](lessons/04_nav_drawdown/README.md) | [Notebook](lessons/04_nav_drawdown/lesson.ipynb) |
| 05 | 第一个滚动因子——20 日动量 | [讲解](lessons/05_momentum_factor/README.md) | [Notebook](lessons/05_momentum_factor/lesson.ipynb) |
| 06 | 同一日期的 40 股动量排名 | [讲解](lessons/06_cross_section_ranking/README.md) | [Notebook](lessons/06_cross_section_ranking/lesson.ipynb) |
| 07 | 原始动量与未来收益的配对 | [讲解](lessons/07_forward_returns_rank_ic/README.md) | [Notebook](lessons/07_forward_returns_rank_ic/lesson.ipynb) |
| 08 | 从单期 IC 到月度研究记录 | [讲解](lessons/08_monthly_ic_icir/README.md) | [Notebook](lessons/08_monthly_ic_icir/lesson.ipynb) |
| 09 | 原始动量的五分组收益检验 | [讲解](lessons/09_quintile_returns/README.md) | [Notebook](lessons/09_quintile_returns/lesson.ipynb) |
| 10 | 波动率与相对成交量因子 | [讲解](lessons/10_volatility_activity/README.md) | [Notebook](lessons/10_volatility_activity/lesson.ipynb) |
| 11 | 同日 MAD 截断、标准化与方向统一 | [讲解](lessons/11_factor_preprocessing/README.md) | [Notebook](lessons/11_factor_preprocessing/lesson.ipynb) |
| 12 | 三因子等权合成与目标持仓 | [讲解](lessons/12_equal_weight_selection/README.md) | [Notebook](lessons/12_equal_weight_selection/lesson.ipynb) |
| 13 | 从目标名单到首次成交与持仓记账 | [讲解](lessons/13_first_execution/README.md) | [Notebook](lessons/13_first_execution/lesson.ipynb) |
| 14 | 连续估值与第二次月度调仓 | [讲解](lessons/14_daily_valuation_rebalance/README.md) | [Notebook](lessons/14_daily_valuation_rebalance/lesson.ipynb) |
| 15 | 完整历史回测与四项绩效指标 | [讲解](lessons/15_full_history_performance/README.md) | [Notebook](lessons/15_full_history_performance/lesson.ipynb) |
| 16 | 同池、同费率基准与成本路径对照 | [讲解](lessons/16_benchmark_cost_comparison/README.md) | [Notebook](lessons/16_benchmark_cost_comparison/lesson.ipynb) |
| 17 | 连续账户的事后分段稳定性检查 | [讲解](lessons/17_split_stability/README.md) | [Notebook](lessons/17_split_stability/lesson.ipynb) |
| 18 | 真实 A 股快照核对与教学回放 | [讲解](lessons/18_real_market_data/README.md) | [Notebook](lessons/18_real_market_data/lesson.ipynb) |
| 19 | 教学项目的复现、验收与交付 | [讲解](lessons/19_finalize_project/README.md) | [Notebook](lessons/19_finalize_project/lesson.ipynb) |

</details>

## 回测结果

以下为固定输入和教学成交假设下的历史结果：

| 实验 | 评价区间 | 三因子累计收益 | 同池基准累计收益 |
| --- | --- | ---: | ---: |
| 人工数据 | 2020–2025 | −3.5632% | +14.1581% |
| 固定 30 股真实快照 | 2023–2025 | +27.0063% | +19.7282% |

人工数据用于检查工程和评估方法。真实快照的全期结果领先于同池基准，但 2025 年仍然落后。分段结果、成本路径和交易记录都保留在教程中，方便追问收益究竟来自哪里。

解读这些数字时，需要一起考虑几个前提：

- 股票池固定选取，存在样本选择和幸存者偏差，不能代表完整 A 股市场。
- 历史可成交状态未知；复权价格、可分割持仓单位和固定费用属于教学执行假设。
- “测试”年份已经看过，这里是历史复现和事后检查，不能作为新的未见样本外验证。

动态历史股票池、可靠的交易状态、公司行为现金账、整手与最低佣金、容量和冲击，以及独立新时期评估，都是后续需要补上的研究工作。

## 仓库导航

- **学习材料：**[逐课教程](lessons/)、[课程脚本](examples/)、[方法总览](docs/07_教学项目总览.md)。
- **成员实操：**[统一输入与任务](member_practice/market_v1.0.0/)。
- **程序与规则：**[核心模块](src/ashare_lab/)、[配置](configs/)、[自动测试](tests/)、[SQL 练习](sql/worksheet.sql)。
- **复现记录：**[Notebook 执行记录](publication/notebook_validation.json)、[发布校验](publication/validation.json)、[历史交付记录](publication/history/previous_delivery.json)。

<p align="center"><a href="#quantitativeteamproject1">回到顶部</a> · <a href="README.en.md">Read in English</a></p>
