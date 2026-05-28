import os
import sys

# 获取 backend 目录
backend_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(backend_dir)
data_dir = os.path.join(backend_dir, "data")
db_path = os.path.join(data_dir, "pimain.db")

print(f"数据库路径: {db_path}")

# 确认操作
confirm = input("即将删除并重置数据库，是否继续？(y/N): ")
if confirm.lower() != 'y':
    print("操作已取消")
    sys.exit(0)

# 删除数据库文件
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"已删除: {db_path}")
else:
    print("数据库文件不存在")

# 删除 WAL 和 SHM 文件（如果存在）
for ext in ['-wal', '-shm']:
    wal_path = db_path + ext
    if os.path.exists(wal_path):
        os.remove(wal_path)
        print(f"已删除: {wal_path}")

print("\n数据库已重置。重启后端服务时将自动创建新数据库。")