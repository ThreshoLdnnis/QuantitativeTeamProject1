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
  <a href="#backtest-results">Results</a> ·
  <a href="#project-retrospective">Retrospective</a>
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

<!-- LESSON_TABLE -->

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

## Project retrospective

**Review date: November 27, 2026** · Baseline: [3dad645](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/tree/3dad64551edc456b9e1a2251c2d807260b24d505)

This phase completed the workflow from data preparation and factor testing to portfolio accounting and delivery. The evidence supports a research and backtesting prototype that reproduces its calculations under fixed inputs. It does not yet establish persistent alpha or realistic historical execution.

The review separates completed work, observed results, and the evidence still needed. Whether another factor adds useful information is an empirical question; a better-looking equity curve cannot answer it on its own.

### Completed work and deliverables

- **Data and storage:** 50,927 daily records for 30 A-share stocks over 2019–2025, 1,699 trading dates, and 50,970 universe records, with provenance, gaps, type conventions, hashes, and a SQLite import and query workflow.
- **Factor research:** 20-day momentum, 20-day volatility, and 5/20 relative volume; MAD clipping, cross-sectional standardization, direction adjustment, equal-weight combination, monthly IC, ICIR, and quintile analysis.
- **Portfolio backtesting:** month-end closing signals and simulated execution at the next trading day's open, with orders, fills, cash, holdings, costs, and NAV recorded; a pool benchmark, cost scenarios, and period comparisons.
- **Learning and reproduction:** 20 lesson notes, 20 notebooks, plots and execution records, a bilingual homepage, and 13 member distribution files for independent reconstruction from shared inputs.

The review reran the existing **35 unit tests, all passing**. It independently recomputed **28 performance rows** from daily returns and **120 IC coefficients** from saved factor scores and forward-return labels; the values agree with the saved outputs. These checks address calculations and tested behavior, not source-data bias or live execution feasibility.

Methods, input fingerprints, and numerical records are in the [review evidence](publication/retrospective_20261127/review_evidence.json). Tests are in [tests/](tests/); earlier notebook execution is recorded in [notebook_validation.json](publication/notebook_validation.json). The full notebook collection was not rerun in this review.

### Observed performance on the market snapshot

The table uses **2023–2025, 727 trading sessions, and the 1× teaching cost scenario**. Annualization assumes 252 sessions; the Sharpe calculation assumes a zero risk-free rate. The original figures remain in [metrics.csv](runs/lesson18_real_market/experiment/metrics.csv).

| Metric | Three-factor portfolio | Equal-weight pool benchmark |
| --- | ---: | ---: |
| Full-period cumulative return | 27.01% | 19.73% |
| Annualized return | 8.64% | 6.44% |
| Annualized volatility | 11.74% | 12.30% |
| Sharpe ratio | 0.76 | 0.57 |
| Maximum drawdown | −14.17% | −13.59% |
| 2025 cumulative return | 3.36% | 8.04% |

The full-period return difference is **+7.28 percentage points**. The cumulative relative wealth return, `(1 + strategy return) / (1 + benchmark return) - 1`, is **+6.08%**. These are different measures; neither is annualized alpha.

The full-period lead did not persist across all years. In 2025 the three-factor portfolio lagged by **4.68 percentage points**. The low-volatility strategy also produced a higher full-period cumulative return, **43.52%**, and a Sharpe ratio of about **1.28**. The present results do not show that adding momentum and activity created incremental value. Selecting the best performer after seeing these results would not constitute a new out-of-sample finding.

### Strength of the factor evidence

After removing labels that cross evaluation-period boundaries and requiring complete holding periods, there are **30 monthly IC observations, 10 per year**. Each cross section contains 30 stocks, leaving 6 per quintile. More than 50,000 daily price rows are not 50,000 independent factor tests.

The composite's full-period mean IC is about **0.0748**, with a **non-annualized ICIR of 0.3552**. This indicates a positive ranking relationship within the sample, but the short series, variation across years, and already-viewed results limit the claim. Average theoretical returns across the five groups are not consistently monotonic. That pattern needs explanation; it is neither automatically a coding error nor evidence of a stable factor.

