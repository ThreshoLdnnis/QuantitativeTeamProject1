"""把全部教学内容、数据、数据库和运行结果保存为固定版本快照。"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "QuantitativeTeamProject1-full-snapshot.zip"
EXCLUDED = {".git", ".venv", "__pycache__", ".ipynb_checkpoints", ".pytest_cache"}


def main():
    archive = ROOT.parent / NAME
    files = sorted(path for path in ROOT.rglob("*") if path.is_file()
                   and not any(part in EXCLUDED or part.endswith(".egg-info") for part in path.parts)
                   and path.suffix not in {".pyc", ".pyo", ".zip"})
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in files:
            bundle.write(path, f"{ROOT.name}/{path.relative_to(ROOT).as_posix()}")
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("完整快照 ZIP 校验失败。")
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest.hexdigest()}  {NAME}\n", encoding="utf-8")
    print(json.dumps(dict(archive=str(archive), files=len(files), bytes=archive.stat().st_size,
                          sha256=digest.hexdigest(), checksum=str(checksum)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
