"""我的第 0 步：检查解释器、依赖和项目输入位置。"""
from pathlib import Path
import importlib.metadata
import platform
import sys

project_dir = Path(__file__).resolve().parents[1]
print("我的 Python 版本：", platform.python_version())
print("我的解释器：", sys.executable)
for dependency in ["numpy", "pandas", "matplotlib"]:
    print(f"{dependency} = {importlib.metadata.version(dependency)}")
for relative in ["pyproject.toml", "configs/baseline.json", "examples/01_read_prices.py",
                 "runs/first_demo_20261107/input/metadata.json", "data/market_teaching/metadata.json"]:
    path = project_dir / relative
    if not path.exists():
        raise FileNotFoundError(f"我需要先准备项目文件：{relative}")
    print("已找到：", relative)
