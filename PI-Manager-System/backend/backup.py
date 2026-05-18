# -*- coding: utf-8 -*-
"""
数据库备份脚本 - 48小时自动备份
"""
import os
import sys
import shutil
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
BACKUP_INTERVAL_HOURS = 48  # 48小时备份一次
MAX_BACKUPS = 10  # 最多保留10个备份

def get_mysql_config():
    """获取MySQL配置"""
    try:
        from config import Config
        config = Config()
        return {
            'host': config.get('MYSQL_HOST', 'localhost'),
            'port': int(config.get('MYSQL_PORT', 3306)),
            'user': config.get('MYSQL_USER', 'root'),
            'password': config.get('MYSQL_PASSWORD', ''),
            'database': config.get('MYSQL_DATABASE', 'pi_manager')
        }
    except Exception as e:
        print(f"获取数据库配置失败: {e}")
        return None


def create_backup():
    """创建数据库备份"""
    config = get_mysql_config()
    if not config:
        print("无法获取数据库配置，跳过备份")
        return False
    
    try:
        import pymysql
        from pymysql import mysqldump_stream
    except ImportError:
        print("pymysql 未安装，使用 mysqldump 命令行工具")
        return create_backup_with_mysqldump(config)
    
    try:
        # 创建备份目录
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"pi_manager_backup_{timestamp}.sql")
        
        print(f"开始备份数据库: {config['database']}")
        print(f"备份文件: {backup_file}")
        
        # 连接数据库
        conn = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        
        # 使用 mysqldump 备份
        with conn.cursor() as cursor:
            # 获取所有表
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
        
        conn.close()
        
        # 执行 mysqldump
        import subprocess
        
        cmd = [
            'mysqldump',
            '-h', config['host'],
            '-P', str(config['port']),
            '-u', config['user'],
            f'-p{config["password"]}',
            '--single-transaction',
            '--quick',
            '--lock-tables=False',
            config['database']
        ]
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
            if result.returncode != 0:
                print(f"备份失败: {result.stderr.decode()}")
                return False
        
        # 压缩备份文件
        compressed_file = compress_backup(backup_file)
        
        print(f"备份成功: {compressed_file}")
        
        # 清理旧备份
        cleanup_old_backups()
        
        return True
        
    except Exception as e:
        print(f"备份失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_backup_with_mysqldump(config):
    """使用 mysqldump 命令行工具备份"""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"pi_manager_backup_{timestamp}.sql")
        
        print(f"使用 mysqldump 备份数据库: {config['database']}")
        
        import subprocess
        
        cmd = [
            'mysqldump',
            '-h', config['host'],
            '-P', str(config['port']),
            '-u', config['user'],
            f'-p{config["password"]}',
            '--single-transaction',
            '--quick',
            config['database']
        ]
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
            if result.returncode != 0:
                print(f"备份失败: {result.stderr.decode()}")
                return False
        
        compressed_file = compress_backup(backup_file)
        
        print(f"备份成功: {compressed_file}")
        
        cleanup_old_backups()
        
        return True
        
    except Exception as e:
        print(f"备份失败: {e}")
        return False


def compress_backup(sql_file):
    """压缩备份文件"""
    import gzip
    
    compressed_file = sql_file + '.gz'
    
    with open(sql_file, 'rb') as f_in:
        with gzip.open(compressed_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # 删除原始文件
    os.remove(sql_file)
    
    return compressed_file


def cleanup_old_backups():
    """清理旧备份文件"""
    try:
        if not os.path.exists(BACKUP_DIR):
            return
        
        # 获取所有备份文件
        backup_files = []
        for f in os.listdir(BACKUP_DIR):
            if f.startswith('pi_manager_backup_') and (f.endswith('.sql') or f.endswith('.sql.gz')):
                fpath = os.path.join(BACKUP_DIR, f)
                backup_files.append((fpath, os.path.getmtime(fpath)))
        
        # 按时间排序
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        # 删除超过最大数量的备份
        if len(backup_files) > MAX_BACKUPS:
            for fpath, _ in backup_files[MAX_BACKUPS:]:
                print(f"删除旧备份: {fpath}")
                os.remove(fpath)
        
        print(f"当前备份数量: {len(backup_files)}")
        
    except Exception as e:
        print(f"清理旧备份失败: {e}")


def check_and_backup():
    """检查是否需要备份"""
    last_backup_file = os.path.join(BACKUP_DIR, '.last_backup')
    
    # 检查上次备份时间
    if os.path.exists(last_backup_file):
        with open(last_backup_file, 'r') as f:
            last_backup_time = float(f.read().strip())
    else:
        last_backup_time = 0
    
    current_time = time.time()
    interval_seconds = BACKUP_INTERVAL_HOURS * 3600
    
    if current_time - last_backup_time >= interval_seconds:
        print(f"\n{'='*50}")
        print(f"开始定时备份 (距离上次: {int((current_time - last_backup_time) / 3600)} 小时)")
        print(f"{'='*50}\n")
        
        success = create_backup()
        
        if success:
            # 更新上次备份时间
            with open(last_backup_file, 'w') as f:
                f.write(str(current_time))
    else:
        next_backup_hours = int((interval_seconds - (current_time - last_backup_time)) / 3600)
        print(f"下次备份时间: {next_backup_hours} 小时后")


def run_scheduler():
    """运行备份调度器"""
    print("数据库备份调度器已启动")
    print(f"备份间隔: {BACKUP_INTERVAL_HOURS} 小时")
    print(f"备份目录: {BACKUP_DIR}")
    print(f"最大保留: {MAX_BACKUPS} 个备份")
    print("-" * 50)
    
    # 先检查是否需要立即备份
    check_and_backup()
    
    # 然后定期检查
    import threading
    
    while True:
        time.sleep(3600)  # 每小时检查一次
        check_and_backup()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库备份工具')
    parser.add_argument('--once', action='store_true', help='立即执行一次备份')
    parser.add_argument('--daemon', action='store_true', help='以后台模式运行')
    
    args = parser.parse_args()
    
    if args.once:
        create_backup()
    elif args.daemon:
        run_scheduler()
    else:
        # 默认行为：检查并备份
        check_and_backup()