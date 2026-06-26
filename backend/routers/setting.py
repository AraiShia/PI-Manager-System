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


@router.get("/profit-margin/get")
def get_profit_margin(db: Session = Depends(get_db)):
    """获取毛利率设置"""
    setting = db.query(SysSetting).filter(SysSetting.key == "default_profit_margin").first()
    if setting:
        return {"profit_margin": float(setting.value)}
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


@router.get("/exchange-rate/get")
def get_exchange_rate(db: Session = Depends(get_db)):
    """获取汇率设置"""
    setting = db.query(SysSetting).filter(SysSetting.key == "exchange_rate").first()
    if setting:
        return {"exchange_rate": float(setting.value)}
    return {"exchange_rate": 7.24}


@router.post("/exchange-rate/set")
def set_exchange_rate(exchange_rate: float, db: Session = Depends(get_db)):
    """设置汇率"""
    if exchange_rate <= 0:
        raise HTTPException(status_code=400, detail="汇率必须大于0")
    
    setting = db.query(SysSetting).filter(SysSetting.key == "exchange_rate").first()
    
    if setting:
        setting.value = str(exchange_rate)
    else:
        setting = SysSetting(
            key="exchange_rate",
            value=str(exchange_rate),
            description="人民币兑美元汇率"
        )
        db.add(setting)
    
    db.commit()
    return {"message": "汇率已设置", "exchange_rate": exchange_rate}


@router.get("/all")
def get_all_globals(db: Session = Depends(get_db)):
    """获取所有全局变量"""
    defaults = SysSetting.get_default_settings()
    result = {}
    
    # 获取数据库中的设置
    db_settings = db.query(SysSetting).all()
    for s in db_settings:
        result[s.key] = float(s.value) if s.value else None
    
    # 补充默认值
    for key, value in defaults.items():
        if key not in result:
            result[key] = float(value) if value else None
    
    return result


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