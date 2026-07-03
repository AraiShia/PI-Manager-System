from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PIInvoiceItemDetailResponse(BaseModel):
    """PI订单项详细响应 - 包含所有41列所需字段"""
    
    # === 元数据 ===
    id: int
    product_id: Optional[int] = None
    
    # === A组: 基础信息 (列0-8) ===
    order_date: Optional[str] = None                   # 列0: 订单日期
    order_no: Optional[str] = None                     # 列1: ORDER NO.
    customer_code: Optional[str] = None                # 列2: 客户产品编号
    oe_number: Optional[str] = None                    # 列3: OE号
    remark: Optional[str] = None                       # 列4: 客户需求备注
    detail_desc: Optional[str] = None                  # 列5: 产品名称
    image_url: Optional[str] = None                    # 列6: 图片URL
    customer_model: Optional[str] = None               # 列7: 客户型号
    color: Optional[str] = None                        # 列8: 颜色（与 product_feature 拼接显示）
    product_feature: Optional[str] = None              # 列8: 产品特性 ⭐

    # === B组: 价格与财务 (列9-20) ===
    quantity: float = 0                                # 列9: 数量
    unit_price: float = 0                              # 列10: 报价
    total_price: float = 0                             # 列11: 合计金额
    customer_reply: Optional[str] = None               # 列12: 客户最新回复
    prepayment: Optional[float] = None                 # 列13: 客户预付款
    remaining_payment: Optional[float] = None          # 列14: 待收尾款
    estimated_usd: Optional[float] = None              # 列15: 预估美金报价
    profit_margin: Optional[float] = None              # 列16: 预估毛利率
    purchase_price: Optional[float] = None             # 列17: 采购价格
    shipping_fee: Optional[float] = None               # 列18: 运费
    misc_fee: Optional[float] = None                   # 列19: 杂费
    total_amount: Optional[float] = None               # 列20: 总金额
    
    # === C组: 供应商与采购 (列21-26) ===
    supplier_name: Optional[str] = None                # 列21: 工厂简称
    shop_url: Optional[str] = None                     # 列22: 店铺链接
    delivery_date: Optional[str] = None                # 列23: 交货日期
    received_status: Optional[str] = None              # 列24: 是否已收货
    factory_deposit: Optional[float] = None            # 列25: 工厂订金
    factory_balance: Optional[float] = None            # 列26: 工厂尾款
    
    # === D组: 物流入库 (列27-29) ===
    # 2026-06-23 收敛：与后端 CRUD 对齐，只保留 storage_status / stocked_qty（新规范），
    # 删除 warehouse_action / warehouse_qty 别名（之前任务 4 漏改 schema 导致 Pydantic
    # 序列化时把 stocked_qty/storage_status 当作未知字段丢弃，前端拿到 None）。
    storage_status: Optional[str] = None               # 列27: 入库操作（√已入库/◐部分入库/×未入库）
    stocked_qty: Optional[float] = None                # 列28: 入库数量
    packaging: Optional[str] = None                   # 列29: 包装方式（前端字段名）
    packaging_method: Optional[str] = None             # 列29: 包装方式（兼容旧字段名）

    # === E组: 产品细节 (列30-38) ===
    purchase_option_name: Optional[str] = None         # 列30: 采购选项/名称（前端字段名）
    purchase_option: Optional[str] = None              # 列30: 采购选项/名称（兼容旧字段名）
    product_detail: Optional[str] = None               # 列31: 产品细节
    factory_no: Optional[str] = None                   # 列32: 工厂编号
    carton_size: Optional[str] = None                  # 列33: 纸箱尺寸
    packing_spec: Optional[str] = None                 # 列34: 打包规格
    carton_count: Optional[int] = None                 # 列35: 箱数（"1件多箱"模式下=总箱数）
    # 🔧 2026-06-26 修复：后端 _build_item_detail_v11 会在 "1件多箱" 模式下写入
    # boxes_count=每件箱数（boxes_per_piece），但 schema 之前未声明该字段，
    # Pydantic 默认会丢弃未知字段，导致前端编辑对话框回填时拿到 None，
    # 进而 fallback 到 carton_count（=总箱数），把"件数设置"误填成总箱数
    boxes_count: Optional[int] = None                  # 列35: 箱数（"1件多箱"模式下=每件箱数）
    cartons_per_unit: Optional[int] = None            # 每件箱数（1件多箱模式）
    estimated_volume: Optional[float] = None           # 列36: 预估体积
    carton_gross_weight: Optional[float] = None        # 列37: 整箱毛重
    total_weight: Optional[float] = None               # 列38: 总重量
    
    # === F组: 其他属性 (列39-40) ===
    brand: Optional[str] = None                        # 列39: 品牌
    invoice_status: Optional[str] = None               # 列40: 开票情况
    
    class Config:
        from_attributes = True


class PIInvoiceDetailFullResponse(BaseModel):
    """PI订单完整详情响应"""
    id: int
    dept_id: str
    pi_no: str
    customer_id: int
    customer_name: Optional[str] = None
    customer_code: Optional[str] = None
    total_amount: float
    currency: str = "USD"
    status: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    items: List[PIInvoiceItemDetailResponse] = []
    payment_stages: List[dict] = []
    
    class Config:
        from_attributes = True
