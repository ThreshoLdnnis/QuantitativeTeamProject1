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
  <a href="#回测结果">回测结果</a> ·
  <a href="#成果与交付复盘">成果复盘</a>
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

<!-- LESSON_TABLE -->

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

## 成果与交付复盘

**复盘日期：2026-11-27** · 对照版本：[3dad645](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/tree/3dad64551edc456b9e1a2251c2d807260b24d505)

这一期已经跑通了从数据整理、因子检验到交易记账和结果交付的完整流程。目前能够证明的是：这套研究与回测原型可以在固定输入下复现，关键计算和时序处理有记录可查。现有样本还不足以证明稳定 Alpha，真实可成交性也没有得到验证。

这次复盘把已经完成的工作、实际结果和下一版要补的证据分开记录。增加因子是否有用，需要通过对照检验回答；收益曲线更好看，本身不能替代研究验证。

### 已完成的成果与交付

- **数据与存储：** 整理 30 只 A 股 2019–2025 年的 50,927 条行情、1,699 个交易日和 50,970 条股票池记录，保留数据来源、缺口、类型约定与版本摘要，并提供 SQLite 导入和查询流程。
- **因子研究：** 实现 20 日动量、20 日波动率、5/20 相对成交量，完成 MAD 去极值、截面标准化、方向处理、等权合成、月度 IC、ICIR 和五分组检验。
- **组合回测：** 实现月末收盘形成信号、下一交易日开盘模拟执行，记录订单、成交、现金、持仓、费用和净值，并提供同池基准、成本情景及分区结果。
- **学习与复现材料：** 交付 20 课讲解、20 本 Notebook、图表和执行记录；提供中英双语首页及 13 份成员实操发放文件，便于从同一输入独立重建。

本轮复核重新运行了现有 **35 项单元测试，全部通过**；从逐日收益独立复算了 **28 行绩效指标**，并由保存的因子分数与未来收益标签重新计算 **120 个 IC 系数**，结果与原输出一致。这些检查覆盖计算与已测试的行为，不等于证明数据无偏或策略可以实盘执行。

复核方法、输入指纹和数值记录见 [复盘证据](publication/retrospective_20261127/review_evidence.json)。现有测试在 [tests/](tests/)，此前 Notebook 执行记录见 [notebook_validation.json](publication/notebook_validation.json)；本轮没有重新执行全部 Notebook。

### 真实样本的实际表现

下表使用 **2023–2025 年、727 个交易日、1 倍教学成本**。年化按 252 个交易日计算，Sharpe 的无风险利率假设为 0。原指标保存在 [metrics.csv](runs/lesson18_real_market/experiment/metrics.csv)。

| 指标 | 三因子合成 | 同池等权基准 |
| --- | ---: | ---: |
| 全期累计收益 | 27.01% | 19.73% |
| 年化收益 | 8.64% | 6.44% |
| 年化波动率 | 11.74% | 12.30% |
| Sharpe | 0.76 | 0.57 |
| 最大回撤 | −14.17% | −13.59% |
| 2025 年累计收益 | 3.36% | 8.04% |

全期收益差为 **+7.28 个百分点**；按 `(1+策略收益)/(1+基准收益)-1` 计算的累计财富比相对收益为 **+6.08%**。这两个指标含义不同，都不能写成年化 Alpha。

全期领先并没有在各年稳定延续：2025 年三因子落后基准 **4.68 个百分点**。同时，低波动单因子全期累计收益为 **43.52%**、Sharpe 约 **1.28**，优于三因子合成。当前结果没有证明加入动量和活跃度后带来了增量价值，也不能只根据这一批结果选出最赚钱的方案，再把它当作新的样本外发现。

### 因子证据有多强

剔除跨分区标签并要求完整持有期后，月度 IC 实际只有 **30 期，每年 10 期**；每期 30 只股票，五分组后每组 6 只。5 万多条日行情不是 5 万多个独立的因子检验样本。

合成因子的全期平均 IC 约 **0.0748**，未年化 ICIR 约 **0.3552**。这说明样本内存在正向排序关系，但较短的时间序列、年度变化和已查看的结果限制了结论强度。五组平均理论收益也没有呈现稳定的单调递增关系；这需要继续解释，不能直接归为代码错误或当作稳定有效性的证明。

