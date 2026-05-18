"""
客户回复CRUD操作
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from models.customer_reply import CustomerReply
from schemas.customer_reply import CustomerReplyCreate, CustomerReplyUpdate


def get_customer_replies(db: Session, skip: int = 0, limit: int = 100) -> List[CustomerReply]:
    """获取所有客户回复"""
    return db.query(CustomerReply).order_by(desc(CustomerReply.reply_date)).offset(skip).limit(limit).all()


def get_customer_replies_by_pi(db: Session, pi_id: int) -> List[CustomerReply]:
    """获取某PI的所有客户回复"""
    return db.query(CustomerReply).filter(
        CustomerReply.pi_id == pi_id
    ).order_by(desc(CustomerReply.reply_date)).all()


def get_latest_reply_by_pi(db: Session, pi_id: int) -> Optional[CustomerReply]:
    """获取某PI的最新客户回复"""
    return db.query(CustomerReply).filter(
        CustomerReply.pi_id == pi_id
    ).order_by(desc(CustomerReply.reply_date)).first()


def get_customer_replies_by_customer(db: Session, customer_id: int) -> List[CustomerReply]:
    """获取某客户的所有回复"""
    return db.query(CustomerReply).filter(
        CustomerReply.customer_id == customer_id
    ).order_by(desc(CustomerReply.reply_date)).all()


def get_customer_reply(db: Session, reply_id: int) -> Optional[CustomerReply]:
    """获取单个客户回复"""
    return db.query(CustomerReply).filter(CustomerReply.id == reply_id).first()


def create_customer_reply(db: Session, reply: CustomerReplyCreate) -> CustomerReply:
    """创建客户回复"""
    db_reply = CustomerReply(
        pi_id=reply.pi_id,
        customer_id=reply.customer_id,
        reply_date=reply.reply_date,
        reply_content=reply.reply_content
    )
    db.add(db_reply)
    db.commit()
    db.refresh(db_reply)
    return db_reply


def update_customer_reply(db: Session, reply_id: int, reply: CustomerReplyUpdate) -> Optional[CustomerReply]:
    """更新客户回复"""
    db_reply = get_customer_reply(db, reply_id)
    if not db_reply:
        return None
    
    update_data = reply.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_reply, key, value)
    
    db.commit()
    db.refresh(db_reply)
    return db_reply


def delete_customer_reply(db: Session, reply_id: int) -> bool:
    """删除客户回复"""
    db_reply = get_customer_reply(db, reply_id)
    if not db_reply:
        return False
    
    db.delete(db_reply)
    db.commit()
    return True