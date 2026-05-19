"""
系统设置API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.database import get_db
from models.setting import SysSetting

router = APIRouter(prefix="/api/settings", tags=["系统设置"])


class SettingCreate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str]
    description: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[SettingResponse])
def get_all_settings(db: Session = Depends(get_db)):
    """获取所有设置"""
    settings = db.query(SysSetting).all()
    return settings


@router.get("/{key}", response_model=SettingResponse)
def get_setting(key: str, db: Session = Depends(get_db)):
    """获取指定设置"""
    setting = db.query(SysSetting).filter(SysSetting.key == key).first()
    if not setting:
        # 返回默认值
        defaults = SysSetting.get_default_settings()
        if key in defaults:
            return {"id": None, "key": key, "value": defaults[key], "description": None}
        raise HTTPException(status_code=404, detail="设置不存在")
    return setting


@router.put("/{key}")
def update_setting(key: str, setting: SettingUpdate, db: Session = Depends(get_db)):
    """更新或创建设置"""
    db_setting = db.query(SysSetting).filter(SysSetting.key == key).first()
    
    if db_setting:
        db_setting.value = setting.value
    else:
        db_setting = SysSetting(
            key=key,
            value=setting.value,
            description=f"用户设置的 {key}"
        )
        db.add(db_setting)
    
    db.commit()
    return {"message": "设置已更新", "key": key, "value": setting.value}


@router.get("/profit-margin/get")
def get_profit_margin(db: Session = Depends(get_db)):
    """获取毛利率设置"""
    setting = db.query(SysSetting).filter(SysSetting.key == "default_profit_margin").first()
    if setting:
        return {"profit_margin": float(setting.value)}
    
    # 返回默认值
    return {"profit_margin": 25.0}


@router.post("/profit-margin/set")
def set_profit_margin(profit_margin: float, db: Session = Depends(get_db)):
    """设置毛利率"""
    if profit_margin < 0 or profit_margin > 100:
        raise HTTPException(status_code=400, detail="毛利率必须在0-100之间")
    
    setting = db.query(SysSetting).filter(SysSetting.key == "default_profit_margin").first()
    
    if setting:
        setting.value = str(profit_margin)
    else:
        setting = SysSetting(
            key="default_profit_margin",
            value=str(profit_margin),
            description="默认毛利率（百分比）"
        )
        db.add(setting)
    
    db.commit()
    return {"message": "毛利率已设置", "profit_margin": profit_margin}