# 完整数据与结果索引

全部代码、每步 README、每步 Notebook、图表和小型结果表均可在仓库中直接浏览。教程文案更新至 v1.0.1，输入数据和计算结果保持不变，沿用 v1.0.0 的固定快照。完整数据、SQLite 和大型中间表保存在下方 ZIP 中，保留项目原有相对目录。

- [v1.0.0 固定数据快照](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.0)
- [完整快照 ZIP](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/download/v1.0.0/QuantitativeTeamProject1-full-snapshot.zip)
- [ZIP 的 SHA-256](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/download/v1.0.0/QuantitativeTeamProject1-full-snapshot.zip.sha256)

在仓库根目录执行 `python publication/restore_snapshot.py`，脚本会核对 ZIP 哈希并恢复 `data/` 与 `runs/`，保留当前源码与学习文档。手动恢复时，只将 ZIP 中的 `data/` 与 `runs/` 合并到当前项目，避免用历史版本的教程覆盖新版文案。

正文中的大型表格链接指向本索引；每一行路径都是完整 ZIP 中可以查到的实际文件。图表和 Notebook 静态输出可直接阅读。恢复完整快照后，既有真实数据实验可以离线运行；重新取数则需要另行记录来源和下载时间。

| 完整快照中的路径 | 大小 MiB | SHA-256 |
| --- | ---: | --- |
| `data/market_teaching/prices.csv` | 4.388 | `4473e5398f359f0cf2f24f7b28034ea16bd1159835df25ab6c7f80698bff9e5c` |
| `data/market_teaching/universe.csv` | 1.167 | `8916ce3e8a7711ef2dda8577ea8fa2cc849eaf528f5412b70fc1ac7f505c9d45` |
| `runs/first_demo_20261107/factors.csv` | 10.911 | `d5e05c1b5371c30a64684333a9f6828a30eedb9dc60087ebfdb0e492b685c041` |
| `runs/first_demo_20261107/input/prices.csv` | 12.784 | `e7fa8d62ddf8baa92f3d2b45c96096644f6c38fc13aa94e4c4acb07f57dd3b36` |
| `runs/first_demo_20261107/input/universe.csv` | 1.673 | `2deb2208a998c326480639ecb3cf268013b1e8e126513cc79bc682db81767a0d` |
| `runs/first_demo_20261107/lesson10_raw_factors/raw_factors.csv` | 9.875 | `c02bd60a7d1c58177f9d37a880c180d1add464f00d8f27394a1d57199b73d126` |
| `runs/first_demo_20261107/lesson15_full_backtest/positions.csv` | 1.361 | `dfd26b4f254819ede3822a1ca14bace1774ab639a09998fe32b5e8f6599178b9` |
| `runs/first_demo_20261107/lesson16_benchmark_cost/benchmark_cost0/positions.csv` | 5.579 | `01f91e5a3a2f0802a69582005182b07d33416860f1e65238f419450993133b28` |
| `runs/first_demo_20261107/lesson16_benchmark_cost/benchmark_cost1/positions.csv` | 5.579 | `9503d4ebdcf94a3ab68a42426ee3736a8e9af26cee6729d3f742b33d44e81ef4` |
| `runs/first_demo_20261107/lesson16_benchmark_cost/benchmark_cost2/positions.csv` | 5.578 | `a3e5c50bf96e65dbf5da72e296dfda45f5526d92b209ef6f9ab6432d9123f393` |
| `runs/first_demo_20261107/lesson16_benchmark_cost/strategy_cost0/positions.csv` | 1.364 | `d3abe6705f1d1e8126b5726e46e6a62ff2aa1f1d08cf2ffe82ef177bd0e0fe5b` |
| `runs/first_demo_20261107/lesson16_benchmark_cost/strategy_cost1/positions.csv` | 1.361 | `dfd26b4f254819ede3822a1ca14bace1774ab639a09998fe32b5e8f6599178b9` |
| `runs/first_demo_20261107/lesson16_benchmark_cost/strategy_cost2/positions.csv` | 1.360 | `403e509098407ebfc9289cb3b4c656c5241a88bd35c6195a26aa000fe44d3cf6` |
| `runs/first_demo_20261107/positions_activity.csv` | 1.379 | `7b07f99db6f7c5e1b838aa9810c51d1c1a95c0e107a56236524a535762f1b466` |
| `runs/first_demo_20261107/positions_benchmark.csv` | 5.579 | `9503d4ebdcf94a3ab68a42426ee3736a8e9af26cee6729d3f742b33d44e81ef4` |
| `runs/first_demo_20261107/positions_momentum.csv` | 1.375 | `99584ca25d8998ce127e81c54b5b201c30054d5a00626e9f4a19cb223c9cdcd6` |
| `runs/first_demo_20261107/positions_multifactor.csv` | 1.361 | `dfd26b4f254819ede3822a1ca14bace1774ab639a09998fe32b5e8f6599178b9` |
| `runs/first_demo_20261107/positions_multifactor_cost0.csv` | 1.364 | `d3abe6705f1d1e8126b5726e46e6a62ff2aa1f1d08cf2ffe82ef177bd0e0fe5b` |
| `runs/first_demo_20261107/positions_multifactor_cost2.csv` | 1.360 | `403e509098407ebfc9289cb3b4c656c5241a88bd35c6195a26aa000fe44d3cf6` |
| `runs/first_demo_20261107/positions_volatility.csv` | 1.391 | `4c97ba9d14d4be3ff659e0d892ded6ffe011cae674090c215a0ba8d963fc9616` |
| `runs/first_demo_20261107/research.sqlite` | 36.910 | `8b40f609c5fe15141b419199760ca86f39466871462e66c46e8a555b233d0815` |
| `runs/lesson18_real_market/experiment/factors.csv` | 7.581 | `8bd3199b062c358a5060e97e602b7aea2791737c4f8cbe732586fdce8bd97935` |
| `runs/lesson18_real_market/experiment/positions_benchmark.csv` | 1.682 | `0d7d0ded785a4aa6c1d09354d98be7f6ba6b199882cab9309efe61ec1e84d4a3` |
| `runs/lesson18_real_market/experiment/research.sqlite` | 20.820 | `e41d600ed41ee82cdcddb6af8e184baec4a9277aa351e6326f11a83b4bc94aa7` |
