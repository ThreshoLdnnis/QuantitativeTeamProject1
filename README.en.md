<p align="center">
  <img src="assets/readme-cover.jpg" alt="Project cover: Earth seen from above" width="100%">
</p>

<h1 align="center">QuantitativeTeamProject1</h1>

<p align="center">
  <strong>A-share Multi-Factor Stock Selection and Backtesting</strong><br>
  Learning Quantitative Finance · Project 2<br>
  <sub>Python · SQLite · Factor research · Portfolio backtesting</sub>
</p>

<p align="center">
  <a href="README.md">简体中文</a> · <strong>English</strong>
</p>

<p align="center">
  <a href="#start-here">Start here</a> ·
  <a href="#member-practice">Member practice</a> ·
  <a href="#lessons">Lessons</a> ·
  <a href="#backtest-results">Results</a>
</p>

This project began with a price table and grew into a workflow for studying factors, selecting stocks, rebalancing, and evaluating a portfolio. I started with basic Python and learned the quantitative finance concepts along the way. The repository keeps the formulas, code, plots, and execution records, including the periods when the strategy fell behind its benchmark.

There is **one environment lesson followed by 19 practical steps**, each with notes and an executable notebook. After working through them, members can rebuild the project from an empty directory using the same inputs. The detailed lessons, notebooks, and assignment documents are written in Chinese; this page provides an English guide to the repository.

## Start here

| Follow the lessons | Rebuild the project independently |
| --- | --- |
| Begin with [Lesson 00: Environment setup](lessons/00_environment/README.md), then read the notes and run each notebook in order. | Use the [member practice materials](member_practice/market_v1.0.0/). Read the dictionary and assignment, build your own database, and write the research code. |
| Intended for readers with basic Python who are new to quantitative finance. | All three members use the same input version and each complete the whole project. |

## Member practice

All practice files are in **[member_practice/market_v1.0.0](member_practice/market_v1.0.0/)**. The team leader supplies the common inputs, rules, and assignment. Each member builds their own SQLite database, SQL queries, factors, backtest, and report.

The dataset is a fixed teaching pool of **30 A-share stocks**. Input history covers 2019–2025; the formal evaluation period is 2023–2025. The market data were retrieved on **November 2, 2026**, with observations ending **December 31, 2025**. These files preserve the existing snapshot; they have not been downloaded again.

| File | Purpose |
| --- | --- |
| [prices.csv](member_practice/market_v1.0.0/prices.csv) | 50,927 daily price records, one stock and date per row. |
| [calendar.csv](member_practice/market_v1.0.0/calendar.csv) | 1,699 trading dates for aligning windows and execution dates. |
| [universe.csv](member_practice/market_v1.0.0/universe.csv) | 50,970 stock-universe records, including rows with `eligible=0`. |
| [Data dictionary](member_practice/market_v1.0.0/04_数据字典.md) | Fields, types, units, adjusted prices, leading zeros, and missing values. |
| [Sources and usage](member_practice/market_v1.0.0/05_数据来源与使用说明.md) | Data provenance, usage instructions, and sample limitations. |
| [Common parameters](member_practice/market_v1.0.0/06_统一参数说明.md) | Factor definitions, normalization, selection, rebalancing, benchmark, and costs. |
| [Assignment and submissions](member_practice/market_v1.0.0/07_任务与提交要求.md) | Database work, Q01–Q10, the research workflow, and deliverables. |
| [metadata.json](member_practice/market_v1.0.0/metadata.json) | Original source metadata for programs and provenance checks. |
| [market_teaching.json](member_practice/market_v1.0.0/market_teaching.json) | The frozen parameters shared by all members. |
| [Hash verification guide](member_practice/market_v1.0.0/08_哈希核验说明.md) | How to check that the received files match the release. |
| [File hash manifest](member_practice/market_v1.0.0/09_文件哈希清单.txt) | SHA-256 digests for 11 fixed files. |
| [校验文件.py](member_practice/market_v1.0.0/校验文件.py) | Verification script using only the Python standard library. |
| [Release notice](member_practice/market_v1.0.0/00_发放公告.txt) | Version, trusted digest, and commands for the leader to send separately. |

