from app.database import SessionLocal, engine, Base
from models.user import SysUser

def init_admin_user():
    """初始化管理员用户"""
    db = SessionLocal()
    try:
        # 检查是否已存在管理员
        admin = db.query(SysUser).filter(SysUser.username == "admin").first()
        if admin:
            print("管理员用户已存在")
            print(f"用户名: {admin.username}")
            print(f"真实姓名: {admin.real_name}")
            print(f"是否管理员: {admin.is_admin}")
            return
        
        # 创建默认管理员
        admin = SysUser(
            username="admin",
            password_hash="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # admin的SHA256哈希
            real_name="系统管理员",
            email="admin@example.com",
            is_admin=True,
            is_active=True,
            dept_id="S"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("管理员用户创建成功！")
        print(f"用户名: {admin.username}")
        print(f"密码: admin")
        print(f"真实姓名: {admin.real_name}")
        print("请登录后立即修改密码！")
        
    except Exception as e:
        print(f"创建管理员用户失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")
    
    # 初始化管理员用户
    init_admin_user()
