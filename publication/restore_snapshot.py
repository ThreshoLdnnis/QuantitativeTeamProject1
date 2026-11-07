"""从固定 GitHub Release 恢复 data/ 与 runs/，保留当前源码与学习记录。"""
import hashlib
from pathlib import Path
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://github.com/ThreshoLdnnis/QuantitativeTeamProject1/releases/download/v1.0.1/"
NAME = "QuantitativeTeamProject1-full-snapshot.zip"


def main():
    with urllib.request.urlopen(BASE + NAME + ".sha256", timeout=60) as response:
        expected = response.read().decode("utf-8").split()[0]
    with tempfile.TemporaryDirectory(prefix="qtp1-snapshot-") as temporary:
        archive = Path(temporary) / NAME
        print("正在下载同版本完整快照……", flush=True)
        urllib.request.urlretrieve(BASE + NAME, archive)
        digest = hashlib.sha256()
        with archive.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError("完整快照 SHA-256 不一致，停止解压。")
        restored = 0
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                parts = Path(item.filename).parts
                if len(parts) < 3 or parts[1] not in {"data", "runs"} or item.is_dir():
                    continue
                destination = ROOT.joinpath(*parts[1:]).resolve()
                if not destination.is_relative_to(ROOT):
                    raise ValueError("快照路径越出仓库。")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(item) as source, destination.open("wb") as target:
                    while block := source.read(1024 * 1024):
                        target.write(block)
                restored += 1
        print(f"已恢复 {restored} 个数据与结果文件；当前源码和学习文档保持原样。")


if __name__ == "__main__":
    main()
