"""
初始化产品类目数据
"""
from app.database import SessionLocal
from models.product_category import PrdProductCategory

def init_categories():
    db = SessionLocal()
    
    try:
        # 检查是否已有类目
        existing = db.query(PrdProductCategory).count()
        if existing > 0:
            print(f"[INFO] 数据库中已有 {existing} 个类目")
            return
        
        # 添加默认类目
        categories = [
            PrdProductCategory(code='01', name='刹车系统', description='刹车片、刹车盘、刹车卡钳等', sort_order=1),
            PrdProductCategory(code='02', name='滤清器', description='空气滤清器、机油滤清器、燃油滤清器等', sort_order=2),
            PrdProductCategory(code='03', name='皮带', description='正时皮带、发电机皮带、多楔带等', sort_order=3),
            PrdProductCategory(code='04', name='悬挂件', description='避震器、弹簧、下摆臂、球头等', sort_order=4),
            PrdProductCategory(code='05', name='电气件', description='火花塞、蓄电池、点火线圈等', sort_order=5),
            PrdProductCategory(code='06', name='冷却系统', description='水泵、散热器、风扇、温控开关等', sort_order=6),
            PrdProductCategory(code='07', name='点火系统', description='点火线圈、火花塞、高压线等', sort_order=7),
            PrdProductCategory(code='08', name='传动系统', description='离合器片、压板、飞轮、变速箱油等', sort_order=8),
            PrdProductCategory(code='09', name='车身件', description='保险杠、大灯、尾灯、后视镜等', sort_order=9),
            PrdProductCategory(code='10', name='其他', description='其他汽车配件', sort_order=10),
        ]
        
        for cat in categories:
            db.add(cat)
        
        db.commit()
        print(f"[SUCCESS] 已添加 {len(categories)} 个产品类目")
        
    except Exception as e:
        print(f"[ERROR] 添加类目失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("初始化产品类目数据")
    print("=" * 50)
    init_categories()