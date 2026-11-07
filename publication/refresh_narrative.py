"""同步 README 与 Notebook 的说明文字，保留已执行的代码、输出和图表。"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

import nbformat

from build_learning_materials import make_root_index, remove_generated

ROOT = Path(__file__).resolve().parents[1]


def original_file(ref, relative):
    return subprocess.check_output(["git", "show", f"{ref}:{relative}"], cwd=ROOT)


def prose(text):
    return re.sub(r"```.*?```", "", remove_generated(text), flags=re.S)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="HEAD")
    args = parser.parse_args()
    baseline = subprocess.check_output(
        ["git", "rev-parse", args.baseline], cwd=ROOT, text=True).strip()
    folders = sorted(p.parent for p in ROOT.glob("lessons/*/README.md"))
    records = []
    validation_path = ROOT / "publication/notebook_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    by_path = {row["path"]: row for row in validation["notebooks"]}
    for folder in folders:
        relative = (folder / "README.md").relative_to(ROOT).as_posix()
        previous = original_file(baseline, relative).decode("utf-8").replace("\r\n", "\n")
        current = (folder / "README.md").read_text(encoding="utf-8")
        # 润色可以改变说明文字，不能悄然改写示例代码或展示公式。
        executable_fences = lambda text: [(language, body) for language, body in
            re.findall(r"```([^\n]*)\n(.*?)```", text, re.S) if language.strip() != "mermaid"]
        assert executable_fences(previous) == executable_fences(current), relative
        assert re.findall(r"\$\$.*?\$\$", previous, re.S) == re.findall(r"\$\$.*?\$\$", current, re.S), relative
        assert re.findall(r"!\[[^\]]*\]\(([^)]+)\)", previous) == re.findall(r"!\[[^\]]*\]\(([^)]+)\)", current), relative
        path = folder / "lesson.ipynb"
        nb = nbformat.read(path, as_version=4)
        old_nb = nbformat.reads(original_file(baseline, path.relative_to(ROOT).as_posix()).decode("utf-8"), as_version=4)
        old_code = [copy.deepcopy(c) for c in old_nb.cells if c.cell_type == "code"]
        split = next(i for i, c in enumerate(nb.cells) if c.cell_type == "markdown"
                     and c.source.startswith(("## 我的完整可运行实现", "## 完整可运行实现")))
        sections = [s.strip() for s in re.split(r"(?=^## )", remove_generated(current), flags=re.M) if s.strip()]
        narrative = []
        old_markdown = nb.cells[:split]
        for index, section in enumerate(sections):
            cell = copy.deepcopy(old_markdown[index]) if index < len(old_markdown) else nbformat.v4.new_markdown_cell()
            assert cell.cell_type == "markdown"
            cell.source = section
            narrative.append(cell)
        nb.cells = narrative + nb.cells[split:]
        for cell in nb.cells[len(narrative):]:
            if cell.cell_type != "markdown":
                continue
            cell.source = (cell.source
                .replace("## 我的完整可运行实现", "## 完整可运行实现")
                .replace("我先定位仓库根目录", "先定位仓库根目录")
                .replace("## 我的图表输出", "## 图表输出")
                .replace("完整脚本已经保存图表。我在这里把", "完整脚本已经保存图表。这里把")
                .replace("## 我的复核", "## 运行复核")
                .replace("我在干净内核中按顺序执行以上实现", "以上实现已在干净内核中按顺序执行"))
        assert [c for c in nb.cells if c.cell_type == "code"] == old_code, str(path)
        nbformat.validate(nb)
        nbformat.write(nb, path)
        by_path[path.relative_to(ROOT).as_posix()]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append({"step": int(folder.name[:2]), "first_person_before": prose(previous).count("我"),
                        "first_person_after": prose(current).count("我"),
                        "code_cells_and_saved_outputs": "identical to baseline",
                        "executable_fenced_code_display_formulas_and_image_targets": "unchanged",
                        "diagram_labels": "Presentation wording may be revised; dates and timeline are preserved."})
    make_root_index(folders)
    validation["narrative_revision"] = {"updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": baseline, "scope": "Markdown only; all executed code cells, execution counts and saved outputs preserved."}
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    record = {"baseline_commit": baseline, "scope": "Natural prose revision across learning materials",
              "steps": records, "status": "passed"}
    (ROOT / "publication/editorial_revision.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"notebooks_updated": len(records), "code_and_outputs_preserved": True,
          "first_person_before": sum(r["first_person_before"] for r in records),
          "first_person_after": sum(r["first_person_after"] for r in records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
