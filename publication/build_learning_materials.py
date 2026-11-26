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
    """Build both README languages from their maintained Markdown templates."""
    english_titles = {
        "00": "Environment setup",
        "01": "Read price data and its 13 fields",
        "02": "Daily returns from adjusted prices",
        "03": "Cumulative returns and buy-and-hold NAV",
        "04": "NAV and maximum drawdown",
        "05": "20-day momentum",
        "06": "Cross-sectional momentum rankings",
        "07": "Momentum and forward returns",
        "08": "Monthly IC and ICIR",
        "09": "Momentum quintile returns",
        "10": "Volatility and relative volume",
        "11": "MAD clipping, standardization, and factor direction",
        "12": "Equal-weight factor scores and stock selection",
        "13": "First trades and portfolio accounting",
        "14": "Daily valuation and the next rebalance",
        "15": "Full-period backtest and performance metrics",
        "16": "Benchmark and trading-cost comparisons",
        "17": "Period-by-period stability checks",
        "18": "Real-market snapshot and historical replay",
        "19": "Reproduction, validation, and delivery",
    }
    chinese_rows, english_rows = [], []
    for folder in sorted(folders):
        step = folder.name[:2]
        if step not in english_titles:
            raise ValueError(f"Add an English title for lesson {step}")
        title = (folder / "README.md").read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
        title = re.sub(r"^第\s*\d+\s*步[：:]\s*", "", title)
        notes = f"lessons/{folder.name}/README.md"
        notebook = f"lessons/{folder.name}/lesson.ipynb"
        chinese_rows.append(f"| {step} | {title} | [讲解]({notes}) | [Notebook]({notebook}) |")
        english_rows.append(f"| {step} | {english_titles[step]} | [Notes]({notes}) | [Notebook]({notebook}) |")
    chinese_table = "\n".join(["| 步骤 | 内容 | 讲解 | Notebook |", "| --- | --- | --- | --- |", *chinese_rows])
    english_table = "\n".join(["| Step | Topic | Notes | Notebook |", "| --- | --- | --- | --- |", *english_rows])
    for template_name, output_name, table in [
        ("README.zh.md", "README.md", chinese_table),
        ("README.en.md", "README.en.md", english_table),
    ]:
        template = (ROOT / "publication/readme_templates" / template_name).read_text(encoding="utf-8")
        marker = "<!-- LESSON_TABLE -->"
        if template.count(marker) != 1:
            raise ValueError(f"Expected one lesson table marker in {template_name}")
        (ROOT / output_name).write_text(template.replace(marker, table), encoding="utf-8", newline="\n")


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
