"""把逐步学习记录、完整脚本和实际执行输出组织成 README 与 Notebook。"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- GENERATED_FULL_SOURCE_START -->"
END = "<!-- GENERATED_FULL_SOURCE_END -->"
NAV_START = "<!-- GENERATED_NAV_START -->"
NAV_END = "<!-- GENERATED_NAV_END -->"


def remove_generated(text):
    for first, last in [(START, END), (NAV_START, NAV_END)]:
        text = re.sub(re.escape(first) + r".*?" + re.escape(last), "", text, flags=re.S)
    return text.strip() + "\n"


def source_chunks(source):
    """保留完整执行顺序；函数/类作为整体，不把缩进体拆成无效单元。"""
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    chunks, buffered, previous = [], "", 0
    for node in tree.body:
        part = "".join(lines[previous:node.end_lineno])
        previous = node.end_lineno
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If)):
            if buffered.strip():
                chunks.append(buffered.strip())
                buffered = ""
            chunks.append(part.strip())
        else:
            buffered += part
            if len(buffered) >= 2000:
                chunks.append(buffered.strip())
                buffered = ""
    buffered += "".join(lines[previous:])
    if buffered.strip():
        chunks.append(buffered.strip())
    assert ast.dump(ast.parse("\n\n".join(chunks)), include_attributes=False) == ast.dump(tree, include_attributes=False)
    return chunks


def build_notebook(folder, narrative, source_path):
    number = int(folder.name[:2])
    source = source_path.read_text(encoding="utf-8")
    image_paths = []
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", narrative):
        path = (folder / match.group(1).strip("<>")).resolve()
        if path.exists() and path.suffix.lower() == ".png" and path.is_relative_to(ROOT):
            image_paths.append(path.relative_to(ROOT).as_posix())
    image_paths = list(dict.fromkeys(image_paths))
    nb = nbformat.v4.new_notebook()
    nb.metadata.update(kernelspec={"display_name": "Python 3", "language": "python", "name": "python3"},
                       language_info={"name": "python", "version": "3.12"},
                       project={"step": number, "source": source_path.relative_to(ROOT).as_posix(),
                                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest()})
    for section in re.split(r"(?=^## )", narrative, flags=re.M):
        if section.strip():
            nb.cells.append(nbformat.v4.new_markdown_cell(section.strip()))
    nb.cells.append(nbformat.v4.new_markdown_cell(
        "## 完整可运行实现\n\n上面的片段用于解释思路；下面各单元按顺序执行完整脚本。"
        "先定位仓库根目录，并显式设置脚本路径，使 `__file__` 在 Notebook 中也有明确含义。"
        + ("第 19 步固定使用 `--verify-only`，因此本 Notebook 会校验并更新报告，不自动创建交付 ZIP。" if number == 19 else "")))
    source_relative = source_path.relative_to(ROOT).as_posix()
    bootstrap = f'''from pathlib import Path
import os
import sys

PROJECT_ROOT = next((candidate for candidate in [Path.cwd(), *Path.cwd().parents]
                     if (candidate / "pyproject.toml").exists()
                     and (candidate / "examples/01_read_prices.py").exists()), None)
if PROJECT_ROOT is None:
    raise FileNotFoundError("我需要从本项目目录或它的子目录打开 Notebook。")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)
__file__ = str(PROJECT_ROOT / {source_relative!r})
sys.argv = [__file__]{' + ["--verify-only"]' if number == 19 else ''}
'''
    nb.cells.append(nbformat.v4.new_code_cell(bootstrap))
    for index, chunk in enumerate(source_chunks(source), start=1):
        nb.cells.append(nbformat.v4.new_markdown_cell(f"### 完整实现 · 单元 {index}"))
        nb.cells.append(nbformat.v4.new_code_cell(chunk))
    if image_paths:
        nb.cells.append(nbformat.v4.new_markdown_cell(
            "## 图表输出\n\n完整脚本已经保存图表。这里把本步或正文明确引用的跨步图表显示为静态输出，"
            "因此 GitHub 页面无需活动内核也能看到图片。数值与图表来源沿用正文说明。"))
        for relative in image_paths:
            nb.cells.append(nbformat.v4.new_code_cell(
                "from IPython.display import Image, display\n"
                f"display(Image(filename=str(PROJECT_ROOT / {relative!r})))"))
    nb.cells.append(nbformat.v4.new_markdown_cell(
        "## 运行复核\n\n以上实现已在干净内核中按顺序执行；执行状态记录在仓库的 "
        "[Notebook 校验记录](../../publication/notebook_validation.json)。"
        "代码中的数据身份、费用和成交假设仍然适用，运行成功只验证对应实现。"))
    nbformat.validate(nb)
    nbformat.write(nb, folder / "lesson.ipynb")
    return nb


def make_root_index(folders):
    rows = []
    for folder in folders:
        title = (folder / "README.md").read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
        rows.append(f"| {folder.name[:2]} | {title} | [详细讲解](lessons/{folder.name}/README.md) | [运行与输出](lessons/{folder.name}/lesson.ipynb) |")
    table = "\n".join(["| 步骤 | 学习内容 | README | Notebook |", "| --- | --- | --- | --- |", *rows])
    text = f'''# QuantitativeTeamProject1

## 金融修道第二期：如何从零到一搭建 A 股多因子选股与回测系统

这份项目记录了我从基础 Python 出发，逐步搭建量化选股与回测系统的过程，包含 **第 0 步的环境准备 + 第 1—19 步完整操作流程**。每一步都有独立的 README 和可运行 Notebook，保留公式推导、代码解释、实际数值、图表与验收记录。实现中的假设和限制，以及没有跑赢基准的结果，也一并记录。

完整流程：**环境 → 行情 → 收益与回撤 → 动量 → IC 与分组 → 三因子处理 → 综合选股 → 成交与现金 → 全期回测 → 基准和成本 → 分段检查 → 真实行情回放 → 交付复现**。

## 阅读顺序

- 从 [第 0 步](lessons/00_environment/README.md)确认环境和数据位置，再按编号向后推进。
- README 提供详细讲解和学习记录，Notebook 保存实际执行输出，并提供按顺序运行的完整代码。
- [完整快照索引](publication/ASSET_INDEX.md)说明大表、原始快照和 SQLite 的位置。教程与 Notebook 已更新至 [v1.0.1](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.1)，数据与计算结果沿用 [v1.0.0 固定快照](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.0)。恢复脚本只提取数据与结果，保留当前教程文案。源码、全部图文教材、Notebook、图表和小型结果表可在仓库内直接浏览。

{table}

## 环境安装与复现

项目已在 Python 3.12 环境验证。Windows PowerShell 的完整操作如下；没有 `py` 时，可使用第 0 步记录的解释器绝对路径方法。

```powershell
git clone https://github.com/ThreshoLdnnis/QuantitativeTeamProject1.git
cd QuantitativeTeamProject1
py -3.12 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-tested.txt -e ".[plots]"
.\\.venv\\Scripts\\python.exe publication/restore_snapshot.py
.\\.venv\\Scripts\\python.exe examples/19_finalize_project.py --verify-only
```

运行 Notebook 时，另外安装：

```powershell
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-notebooks.txt
.\\.venv\\Scripts\\python.exe -m jupyter lab
```

安装后可直接打开 `lessons/NN_*/lesson.ipynb`。Notebook 会从当前目录向上定位仓库，并设置脚本路径；第 19 步 Notebook 固定使用校验模式，避免无意重复打包。

完整重跑已有输入和第 01—18 课：

```powershell
.\\.venv\\Scripts\\python.exe examples/19_finalize_project.py --rebuild
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
'''
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def execute_notebooks(folders):
    results = []
    # 使用当前构建环境的解释器启动内核，避免调用本机另一个 Python。
    with tempfile.TemporaryDirectory(prefix="qtp1-kernel-") as temporary:
        kernel_dir = Path(temporary) / "qtp1"
        kernel_dir.mkdir()
        (kernel_dir / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "QuantitativeTeamProject1 Python", "language": "python"}), encoding="utf-8")
        for folder in folders:
            path = folder / "lesson.ipynb"
            notebook = nbformat.read(path, as_version=4)
            print("执行 Notebook：", folder.name, flush=True)
            manager = KernelManager(kernel_name="qtp1", kernel_spec_manager=KernelSpecManager(kernel_dirs=[temporary]))
            client = NotebookClient(notebook, km=manager, timeout=900,
                                    resources={"metadata": {"path": str(folder)}})
            try:
                client.execute()
            except Exception:
                nbformat.write(notebook, path)
                raise
            finally:
                if manager.has_kernel:
                    manager.shutdown_kernel(now=True)
            # 只把机器目录显示成相对路径；数值、图像和执行顺序保持不变。
            for cell in notebook.cells:
                for output in cell.get("outputs", []):
                    if output.get("output_type") == "stream":
                        output["text"] = output["text"].replace(str(ROOT), ".").replace(sys.prefix, ".venv")
            nbformat.validate(notebook)
            nbformat.write(notebook, path)
            results.append(dict(step=int(folder.name[:2]), path=path.relative_to(ROOT).as_posix(),
                                 status="passed", code_cells=sum(c.cell_type == "code" for c in notebook.cells),
                                 image_outputs=sum("image/png" in out.get("data", {}) for cell in notebook.cells for out in cell.get("outputs", [])),
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (ROOT / "publication/notebook_validation.json").write_text(json.dumps({
        "executed_at_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
        "notebooks": results, "output_path_display": "Absolute workspace and environment paths normalized; numbers and images unchanged."},
        ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    folders = sorted(p.parent for p in (ROOT / "lessons").glob("*/README.md"))
    assert [int(p.name[:2]) for p in folders] == list(range(20))
    sources = {int(p.name[:2]): p for p in (ROOT / "examples").glob("[0-9][0-9]_*.py")}
    sources[0] = ROOT / "publication/environment_check.py"
    for index, folder in enumerate(folders):
        path = folder / "README.md"
        narrative = remove_generated(path.read_text(encoding="utf-8"))
        source = sources[index].read_text(encoding="utf-8")
        source_relative = sources[index].relative_to(ROOT).as_posix()
        navigation = [f"[项目首页](../../README.md)", "[本步 Notebook](lesson.ipynb)"]
        if index:
            navigation.append(f"[上一步](../{folders[index - 1].name}/README.md)")
        if index + 1 < len(folders):
            navigation.append(f"[下一步](../{folders[index + 1].name}/README.md)")
        appendix = f"\n{START}\n\n## 完整脚本源码\n\n本步完整实现见 [{sources[index].name}](../../{source_relative})。核心代码已在前文逐段解释，以下代码与脚本文件一致。\n\n```python\n{source.rstrip()}\n```\n\n{END}\n"
        path.write_text(narrative + appendix + "\n" + NAV_START + "\n\n" + " · ".join(navigation) + "\n\n" + NAV_END + "\n", encoding="utf-8")
        build_notebook(folder, narrative, sources[index])
    make_root_index(folders)
    for name in ["notebook_validation.json", "validation.json"]:
        path = ROOT / "publication" / name
        if not path.exists():
            path.write_text(json.dumps({"status": "preparing"}), encoding="utf-8")
    if args.execute:
        execute_notebooks(folders)
    print("已生成 20 篇 README 与 20 本 Notebook。", flush=True)


if __name__ == "__main__":
    main()
