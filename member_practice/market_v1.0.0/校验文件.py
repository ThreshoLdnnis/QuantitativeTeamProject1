"""Verify individually distributed market files against the leader's external SHA-256."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

BUNDLE = "QTP1-MARKET-FILES-1.0.0"
MANIFEST = "09_文件哈希清单.txt"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(root, expected):
    root = Path(root).resolve()
    expected = expected.strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError("请填入负责人独立公告的64位文件哈希清单摘要")
    manifest = root / MANIFEST
    if manifest.is_symlink() or sha(manifest) != expected:
        raise ValueError("文件哈希清单与负责人公告不一致")
    seen, failures = set(), []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if separator != "  " or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("文件哈希清单格式错误")
        if not name or name in {".", "..", MANIFEST} or any(c in name for c in "/\\:") or name in seen:
            raise ValueError(f"清单文件名无效或重复: {name}")
        seen.add(name)
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            failures.append(f"文件缺失或路径无效: {name}")
        elif sha(path) != digest:
            failures.append(f"文件发生变化: {name}")
    if not seen:
        raise ValueError("文件哈希清单为空")
    if failures:
        raise ValueError("；".join(failures))
    return {"status":"通过", "version":BUNDLE, "manifest_sha256":expected,
            "verified_files":len(seen),
            "note":"对照负责人外部摘要验证已列文件的字节。个人work输出不参与核验；不证明实际分析所用输入或独立完成情况。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--folder", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        report = verify(args.folder, args.expected_manifest_sha256)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"status":"失败", "error":str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
