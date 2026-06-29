# ============================================================
# 订单导入系统 - Pydantic 模型定义
# 文件：schemas/order_import.py
# 创建日期：2026-05-29
# 用途：订单导入数据验证和序列化
# ============================================================

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Union, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


# ============================================================
# 1. 基础类型定义
# ============================================================

class OrderDate(BaseModel):
    """订单日期模型"""
    value: date
    
    @classmethod
    def from_string(cls, date_str: str) -> 'OrderDate':
        """从字符串解析日期"""
        formats = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y']
        for fmt in formats:
            try:
                return cls(value=datetime.strptime(date_str, fmt).date())
            except ValueError:
                continue
        raise ValueError(f"无法解析日期: {date_str}")


class MoneyAmount(BaseModel):
    """金额模型（支持USD和RMB）"""
    amount: Decimal
    currency: str = Field(default='USD', pattern='^(USD|RMB)$')
    
    @classmethod
    def from_string(cls, amount_str: str, currency: str = 'USD') -> 'MoneyAmount':
        """从字符串解析金额"""
        # 移除货币符号和逗号
        cleaned = re.sub(r'[$,￥¥]', '', str(amount_str)).strip()
        return cls(amount=Decimal(cleaned), currency=currency)


# ============================================================
# 2. 匹配相关模型
# ============================================================

class MatchItem(BaseModel):
    """匹配项模型（用于批量匹配）"""
    customer_id: Optional[int] = Field(None, ge=1, description="客户ID")
    customer_code: Optional[str] = Field(None, min_length=1, max_length=50, description="客户产品编号")
    oe_number: Optional[str] = Field(None, max_length=100, description="OE号")
    product_name: Optional[str] = Field(None, max_length=200, description="产品名称")
    qty: Optional[int] = Field(None, ge=0, description="产品数量")
    model: Optional[str] = Field(None, max_length=100, description="产品型号（客户型号）")
    
    model_config = ConfigDict(extra='forbid')


class ProductDetail(BaseModel):
    """产品详细信息"""
    id: int = Field(..., description="产品ID")
    detail_desc: Optional[str] = Field(None, max_length=500, description="产品描述")
    oe_number: Optional[str] = Field(None, max_length=100, description="OE号")
    brand: Optional[str] = Field(None, max_length=100, description="品牌")
    unit_price: Optional[Decimal] = Field(None, ge=0, description="单价")
    currency: Optional[str] = Field(None, pattern='^(USD|RMB)$', description="货币")

    model_config = ConfigDict(from_attributes=True)


class ProductMatchResult(BaseModel):
    """产品匹配结果"""
    product_id: int = Field(..., description="产品ID")
    match_type: str = Field(..., pattern='^(exact_customer_code|oe_number|product_name)$', 
                           description="匹配类型")
    match_score: float = Field(..., ge=0, le=100, description="匹配度评分（0-100）")
    detail_desc: Optional[str] = Field(None, max_length=500, description="产品描述")
    oe_number: Optional[str] = Field(None, max_length=100, description="OE号")
    brand: Optional[str] = Field(None, max_length=100, description="品牌")
    product: Optional[ProductDetail] = Field(None, description="产品详情")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 3. 订单导入数据模型（41列）
# ============================================================

