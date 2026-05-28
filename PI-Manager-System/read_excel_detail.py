import pandas as pd

# 读取 Excel 文件
excel_path = r'D:\TraeProjects\PI Manager\PI-Manager-System\docs\订单管理总表.xlsx'

df = pd.read_excel(excel_path, header=None)

print("=== 订单管理总表模板完整列结构 ===\n")
print(f"总行数: {len(df)}, 总列数: {len(df.columns)}\n")

# 提取表头（第1行）
print("--- 表头行（索引0）---")
header = df.iloc[0].tolist()
for i, col in enumerate(header):
    if pd.notna(col):
        print(f"列 {i}: {col}")

print("\n--- 说明行（索引1-9）---")
for row_idx in range(1, min(10, len(df))):
    row = df.iloc[row_idx].tolist()
    non_empty = [(i, str(v)) for i, v in enumerate(row) if pd.notna(v)]
    if non_empty:
        print(f"\n行 {row_idx}:")
        for i, v in non_empty:
            print(f"  列{i}: {v[:100]}")  # 截取前100字符

print("\n\n--- 数据示例（第2行之后）---")
if len(df) > 2:
    for row_idx in range(2, min(5, len(df))):
        row = df.iloc[row_idx].tolist()
        print(f"\n行 {row_idx}:")
        for i, v in enumerate(row):
            if pd.notna(v):
                val = str(v)[:80]
                print(f"  列{i}: {val}")