行业、市值和市场 Beta 暴露尚未得到控制。当前同池基准有助于比较选股结果，但不足以把收益差认定为独立 Alpha。

### 成本比较的补充核对

原流水线仅为三因子重跑 0 倍、2 倍成本，原 `metrics.csv` 的这些情景统一对照 1 倍成本基准。它可以理解为“策略成本变化、参考基准固定”，但不能称为各情景的同费率比较；1 倍成本主基线不受影响。

本轮保留原策略路径，补跑相同成本倍数的基准，得到以下对照。三类成本——佣金、滑点、卖出税费——一起缩放，所有收益均为全期累计值。

| 成本倍数 | 三因子累计收益 | 同成本基准累计收益 | 累计财富比相对收益 |
| --- | ---: | ---: | ---: |
| 0 | 32.56% | 19.98% | 10.49% |
| 1 | 27.01% | 19.73% | 6.08% |
| 2 | 21.69% | 19.48% | 1.85% |

完整精度见 [同成本比较 CSV](publication/retrospective_20261127/cost_comparison_corrected.csv)。补算使用原输入、原因子和原回测引擎，原始数据、配置及历史 `metrics.csv` 均保留。补充表已经完成；把同成本基准纳入自动流水线仍是下一版工作。

成本加倍后，相对收益降至约 1.85%，说明这份样本中的优势对成本较敏感。固定教学费用也不是历史真实费率表，例如证券交易印花税自 [2023 年 8 月 28 日起减半](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html)，历史费用模型需要按生效日期处理。

### 目前仍然存在的限制

1. **历史股票池尚未还原。** 30 只固定股票可能带来样本选择和幸存者偏差；当前资格标记不等于历史 ST、上市天数、退市及可投资资格的完整核验。
2. **真实交易状态未知。** 全部真实行情的 `status_known=0`。显式允许未知状态模拟执行，是教学假设；它不能补充历史成交证据。复权执行价、小数份额、整手、公司行为现金账与容量约束也需要进一步处理。
3. **缺价与持仓估值仍需完善。** 历史数据包含缺口，现有回测会在持仓缺少有效估值时停止。行业版需要区分停牌、上市状态与行情故障，再制定估值规则；输入历史覆盖 2019–2025 不代表已经完成七年真实回测。
4. **没有新的未见样本外证明。** 2025 年已被查看。后续若据此修改窗口、方向或权重，需要新的验证证据；多次调整后继续引用同一年，会低估事后选择的影响。

关于预先约定研究流程和防止回测过拟合，可参阅 Arnott、Harvey 与 Markowitz 的 [A Backtesting Protocol in the Era of Machine Learning](https://people.duke.edu/~charvey/Research/Published_Papers/SSRN-id3275654.pdf)。

### 下一版的工作顺序

以下是待完成的研究计划，不计入本期已交付成果。

| 顺序 | 工作 | 验收时应拿出的证据 |
| --- | --- | --- |
| 1 | 补齐历史股票池、状态和缺失原因 | 可追溯的数据来源、进入与退出记录、逐期资格及质量报告 |
| 2 | 冻结假设、参数范围和验证方案 | 研究协议、完整实验登记，包括失败方案 |
| 3 | 做单因子、合成和逐项剔除因子的对照 | 同成本增量检验、行业／市值等风险暴露分析及不确定性说明 |
| 4 | 改善成交、费用和容量模型 | 历史费率、公司行为与现金核账、约束场景、自动同成本基准 |
| 5 | 用新证据验证并形成报告 | 可重复运行的研究报告、独立验证或前瞻纸上跟踪记录 |

下一轮研究问题是：**在历史时点股票池、风险暴露控制和合理成本下，动量与活跃度能否改善低波动策略？** 目标是得到可复现、能解释的结论，是否改善绩效由验证结果决定。现阶段适合把这份成果表述为个人多因子研究与回测项目；稳定 Alpha、机构实盘能力和消除幸存者偏差，都还没有相应证据支撑。

<p align="center"><a href="#quantitativeteamproject1">回到顶部</a> · <a href="README.en.md">Read in English</a></p>
