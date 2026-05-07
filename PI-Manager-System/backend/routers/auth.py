from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets

from app.database import get_db
from models.user import SysUser

router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

# 密码哈希函数
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# 生成Token
def generate_token() -> str:
    return secrets.token_urlsafe(32)

# 获取当前用户
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> SysUser:
    token = credentials.credentials
    user = db.query(SysUser).filter(SysUser.username == token).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证信息"
        )
    return user

# 获取当前用户（可选）
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> Optional[SysUser]:
    if not credentials:
        return None
    try:
        token = credentials.credentials
        user = db.query(SysUser).filter(SysUser.username == token).first()
        if not user or not user.is_active:
            return None
        return user
    except:
        return None

# 获取当前管理员
async def get_current_admin(
    current_user: SysUser = Depends(get_current_user)
) -> SysUser:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

@router.post("/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(SysUser).filter(
        SysUser.username == username,
        SysUser.password_hash == hash_password(password),
        SysUser.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "token": user.username,  # 简化实现，使用用户名作为token
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "is_admin": user.is_admin,
            "dept_id": user.dept_id
        }
    }

@router.get("/me")
async def get_me(current_user: SysUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "is_admin": current_user.is_admin,
        "dept_id": current_user.dept_id,
        "last_login": current_user.last_login
    }

@router.post("/users")
async def create_user(
    username: str,
    password: str,
    real_name: str,
    is_admin: bool = False,
    dept_id: Optional[str] = None,
    current_user: SysUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # 检查用户名是否已存在
    existing = db.query(SysUser).filter(SysUser.username == username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    user = SysUser(
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        is_admin=is_admin,
        dept_id=dept_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"message": "用户创建成功", "user_id": user.id}

@router.get("/users")
async def get_users(
    current_user: SysUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(SysUser).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "real_name": u.real_name,
            "email": u.email,
            "phone": u.phone,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "dept_id": u.dept_id,
            "last_login": u.last_login,
            "created_at": u.created_at
        }
        for u in users
    ]

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    real_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    is_admin: Optional[bool] = None,
    is_active: Optional[bool] = None,
    dept_id: Optional[str] = None,
    current_user: SysUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if real_name is not None:
        user.real_name = real_name
    if email is not None:
        user.email = email
    if phone is not None:
        user.phone = phone
    if is_admin is not None:
        user.is_admin = is_admin
    if is_active is not None:
        user.is_active = is_active
    if dept_id is not None:
        user.dept_id = dept_id
    
    db.commit()
    db.refresh(user)
    
    return {"message": "用户更新成功"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: SysUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "用户删除成功"}
