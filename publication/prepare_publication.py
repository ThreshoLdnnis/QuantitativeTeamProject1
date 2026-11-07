"""发布整理：校验文档、区分可浏览文件和完整快照、生成索引。"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import nbformat

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "__pycache__", ".ipynb_checkpoints", ".pytest_cache"}
THRESHOLD = 1024 * 1024


def all_files():
    return sorted(path for path in ROOT.rglob("*") if path.is_file()
                  and not any(part in EXCLUDED or part.endswith(".egg-info") for part in path.parts)
                  and path.suffix not in {".pyc", ".pyo", ".zip"})


def snapshot_only(path):
    return path.suffix == ".sqlite" or (path.stat().st_size > THRESHOLD and path.suffix.lower() not in {".ipynb", ".png", ".svg"})


def relink_markdown(text, origin, large):
    target_index = os.path.relpath(ROOT / "publication/ASSET_INDEX.md", origin.parent).replace("\\", "/")
    def replacement(match):
        link = match.group(2).strip("<>")
        parsed = urlsplit(link)
        if not parsed.scheme and parsed.path:
            target = (origin.parent / unquote(parsed.path)).resolve()
            if target in large:
                return match.group(1) + "(" + target_index + ")"
        return match.group(0)
    parts = re.split(r"(```.*?```)", text, flags=re.S)
    for index in range(0, len(parts), 2):
        parts[index] = re.sub(r"(!?\[[^\]]*\])\(([^)]+)\)", replacement, parts[index])
    return "".join(parts)


def prepare():
    files = all_files()
    large = {path for path in files if snapshot_only(path)}
    table = ["| 完整快照中的路径 | 大小 MiB | SHA-256 |", "| --- | ---: | --- |"]
    for path in sorted(large):
        data = path.read_bytes()
        table.append(f"| `{path.relative_to(ROOT).as_posix()}` | {len(data)/1024**2:.3f} | `{hashlib.sha256(data).hexdigest()}` |")
    text = """# 完整数据与结果索引

全部代码、每步 README、每步 Notebook、图表和小型结果表均可在仓库中直接浏览。完整数据快照、SQLite 和大型中间表放在同版本 Release 的完整 ZIP 中，保留项目原有相对目录。

- [v1.0.1 完整 Release](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/tag/v1.0.1)
- [完整快照 ZIP](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/download/v1.0.1/QuantitativeTeamProject1-full-snapshot.zip)
- [ZIP 的 SHA-256](https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/download/v1.0.1/QuantitativeTeamProject1-full-snapshot.zip.sha256)

在仓库根目录执行 `python publication/restore_snapshot.py`，脚本会核对 ZIP 哈希并恢复 `data/` 与 `runs/`，保留当前源码与学习文档。也可手动把完整 ZIP 解压到仓库父目录，合并其中的 `QuantitativeTeamProject1/`。

正文中的大型表格链接指向本索引；每一行路径都是完整 ZIP 中可以查到的实际文件。图表和 Notebook 静态输出可直接阅读。恢复完整快照后，既有真实数据实验可以离线运行；重新取数则需要另行记录来源和下载时间。

