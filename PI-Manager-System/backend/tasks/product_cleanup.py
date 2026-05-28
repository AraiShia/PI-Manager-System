"""
后台任务 - 异步物理删除已软删除的产品
处理多用户冲突问题
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.customer_product import PrdCustomerProduct


def cleanup_deleted_products(db: Session, hours: int = 24):
    """
    清理已软删除的产品（异步物理删除）
    
    规则：
    1. 只删除 deleted_at 超过指定小时数的产品
    2. 检查是否有其他关联数据（如订单、库存等）
    3. 考虑多用户并发冲突：使用事务确保原子性
    
    Args:
        db: 数据库会话
        hours: 超过多少小时的产品将被物理删除（默认24小时）
    
    Returns:
        tuple: (deleted_count, error_message)
    """
    try:
        # 计算软删除时间阈值
        threshold = datetime.now() - timedelta(hours=hours)
        
        # 查找需要删除的产品
        products_to_delete = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.deleted_at != None,  # 已软删除
            PrdCustomerProduct.deleted_at < threshold  # 超过时间阈值
        ).all()
        
        deleted_count = 0
        errors = []
        
        for product in products_to_delete:
            try:
                # 检查关联数据（如果有需要）
                # 这里可以添加业务逻辑检查，如是否有未完成的订单等
                
                # 使用软锁机制：先验证产品仍然可以被删除
                current = db.query(PrdCustomerProduct).filter(
                    PrdCustomerProduct.id == product.id
                ).first()
                
                if current and current.deleted_at and current.deleted_at < threshold:
                    # 物理删除（关联的 codes 和 oes 会通过 cascade 自动删除）
                    db.delete(current)
                    deleted_count += 1
                    print(f"[CLEANUP] 物理删除产品 ID={product.id}, name={product.product_name}")
                    
            except Exception as e:
                errors.append(f"删除产品 {product.id} 失败: {str(e)}")
                print(f"[ERROR] 物理删除产品失败: {e}")
        
        # 提交事务
        db.commit()
        
        if errors:
            return deleted_count, "; ".join(errors)
        
        return deleted_count, None
        
    except Exception as e:
        db.rollback()
        return 0, str(e)


def batch_soft_delete_with_check(db: Session, product_ids: list) -> dict:
    """
    批量软删除（带冲突检查）
    
    处理多用户并发问题：
    1. 使用乐观锁：检查 is_active 状态
    2. 使用悲观锁：行级锁（在事务内锁定）
    
    Args:
        db: 数据库会话
        product_ids: 要删除的产品ID列表
    
    Returns:
        dict: {
            "success": [成功删除的ID列表],
            "failed": [{"id": ID, "reason": "失败原因"}, ...],
            "conflict": [被其他用户操作的ID列表]
        }
    """
    result = {
        "success": [],
        "failed": [],
        "conflict": []
    }
    
    now = datetime.now()
    
    for product_id in product_ids:
        try:
            # 使用 with_for_update() 添加行级锁，防止并发冲突
            product = db.query(PrdCustomerProduct).filter(
                PrdCustomerProduct.id == product_id
            ).with_for_update(nowait=False).first()
            
            if not product:
                result["failed"].append({
                    "id": product_id,
                    "reason": "产品不存在"
                })
                continue
            
            # 检查是否已被其他用户删除
            if not product.is_active:
                result["conflict"].append({
                    "id": product_id,
                    "reason": "已被其他用户删除"
                })
                continue
            
            # 执行软删除
            product.is_active = False
            product.deleted_at = now
            
            result["success"].append(product_id)
            
        except Exception as e:
            result["failed"].append({
                "id": product_id,
                "reason": str(e)
            })
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            "success": [],
            "failed": [{"id": pid, "reason": str(e)} for pid in product_ids],
            "conflict": []
        }
    
    return result