Industry, market-capitalization, and market-beta exposures have not been controlled. The pool benchmark is useful for comparing stock selection, but its return difference is insufficient to establish independent alpha.

### Additional cost comparison

The original pipeline reruns only the three-factor portfolio at 0× and 2× costs. Its `relative_return` values for those scenarios use the 1× benchmark. This is a strategy-cost stress test against a fixed reference, not a comparison at matching cost rates. The main 1× baseline is unaffected.

The review retained the saved strategy paths and reran the benchmark at each matching multiplier. Commission, slippage, and sell-side tax scale together. Every return below is cumulative over the full period.

| Cost multiplier | Strategy cumulative return | Same-cost benchmark return | Cumulative relative wealth return |
| --- | ---: | ---: | ---: |
| 0× | 32.56% | 19.98% | 10.49% |
| 1× | 27.01% | 19.73% | 6.08% |
| 2× | 21.69% | 19.48% | 1.85% |

Full precision is available in the [same-cost comparison CSV](publication/retrospective_20261127/cost_comparison_corrected.csv). The supplemental run uses the original inputs, factors, and backtest engine. Original data, configuration, and historical `metrics.csv` remain unchanged. This comparison is complete; automating the matching benchmark scenarios in the pipeline remains future work.

Relative wealth return falls to about 1.85% when costs double, showing cost sensitivity within this sample. Fixed teaching costs also do not reconstruct historical fee schedules. For example, securities transaction stamp duty was [halved from August 28, 2023](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html); a historical cost model needs effective-date rules.

### Remaining limitations

1. **Historical universe membership is not reconstructed.** The fixed 30-stock sample can introduce selection and survivorship bias. Its eligibility flags do not fully verify historical ST status, listing age, delistings, or investability.
2. **Historical tradability is unknown.** Every real-market record has `status_known=0`. Explicitly allowing unknown states is a teaching assumption, not new execution evidence. Adjusted execution prices, fractional units, trading lots, corporate-action cash flows, and capacity constraints need further work.
3. **Missing prices and held-position valuation need more detail.** The snapshot has gaps, and the current engine stops if a held position lacks a valid valuation. A fuller model must distinguish suspension, listing status, and feed failure before applying valuation rules. Input coverage of 2019–2025 does not mean a seven-year real-market backtest was completed.
4. **There is no new untouched out-of-sample proof.** The 2025 results have been viewed. Changes to windows, directions, or weights based on them need new validation evidence; repeatedly reusing that year would understate the effects of selection after observing results.

For research protocols and backtest overfitting, see Arnott, Harvey, and Markowitz's [A Backtesting Protocol in the Era of Machine Learning](https://people.duke.edu/~charvey/Research/Published_Papers/SSRN-id3275654.pdf).

### Priorities for the next version

These are planned research tasks, not completed deliverables from this phase.

| Order | Work | Evidence required |
| --- | --- | --- |
| 1 | Improve historical universe, status data, and gap classification | Traceable sources, entry and exit records, point-in-time eligibility, and a quality report |
| 2 | Freeze hypotheses, parameter ranges, and validation design | A research protocol and a complete experiment log, including failed variants |
| 3 | Compare individual factors, the composite, and factor-removal variants | Same-cost incremental tests, industry/size exposure analysis, and uncertainty estimates |
| 4 | Improve execution, costs, and capacity modeling | Historical fees, corporate actions and cash reconciliation, constraint scenarios, and automated matching benchmarks |
| 5 | Validate on new evidence and write the research report | Reproducible results, independent validation or forward paper-tracking records |

The next research question is: **Do momentum and activity improve a low-volatility strategy after controlling for historical universe membership, risk exposures, and realistic costs?** The aim is an explainable, reproducible conclusion; performance improvement must be established by validation. The current work can be described as a personal multi-factor research and backtesting project. Claims of persistent alpha, institutional live-trading readiness, or elimination of survivorship bias remain unsupported.

<p align="center"><a href="#quantitativeteamproject1">Back to top</a> · <a href="README.md">阅读中文版</a></p>