Clone the repository or download its ZIP to get the full directory. If saving files individually, keep their names and place them together. Store personal code, SQLite files, logs, and results in a `work/` directory inside it.

From the repository root, verify the materials with Python 3.10 or later:

```powershell
cd member_practice/market_v1.0.0
python '.\校验文件.py' --expected-manifest-sha256 2bc3d368c5eb9228de256ea228a942374c6e1b9010ebe762b910fe84793482cf
```

The script should report `通过` (“passed”) and exit successfully. The release ID is `QTP1-MARKET-FILES-1.0.0`; the digest above identifies the hash manifest itself. Recheck before running experiments or submitting work. The leader issues a new version whenever the shared inputs need revision.

Source files are checked by hash; student-built SQLite databases are checked by their table contents. Hashes detect file differences. Independent work still needs to be assessed through a clean rebuild, code explanations, and discussion of the results.

## Run the reference project

The reference project has been tested with **Python 3.12**. Tested direct dependency versions are recorded in `requirements-tested.txt`. On Windows PowerShell:

```powershell
git clone https://github.com/ThreshoLdnnis/QuantitativeTeamProject1.git
cd QuantitativeTeamProject1
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
.\.venv\Scripts\python.exe publication/restore_snapshot.py
.\.venv\Scripts\python.exe examples/19_finalize_project.py --verify-only
```

The lessons and notebooks are at [v1.0.1](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.1). Full data and computed outputs use the [v1.0.0 snapshot](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.0). The restoration script checks the archive hash and restores `data/` and `runs/`, preserving current source code and teaching notes. See the [snapshot index](publication/ASSET_INDEX.md) for large tables, SQLite databases, and raw source files. The three CSVs for member practice are already included in the repository.

<details>
<summary><strong>Open the notebooks or rerun the reference workflow</strong></summary>