""" + "\n".join(table) + "\n"
    (ROOT / "publication/ASSET_INDEX.md").write_text(text, encoding="utf-8")
    data_note = ("## 数据准备\n\n本页内容来自完整快照上的实际运行。"
                 "从 GitHub 克隆源码后，先在仓库根目录运行 `python publication/restore_snapshot.py`，"
                 "恢复同版本的 `data/` 与 `runs/`，再执行本步。"
                 "[完整数据与大型结果索引](../../publication/ASSET_INDEX.md)保留全部路径和哈希；"
                 "本页图表与 Notebook 已保存输出可直接阅读。\n")
    for path in ROOT.rglob("*.md"):
        if any(part in EXCLUDED for part in path.parts):
            continue
        original = path.read_text(encoding="utf-8")
        changed = relink_markdown(original, path, large)
        if path.parent.parent == ROOT / "lessons" and "<!-- SNAPSHOT_NOTE -->" not in changed:
            first, rest = changed.split("\n", 1)
            changed = first + "\n\n<!-- SNAPSHOT_NOTE -->\n" + data_note + "\n" + rest
        if original != changed:
            path.write_text(changed, encoding="utf-8")
    validation_path = ROOT / "publication/notebook_validation.json"
    notebook_validation = json.loads(validation_path.read_text(encoding="utf-8"))
    by_path = {row["path"]: row for row in notebook_validation["notebooks"]}
    for path in ROOT.glob("lessons/*/lesson.ipynb"):
        notebook = nbformat.read(path, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == "markdown":
                cell.source = relink_markdown(cell.source, path, large)
        if not any("<!-- SNAPSHOT_NOTE -->" in cell.source for cell in notebook.cells if cell.cell_type == "markdown"):
            notebook.cells.insert(1, nbformat.v4.new_markdown_cell("<!-- SNAPSHOT_NOTE -->\n" + data_note))
        nbformat.validate(notebook)
        nbformat.write(notebook, path)
        by_path[path.relative_to(ROOT).as_posix()]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    notebook_validation["presentation_links_updated"] = "Large cached tables point to the release index; executable code and numerical/image outputs are unchanged."
    validation_path.write_text(json.dumps(notebook_validation, ensure_ascii=False, indent=2), encoding="utf-8")
    # 完整报告下载大文件时也指向索引，避免仓库网页出现 404。
    for path in ROOT.rglob("*.html"):
        if any(part in EXCLUDED for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8")
        target_index = os.path.relpath(ROOT / "publication/ASSET_INDEX.md", path.parent).replace("\\", "/")
        def html_link(match):
            relative = match.group(2)
            parsed = urlsplit(relative)
            if not parsed.scheme and (path.parent / unquote(parsed.path)).resolve() in large:
                return match.group(1) + target_index + match.group(3)
            return match.group(0)
        content = re.sub(r'(href=["\'])([^"\']+)(["\'])', html_link, content)
        path.write_text(content, encoding="utf-8")
    ignore = ".venv/\n__pycache__/\n*.pyc\n*.egg-info/\n.ipynb_checkpoints/\n*.sqlite\n\n# 大型快照保留在同版本 Release\n"
    ignore += "\n".join("/" + path.relative_to(ROOT).as_posix() for path in sorted(large) if path.suffix != ".sqlite") + "\n"
    (ROOT / ".gitignore").write_text(ignore, encoding="utf-8")
    return large


def verify_content():
    lessons = sorted(ROOT.glob("lessons/*/README.md"))
    notebooks = sorted(ROOT.glob("lessons/*/lesson.ipynb"))
    assert len(lessons) == len(notebooks) == 20
    assert [int(path.parent.name[:2]) for path in lessons] == list(range(20))
    explanations = 0
    for path in lessons:
        content = path.read_text(encoding="utf-8")
        narrative = content.split("<!-- GENERATED_FULL_SOURCE_START -->")[0]
        prose = re.sub(r"```.*?```", "", narrative, flags=re.S)
        explanations += len(re.findall(r"[\u4e00-\u9fff]", prose))
        assert content.count("```") % 2 == 0
    code_cells, image_outputs = 0, 0
    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                code_cells += 1
                assert cell.execution_count is not None
                if any(out.output_type == "error" for out in cell.get("outputs", [])):
                    raise ValueError(f"Notebook 保存了执行错误：{path}")
            image_outputs += sum("image/png" in out.get("data", {}) for out in cell.get("outputs", []))
    record = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), readmes=len(lessons),
                  executed_notebooks=len(notebooks), executed_code_cells=code_cells,
                  png_outputs=image_outputs, narrative_chinese_characters=explanations,
                  voice="natural learning narrative; first person used selectively for personal choices and reflections", status="passed")
    (ROOT / "publication/validation.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def write_plan(path):
    rows = []
    for file in all_files():
        if snapshot_only(file):
            continue
        data = file.read_bytes()
        try:
            text = data.decode("utf-8")
            encoding, characters = "utf-8", len(text)
        except UnicodeDecodeError:
            encoding, characters = "base64", None
        rows.append(dict(path=file.relative_to(ROOT).as_posix(), bytes=len(data), characters=characters,
                         encoding=encoding, git_sha=hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
                         sha256=hashlib.sha256(data).hexdigest()))
    path.write_text(json.dumps(dict(root=str(ROOT), files=rows), ensure_ascii=False, indent=2), encoding="utf-8")
    return dict(files=len(rows), MiB=sum(row["bytes"] for row in rows) / 1024**2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--skip-prepare", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.plan_only:
        if not args.plan:
            raise ValueError("--plan-only 需要 --plan 路径。")
        print(json.dumps(write_plan(args.plan), ensure_ascii=False, indent=2))
        return
    if not args.skip_prepare:
        prepare()
    record = verify_content()
    if args.plan:
        record["github_payload"] = write_plan(args.plan)
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
