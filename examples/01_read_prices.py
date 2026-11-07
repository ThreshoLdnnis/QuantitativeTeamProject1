"""第一课：读取一只模拟股票的日行情；只读取文件，不修改原始数据。"""

from pathlib import Path  # 1. 处理文件路径
import pandas as pd  # 2. 导入表格处理库

project_dir = Path(__file__).resolve().parents[1]  # 3. 定位项目根目录
data_path = project_dir / "runs" / "first_demo_20261107" / "input" / "prices.csv"  # 4. 定位输入文件

prices = pd.read_csv(data_path, dtype={"symbol": "string"}, parse_dates=["date"])  # 5. 读取行情
symbol = "SYN001"  # 6. 选择要观察的模拟股票；可以改成 SYN002
stock = prices.loc[prices["symbol"] == symbol].copy()  # 7. 筛选这只股票
stock = stock.sort_values("date").reset_index(drop=True)  # 8. 按时间排序并重排行标签

preview_columns = ["date", "symbol", "open", "high", "low", "close"]  # 9. 选择预览列
print(f"全部行情的形状：{prices.shape}；{symbol} 的形状：{stock.shape}")  # 10. 查看行数和列数
print(stock[preview_columns].head(5).to_string(index=False))  # 11. 预览前 5 行

print("\n每列的数据类型：")
print(stock.dtypes.to_string())  # 12. 查看日期、字符串、数字、布尔类型

print("\n第一行的全部字段：")
print(stock.iloc[0].to_string())  # 13. 逐项查看第一条记录