class OrderImportData(BaseModel):
    """订单导入数据模型"""
    # 基本信息（列1-5）
    order_date: date = Field(..., description="订单日期")
    pi_no: str = Field(..., min_length=5, max_length=50, description="PI号（导入时可为带?后缀的临时PI）")
    customer_code: Optional[str] = Field(None, max_length=50, description="客户产品编号")
    oe_number: Optional[str] = Field(None, max_length=100, description="OE号")
    product_desc: Optional[str] = Field(None, max_length=500, description="产品描述")
    
    # [6.0.2] [6.0.2.4] 是否为临时PI（导入时由前端写入）
    is_temp_pi: Optional[bool] = Field(False, description="是否为临时PI，导入时由前端标记")
    
    # 数量和价格（列6-10）
    quantity: int = Field(..., ge=1, description="数量")
    unit_price: Decimal = Field(..., gt=0, description="单价")
    currency: str = Field(default='USD', pattern='^(USD|RMB)$', description="货币")
    amount: Optional[Decimal] = Field(None, ge=0, description="金额")
    discount: Optional[Decimal] = Field(None, ge=0, le=100, description="折扣百分比")
    
    # 客户信息（列11-15）
    customer_id: Optional[int] = Field(None, ge=1, description="客户ID")
    customer_name: Optional[str] = Field(None, max_length=200, description="客户名称")
    contact_person: Optional[str] = Field(None, max_length=100, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    contact_email: Optional[str] = Field(None, max_length=100, description="联系邮箱")
    
    # 供应商信息（列16-20）
    supplier_id: Optional[int] = Field(None, ge=1, description="供应商ID")
    supplier_name: Optional[str] = Field(None, max_length=200, description="供应商名称")
    purchase_option: Optional[str] = Field(None, max_length=100, description="采购选项")
    factory_code: Optional[str] = Field(None, max_length=50, description="工厂编号")
    lead_time: Optional[int] = Field(None, ge=0, description="交期（天）")
    
    # 包装规格（列21-28）
    package_method: Optional[str] = Field(None, max_length=50, description="包装方式")
    package_quantity: Optional[int] = Field(None, ge=1, description="每包数量")
    carton_size_length: Optional[Decimal] = Field(None, gt=0, description="纸箱尺寸-长(cm)")
    carton_size_width: Optional[Decimal] = Field(None, gt=0, description="纸箱尺寸-宽(cm)")
    carton_size_height: Optional[Decimal] = Field(None, gt=0, description="纸箱尺寸-高(cm)")
    carton_volume: Optional[Decimal] = Field(None, ge=0, description="纸箱体积(cbm)")
    pack_spec: Optional[str] = Field(None, max_length=100, description="打包规格")
    gross_weight: Optional[Decimal] = Field(None, ge=0, description="整箱毛重(kg)")
    net_weight: Optional[Decimal] = Field(None, ge=0, description="整箱净重(kg)")
    
    # 运输信息（列29-35）
    shipping_method: Optional[str] = Field(None, max_length=50, description="运输方式")
    port_of_loading: Optional[str] = Field(None, max_length=100, description="起运港")
    port_of_discharge: Optional[str] = Field(None, max_length=100, description="目的港")
    destination: Optional[str] = Field(None, max_length=200, description="目的地")
    payment_terms: Optional[str] = Field(None, max_length=100, description="付款条件")
    delivery_date: Optional[date] = Field(None, description="交货日期")
    remarks: Optional[str] = Field(None, max_length=1000, description="备注")
    
    # 财务信息（列36-41）
    exchange_rate: Optional[Decimal] = Field(None, gt=0, description="汇率")
    estimated_cost: Optional[Decimal] = Field(None, ge=0, description="预估成本")
    profit_margin: Optional[Decimal] = Field(None, ge=0, le=100, description="毛利率(%)")
    sales_person: Optional[str] = Field(None, max_length=100, description="业务员")
    status: Optional[str] = Field(None, max_length=50, description="订单状态")
    
    model_config = ConfigDict(
        extra='allow',  # 允许额外字段，避免Excel列名不完全匹配导致报错
        str_strip_whitespace=True  # 自动去除首尾空格
    )
    
    @field_validator('pi_no')
    @classmethod
    def validate_pi_no(cls, v: str) -> str:
        """验证PI号格式（支持带?后缀的临时PI）[6.0.2]"""
        v = v.strip()
        # 允许带?后缀的临时PI（临时PI号在正式化时由后端生成）
        if not re.match(r'^PI\d{5,}?\?*$', v, re.IGNORECASE):
            raise ValueError(f"PI号格式不正确，应以'PI'开头后跟数字，例如：PI20240101001")
        return v.upper()
    
    @field_validator('customer_id', 'supplier_id')
    @classmethod
    def validate_foreign_keys(cls, v: Optional[int]) -> Optional[int]:
        """验证外键ID"""
        if v is not None and v <= 0:
            raise ValueError("ID必须大于0")
        return v
    
    @field_validator('amount', 'estimated_cost')
    @classmethod
    def calculate_amount_if_missing(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """如果金额未提供，根据数量和单价计算"""
        if v is None and info.field_name == 'amount':
            return None  # 可以在后续步骤中计算
        return v


# ============================================================
# 4. API 请求/响应模型
# ============================================================

class PreviewRequest(BaseModel):
    """文件预览请求（内部使用）"""
    file_path: str = Field(..., description="文件路径")
    max_rows: int = Field(default=10, ge=1, le=100, description="预览最大行数")


class PreviewResponse(BaseModel):
    """文件预览响应"""
    success: bool = Field(default=True, description="是否成功")
    headers: List[str] = Field(..., description="Excel表头")
    preview_rows: List[List[str]] = Field(..., description="预览数据")
    total_rows: int = Field(..., ge=0, description="Excel总行数")
    column_count: int = Field(..., ge=0, description="列数")
    mapping_suggestions: Optional[Dict[str, str]] = Field(None, description="字段映射建议")


class BatchMatchRequest(BaseModel):
    """批量匹配请求"""
    items: List[MatchItem] = Field(..., min_length=1, max_length=1000, description="匹配项列表")
    # 2026-06-23 新增：导入时静默创建 temp（未匹配行静默写 PrdCustomerProduct）
    auto_create_temporary: bool = Field(default=False, description="True 时未匹配项静默创建 temp 产品（导入场景）")
    customer_id: Optional[int] = Field(default=None, ge=1, description="客户ID（auto_create_temporary=True 时必填）")

    model_config = ConfigDict(extra='forbid')


class BatchMatchResultItem(BaseModel):
    """批量匹配结果项"""
    input: MatchItem = Field(..., description="输入数据")
    matches: List[ProductMatchResult] = Field(default=[], description="匹配结果列表")
    best_match: Optional[ProductMatchResult] = Field(None, description="最佳匹配")
    # 2026-06-23 新增：导入流程的状态/产品信息
    status: str = Field(
        default="unmatched",
        description="matched | created_temp | reused_existing | unmatched",
    )
    product_id: Optional[int] = Field(default=None, description="匹配/创建/复用后的 product_id（前端导入时直接用）")
    dedup_hit: bool = Field(default=False, description="是否因 customer_id+model 命中已存在产品")
    product: Optional[Dict[str, Any]] = Field(default=None, description="产品完整字典（前端展示用）")


class BatchMatchResponse(BaseModel):
    """批量匹配响应"""
    success: bool = Field(default=True, description="是否成功")
    results: List[BatchMatchResultItem] = Field(..., description="匹配结果列表")


class MatchRequest(BaseModel):
    """单个产品匹配请求"""
    customer_id: int = Field(..., ge=1, description="客户ID")
    customer_code: str = Field(..., min_length=1, max_length=50, description="客户产品编号")
    oe_number: Optional[str] = Field(None, max_length=100, description="OE号")
    product_name: Optional[str] = Field(None, max_length=200, description="产品名称")
    qty: Optional[int] = Field(None, ge=0, description="产品数量")
    model: Optional[str] = Field(None, max_length=100, description="产品型号（客户型号）")
    
    model_config = ConfigDict(extra='forbid')


class MatchResponse(BaseModel):
    """单个产品匹配响应"""
    success: bool = Field(default=True, description="是否成功")
    matches: List[ProductMatchResult] = Field(default=[], description="所有匹配结果")
    best_match: Optional[ProductMatchResult] = Field(None, description="最佳匹配")
    match_type: str = Field(default='no_match', description="匹配类型")


class ImportError(BaseModel):
    """导入错误信息"""
    row: int = Field(..., ge=1, description="Excel行号")
    error: str = Field(..., description="错误描述")
    suggestions: List[str] = Field(default=[], description="建议修正方案")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class ImportResponse(BaseModel):
    """订单导入响应"""
    success: bool = Field(default=True, description="是否成功")
    success_count: int = Field(default=0, ge=0, description="成功导入数量")
    failed_count: int = Field(default=0, ge=0, description="导入失败数量")
    temp_model_count: int = Field(default=0, ge=0, description="自动生成临时编号的数量")
    errors: List[ImportError] = Field(default=[], description="错误列表")
    created_orders: List[int] = Field(default=[], description="创建的订单ID列表")


class ProductSearchRequest(BaseModel):
    """产品搜索请求"""
    keyword: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量限制")
    threshold: float = Field(default=0.3, ge=0, le=1, description="相似度阈值")


class ProductSearchResponse(BaseModel):
    """产品搜索响应"""
    success: bool = Field(default=True, description="是否成功")
    data: List[ProductMatchResult] = Field(default=[], description="搜索结果")
    total: int = Field(default=0, ge=0, description="符合条件的总数")


# ============================================================
# 5. 错误响应模型
# ============================================================

class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = Field(None, description="出错的字段")
    message: str = Field(..., description="错误信息")
    value: Optional[Any] = Field(None, description="导致错误的具体值")


class ErrorResponse(BaseModel):
    """通用错误响应"""
    success: bool = Field(default=False, description="是否成功")
    error: str = Field(..., description="错误描述")
    error_code: str = Field(..., description="错误代码")
    details: Optional[List[ErrorDetail]] = Field(None, description="详细错误信息")
    
    @classmethod
    def invalid_file_format(cls, details: Optional[str] = None) -> 'ErrorResponse':
        return cls(
            success=False,
            error=details or "文件格式错误，请上传 .xlsx 或 .xls 格式的Excel文件",
            error_code="INVALID_FILE_FORMAT"
        )
    
    @classmethod
    def file_too_large(cls, size_mb: float) -> 'ErrorResponse':
        return cls(
            success=False,
            error=f"文件大小超出限制（最大10MB），当前文件：{size_mb:.2f}MB",
            error_code="FILE_TOO_LARGE"
        )
    
    @classmethod
    def validation_error(cls, errors: List[ErrorDetail]) -> 'ErrorResponse':
        return cls(
            success=False,
            error="数据校验失败",
            error_code="VALIDATION_ERROR",
            details=errors
        )


# ============================================================
# 6. 工具函数
# ============================================================

def parse_order_import_row(row_data: Dict[str, Any]) -> OrderImportData:
    """
    解析一行订单导入数据
    
    Args:
        row_data: 原始行数据（字典形式）
    
    Returns:
        OrderImportData: 验证后的订单数据
    
    Raises:
        ValidationError: 数据验证失败
    """
    return OrderImportData(**row_data)


def validate_excel_file(filename: str) -> bool:
    """
    验证Excel文件格式
    
    Args:
        filename: 文件名
    
    Returns:
        bool: 是否为有效的Excel文件
    """
    valid_extensions = ['.xlsx', '.xls']
    return any(filename.lower().endswith(ext) for ext in valid_extensions)


# ============================================================
# 7. 字段映射配置（供参考）
# ============================================================

# Excel表头到数据库字段的映射
EXCEL_HEADER_MAPPING = {
    '订单日期': 'order_date',
    'ORDER NO.': 'pi_no',
    '客户产品编号': 'customer_code',
    '客户型号': 'model',  # 2026-06-10: 用于匹配 PrdProductCustomer.model_code
    'OE号': 'oe_number',
    '产品描述': 'product_desc',
    '产品名称': 'detail_desc',
    '客户备注': 'remark',
    '备注': 'remark',
    '客户需求/产品备注': 'remark',
    '客户型号(Model)': 'customer_model',
    '产品特性': 'product_feature',
    '产品细节': 'product_detail',
    '数量': 'quantity',
    'QTY': 'quantity',
    'QUANTITY': 'quantity',
    '单价': 'unit_price',
    '报价(USD/RMB)': 'unit_price',
    # B组: 价格与财务
    '客户预付款': 'customer_prepayment',
    '待收尾款': 'remaining_payment',
    '采购价格': 'purchase_price',
    '运费': 'shipping_fee',
    '杂费': 'misc_fee',
    '总金额': 'total_order_amount',
    # C组: 供应商与采购
    '工厂简称': 'supplier_name',
    '供应商名称': 'supplier_name',
    '店铺链接': 'shop_url',
    '交货日期': 'delivery_date',
    '工厂编号': 'factory_code',
    '供应商ID': 'supplier_id',
    '是否已收货': 'storage_status',
    '入库数量': 'stocked_qty',
    '工厂订金': 'factory_deposit',
    '工厂尾款': 'factory_balance',
    # D/E组: 包装与采购选项
    '包装方式': 'packaging',
    '采购选项': 'purchase_option_name',
    '采购选项/名称': 'purchase_option_name',
    '纸箱尺寸': 'carton_size',
    '纸箱长': 'carton_size_length',
    '纸箱宽': 'carton_size_width',
    '纸箱高': 'carton_size_height',
    '打包规格': 'pack_spec',
    '箱数': 'carton_count',
    '毛重(kg)': 'carton_gross_weight',
    '整箱毛重': 'carton_gross_weight',
    # F组: 其他
    '品牌': 'brand',
    '开票情况': 'invoice_status',
    # 货币和其他兼容字段
    '货币': 'currency',
    '金额': 'amount',
    '折扣': 'discount',
    '客户ID': 'customer_id',
    '客户名称': 'customer_name',
    '联系人': 'contact_person',
    '联系电话': 'contact_phone',
    '联系邮箱': 'contact_email',
    '交期': 'lead_time',
    '每包数量': 'pack_spec',
    '纸箱体积': 'carton_volume',
    '毛重': 'carton_gross_weight',
    '净重': 'net_weight',
    '运输方式': 'shipping_method',
    '起运港': 'port_of_loading',
    '目的港': 'port_of_discharge',
    '目的地': 'destination',
    '付款条件': 'payment_terms',
    '汇率': 'exchange_rate',
    '预估成本': 'estimated_cost',
    '毛利率': 'profit_margin',
    '业务员': 'sales_person',
    '订单状态': 'status',
}

# 反向映射（数据库字段到Excel表头）
FIELD_TO_EXCEL_HEADER = {v: k for k, v in EXCEL_HEADER_MAPPING.items()}


# ============================================================
# 8. 常用校验规则
# ============================================================

class ValidationRules:
    """常用校验规则集合"""
    
    # PI号格式：PI + 至少5位数字
    PI_NO_PATTERN = re.compile(r'^PI\d{5,}$', re.IGNORECASE)
    
    # 邮箱格式
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # 电话格式（支持国际电话）
    PHONE_PATTERN = re.compile(r'^[\d\s\-\+\(\)]+$')
    
    @staticmethod
    def validate_email(email: str) -> bool:
        return bool(ValidationRules.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        return bool(ValidationRules.PHONE_PATTERN.match(phone))
    
    @staticmethod
    def validate_pi_no(pi_no: str) -> bool:
        return bool(ValidationRules.PI_NO_PATTERN.match(pi_no))