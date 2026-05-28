import pandas as pd

# 读取 Excel 文件
excel_path = r'D:\TraeProjects\PI Manager\PI-Manager-System\docs\订单管理总表.xlsx'

try:
    df = pd.read_excel(excel_path, header=None)
    print("=== 订单管理总表模板内容 ===\n")
    print(f"行数: {len(df)}, 列数: {len(df.columns)}")
    print("\n--- 所有列 ---")
    for i, row in df.iterrows():
        values = [str(row[col]) if pd.notna(row[col]) else "" for col in df.columns]
        print(f"列 {i}: {values}")

    print("\n--- 提取表头（第1行）---")
    if len(df) > 0:
        header = df.iloc[0].tolist()
        for i, col in enumerate(header):
            if pd.notna(col):
                print(f"{i}: {col}")

    print("\n--- 数据行示例 ---")
    if len(df) > 1:
        for i in range(min(3, len(df))):
            row = df.iloc[i].tolist()
            print(f"\n行 {i}: {row[:20]}...")  # 只显示前20列

except Exception as e:
    print(f"读取失败: {e}")
    import traceback
    traceback.print_exc()