Install the notebook dependencies and start Jupyter:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebooks.txt
.\.venv\Scripts\python.exe -m jupyter lab
```

Open `lessons/NN_*/lesson.ipynb` in order. The notebooks locate the repository and configure the script path. Lesson 19 uses verification mode to check the delivered results.

Rerun Lessons 01–18 using the existing inputs:

```powershell
.\.venv\Scripts\python.exe examples/19_finalize_project.py --rebuild
```

If the `py` launcher is unavailable, follow [Lesson 00](lessons/00_environment/README.md) using the interpreter's absolute path.

</details>

## Lessons

1. **00–04: Prices and returns.** Set up the environment, read market data, and calculate daily returns, cumulative returns, NAV, and maximum drawdown.
2. **05–09: The first factor.** Study 20-day momentum, cross-sectional rankings, forward-return labels, IC, and quintile returns.
3. **10–17: From signals to a portfolio.** Process and combine three factors, account for trades and cash, then compare the benchmark, costs, and period results.
4. **18–19: Market data and delivery.** Check the real-data snapshot, replay the results, and prepare the reproducibility records.

<details>
<summary><strong>All 20 lessons and notebooks</strong></summary>

| Step | Topic | Notes | Notebook |
| --- | --- | --- | --- |
| 00 | Environment setup | [Notes](lessons/00_environment/README.md) | [Notebook](lessons/00_environment/lesson.ipynb) |
| 01 | Read price data and its 13 fields | [Notes](lessons/01_read_prices/README.md) | [Notebook](lessons/01_read_prices/lesson.ipynb) |
| 02 | Daily returns from adjusted prices | [Notes](lessons/02_daily_returns/README.md) | [Notebook](lessons/02_daily_returns/lesson.ipynb) |
| 03 | Cumulative returns and buy-and-hold NAV | [Notes](lessons/03_cumulative_returns/README.md) | [Notebook](lessons/03_cumulative_returns/lesson.ipynb) |
| 04 | NAV and maximum drawdown | [Notes](lessons/04_nav_drawdown/README.md) | [Notebook](lessons/04_nav_drawdown/lesson.ipynb) |
| 05 | 20-day momentum | [Notes](lessons/05_momentum_factor/README.md) | [Notebook](lessons/05_momentum_factor/lesson.ipynb) |
| 06 | Cross-sectional momentum rankings | [Notes](lessons/06_cross_section_ranking/README.md) | [Notebook](lessons/06_cross_section_ranking/lesson.ipynb) |
| 07 | Momentum and forward returns | [Notes](lessons/07_forward_returns_rank_ic/README.md) | [Notebook](lessons/07_forward_returns_rank_ic/lesson.ipynb) |
| 08 | Monthly IC and ICIR | [Notes](lessons/08_monthly_ic_icir/README.md) | [Notebook](lessons/08_monthly_ic_icir/lesson.ipynb) |
| 09 | Momentum quintile returns | [Notes](lessons/09_quintile_returns/README.md) | [Notebook](lessons/09_quintile_returns/lesson.ipynb) |
| 10 | Volatility and relative volume | [Notes](lessons/10_volatility_activity/README.md) | [Notebook](lessons/10_volatility_activity/lesson.ipynb) |
| 11 | MAD clipping, standardization, and factor direction | [Notes](lessons/11_factor_preprocessing/README.md) | [Notebook](lessons/11_factor_preprocessing/lesson.ipynb) |
| 12 | Equal-weight factor scores and stock selection | [Notes](lessons/12_equal_weight_selection/README.md) | [Notebook](lessons/12_equal_weight_selection/lesson.ipynb) |
| 13 | First trades and portfolio accounting | [Notes](lessons/13_first_execution/README.md) | [Notebook](lessons/13_first_execution/lesson.ipynb) |
| 14 | Daily valuation and the next rebalance | [Notes](lessons/14_daily_valuation_rebalance/README.md) | [Notebook](lessons/14_daily_valuation_rebalance/lesson.ipynb) |
| 15 | Full-period backtest and performance metrics | [Notes](lessons/15_full_history_performance/README.md) | [Notebook](lessons/15_full_history_performance/lesson.ipynb) |
| 16 | Benchmark and trading-cost comparisons | [Notes](lessons/16_benchmark_cost_comparison/README.md) | [Notebook](lessons/16_benchmark_cost_comparison/lesson.ipynb) |
| 17 | Period-by-period stability checks | [Notes](lessons/17_split_stability/README.md) | [Notebook](lessons/17_split_stability/lesson.ipynb) |
| 18 | Real-market snapshot and historical replay | [Notes](lessons/18_real_market_data/README.md) | [Notebook](lessons/18_real_market_data/lesson.ipynb) |
| 19 | Reproduction, validation, and delivery | [Notes](lessons/19_finalize_project/README.md) | [Notebook](lessons/19_finalize_project/lesson.ipynb) |

</details>

## Backtest results

These historical results use the fixed inputs and teaching execution assumptions:

| Experiment | Evaluation period | Three-factor cumulative return | Pool benchmark cumulative return |
| --- | --- | ---: | ---: |
| Synthetic data | 2020–2025 | −3.5632% | +14.1581% |
| Fixed 30-stock market snapshot | 2023–2025 | +27.0063% | +19.7282% |

The synthetic dataset is used to check the implementation and evaluation methods. The real-data replay finished ahead of the pool benchmark over the full period, but fell behind in 2025. The lessons retain period results, cost comparisons, and trading records so the sources of the return can be examined.

The figures need to be read alongside their assumptions:

- The fixed stock pool has selection and survivorship bias and does not represent the full A-share market.
- Historical tradability is unverified. Adjusted execution prices, fractional units, and fixed costs are teaching assumptions.
- The years labelled “test” have already been viewed. This is a historical replay and a retrospective check, not a new evaluation on unseen data.

Further work includes historical universe membership, reliable trading-status data, corporate-action cash accounting, trading lots and minimum commissions, capacity and market impact, and evaluation on a new period.

## Repository guide

- **Learning materials:** [lessons](lessons/), [lesson scripts](examples/), and the [method overview](docs/07_教学项目总览.md).
- **Member practice:** [shared inputs and assignment](member_practice/market_v1.0.0/).
- **Implementation and rules:** [core modules](src/ashare_lab/), [configuration](configs/), [tests](tests/), and [SQL exercises](sql/worksheet.sql).
- **Reproduction records:** [notebook execution](publication/notebook_validation.json), [publication validation](publication/validation.json), and the [previous delivery record](publication/history/previous_delivery.json).

<p align="center"><a href="#quantitativeteamproject1">Back to top</a> · <a href="README.md">阅读中文版</a></p>
