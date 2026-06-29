# ============================================================
# 订单导入API路由
# 文件：routers/order_import.py
# 创建日期：2026-05-29
# 用途：订单导入相关API端点
# ============================================================

import logging
import json
logger = logging.getLogger(__name__)

from fastapi import APIRouter, File, UploadFile, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import io

from app.database import get_db
from schemas.order_import import (
    PreviewResponse,
    ImportResponse,
    BatchMatchRequest,
    BatchMatchResponse,
    BatchMatchResultItem,
    MatchRequest,
    MatchResponse,
    ProductSearchRequest,
    ProductSearchResponse,
    ErrorResponse,
    ImportError,
    ProductMatchResult,
    MatchItem,
    ProductDetail,
    EXCEL_HEADER_MAPPING,
)
from services.product_matcher import ProductMatcher
from services.excel_parser import ExcelParser


router = APIRouter(prefix="/orders", tags=["订单导入"])
product_router = APIRouter(prefix="/products", tags=["产品匹配"])


# ============================================================
# 1. 文件预览接口
# ============================================================

@router.post("/preview", response_model=PreviewResponse)
async def preview_order_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    预览 Excel 文件内容
    - 上传 Excel 文件
    - 返回表头和前10行数据预览
    - 提供字段映射建议
    """
    # 验证文件格式
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式错误，请上传 .xlsx 或 .xls 格式的Excel文件"
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 检查文件大小（最大10MB）
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="文件大小超出限制（最大10MB）"
            )
        
        # 解析Excel
        parser = ExcelParser()
        result = parser.parse_preview(content, max_rows=99999)
        
        return PreviewResponse(
            success=True,
            headers=result['headers'],
            preview_rows=result['preview_rows'],
            total_rows=result['total_rows'],
            column_count=result['column_count'],
            mapping_suggestions=_suggest_field_mapping(result['headers'])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _suggest_field_mapping(headers: List[str]) -> dict:
    """根据Excel表头建议字段映射"""
    suggestions = {}
    for header in headers:
        if header in EXCEL_HEADER_MAPPING:
            suggestions[header] = EXCEL_HEADER_MAPPING[header]
    return suggestions


# ============================================================
# 2. 订单导入接口
# ============================================================

@router.post("/import", response_model=ImportResponse)
async def import_orders(
    file: UploadFile = File(...),
    auto_match: bool = Query(True, description="是否自动匹配产品"),
    customer_id: int = Query(None, description="客户ID"),
    db: Session = Depends(get_db)
):
    """
    批量导入订单
    - 解析Excel文件（第一行为表头）
    - 整个Excel创建一个PI订单
    - Excel每行作为一个PI Item
    """
    import_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"[🚀 订单导入开始] 时间={import_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"[📁 文件信息] 文件名={file.filename}, 客户ID={customer_id}, 自动匹配={auto_match}")
    logger.info("=" * 80)

    if not file.filename.endswith(('.xlsx', '.xls')):
        logger.error(f"[❌ 格式错误] 文件格式不支持: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="文件格式错误，请上传 .xlsx 或 .xls 格式的Excel文件"
        )

    try:
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"[✅ 文件读取成功] 大小={len(content)} bytes ({file_size_mb:.2f} MB)")

        parser = ExcelParser()
        rows = parser.parse_all(content)

        logger.info(f"[✅ Excel解析完成] 总行数={len(rows)}, 数据行数={len(rows)-1 if rows else 0}")

        if not rows or len(rows) <= 1:
            logger.error("[❌ 空数据] Excel文件为空或无有效数据")
            raise HTTPException(status_code=400, detail="Excel文件为空或无有效数据")

        errors = []
        created_order_ids = []

        product_matcher = ProductMatcher(db)
        logger.info(f"[🔍 产品匹配器初始化完成]")

        headers = rows[0]
        header_mapping = {}
        for col_idx, header in enumerate(headers):
            if header in EXCEL_HEADER_MAPPING:
                header_mapping[col_idx] = EXCEL_HEADER_MAPPING[header]
                logger.debug(f"  [表头映射] 列{col_idx}: '{header}' → '{EXCEL_HEADER_MAPPING[header]}'")
            elif header.upper() in ('QTY', '数量', 'QUANTITY'):
                header_mapping[col_idx] = 'qty'
                logger.debug(f"  [表头映射-QTY] 列{col_idx}: '{header}' → 'qty'")
            elif header.upper() in ('MODEL', '客户型号'):
                header_mapping[col_idx] = 'model'
                logger.debug(f"  [表头映射-MODEL] 列{col_idx}: '{header}' → 'model'")
            elif header.upper() in ('客户产品编号',):
                header_mapping[col_idx] = 'customer_code'
                logger.debug(f"  [表头映射] 列{col_idx}: '{header}' → 'customer_code'")

        logger.info(f"[📋 表头识别结果]")
        logger.info(f"  原始表头: {headers}")
        logger.info(f"  字段映射: {header_mapping}")
        logger.info(f"  识别到关键字段: Model={'✓' if 'model' in header_mapping.values() else '✗'}, QTY={'✓' if 'qty' in header_mapping.values() else '✗'}")

        all_items = []
        success_rows = 0
        failed_rows = 0
        temp_model_count = 0  # 统计自动生成的临时编号数量

        for row_index, row in enumerate(rows[1:], start=2):
            try:
                row_start_time = datetime.now()
                logger.info(f"\n[📝 处理第{row_index}行] 开始处理...")
                logger.debug(f"  原始数据: {row[:min(10, len(row))]}...")

                order_data, parse_errors = _transform_row_data(row, header_mapping, row_index)

                if parse_errors:
                    logger.warning(f"[⚠️ 第{row_index}行解析错误] 错误数={len(parse_errors)}")
                    for error in parse_errors:
                        logger.warning(f"    错误详情: {error}")
                        errors.append(ImportError(
                            row=row_index,
                            error=error,
                            suggestions=["检查Excel数据格式"]
                        ))
                    failed_rows += 1
                    continue

                # 输出关键字段值
                logger.info(f"  [字段解析结果]")
                logger.info(f"    MODEL: {order_data.get('model')}")
                logger.info(f"    QTY: {order_data.get('qty')}")
                logger.info(f"    OE号: {order_data.get('oe_number')}")
                logger.info(f"    客户编号: {order_data.get('customer_code')}")

                if auto_match:
                    logger.info(f"  [产品自动匹配] 开始...")
                    match_start = datetime.now()
                    _auto_match_entities(order_data, product_matcher, customer_id)
                    match_duration = (datetime.now() - match_start).total_seconds()
                    logger.info(f"  [产品匹配完成] 耗时={match_duration:.3f}s, 结果: product_id={order_data.get('product_id')}")

                    # 匹配状态详情
                    if order_data.get('product_id'):
                        logger.info(f"    ✓ 匹配成功: product_id={order_data.get('product_id')}")
                    elif order_data.get('model'):
                        logger.info(f"    ⚠ 未匹配到产品，将创建临时产品: model={order_data.get('model')}")
                    else:
                        logger.warning(f"    ✗ 无MODEL字段，无法匹配")

                all_items.append(order_data)
                success_rows += 1
                if order_data.get('_temp_model'):
                    temp_model_count += 1
                row_duration = (datetime.now() - row_start_time).total_seconds()
                logger.info(f"  [✅ 第{row_index}行处理完成] 耗时={row_duration:.3f}s, product_id={order_data.get('product_id')}")

            except Exception as e:
                row_duration = (datetime.now() - row_start_time).total_seconds()
                logger.error(f"[❌ 第{row_index}行异常] 耗时={row_duration:.3f}s, 错误={str(e)}", exc_info=True)
                errors.append(ImportError(
                    row=row_index,
                    error=str(e),
                    suggestions=_get_suggestions(str(e))
                ))
                failed_rows += 1

        total_duration = (datetime.now() - import_time).total_seconds()
        logger.info(f"\n[📊 数据处理统计]")
        logger.info(f"  总耗时: {total_duration:.3f}s")
        logger.info(f"  成功行数: {success_rows}")
        logger.info(f"  失败行数: {failed_rows}")
        logger.info(f"  有效Items: {len(all_items)}")

        if not all_items:
            logger.error("[❌ 无有效数据] 所有行解析失败")
            return ImportResponse(
                success=False,
                success_count=0,
                failed_count=len(rows) - 1,
                temp_model_count=0,
                errors=errors,
                created_orders=[]
            )

        try:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"[🏭 创建PI订单流程开始]")
            logger.info(f"  customer_id: {customer_id}")
            logger.info(f"  items数量: {len(all_items)}")

            pi_create_start = datetime.now()
            pi = _create_pi_order(all_items, customer_id, db)
            pi_create_duration = (datetime.now() - pi_create_start).total_seconds()

            logger.info(f"[✅ PI订单创建函数返回成功]")
            logger.info(f"  PI_ID: {pi.id}")
            logger.info(f"  PI_NO: {pi.pi_no}")
            logger.info(f"  创建耗时: {pi_create_duration:.3f}s")
            logger.info(f"  Items数量: {len(pi.items) if hasattr(pi, 'items') else 'N/A'}")

            logger.info(f"[💾 执行数据库提交 db.commit()]")
            db.commit()
            logger.info(f"[✅ 提交成功]")

            logger.info(f"[🔄 刷新PI对象 db.refresh(pi)]")
            db.refresh(pi)
            logger.info(f"[✅ 刷新成功] pi_id={pi.id}, pi_no={pi.pi_no}")

            created_order_ids.append(pi.id)
            success_count = 1
            failed_count = len(rows) - 1 - len(all_items)

            total_duration_final = (datetime.now() - import_time).total_seconds()
            logger.info(f"\n{'=' * 80}")
            logger.info(f"[🎉 订单导入完成]")
            logger.info(f"  最终PI_ID: {pi.id}")
            logger.info(f"  最终PI_NO: {pi.pi_no}")
            logger.info(f"  成功Items: {success_rows}")
            logger.info(f"  失败Items: {failed_rows}")
            logger.info(f"  总耗时: {total_duration_final:.3f}s")
            logger.info(f"{'=' * 80}")

            return ImportResponse(
                success=True,
                success_count=success_count,
                failed_count=failed_count,
                errors=errors,
                created_orders=created_order_ids
            )
        except Exception as e:
            logger.error(f"[导入] 创建PI失败: {e}", exc_info=True)
            logger.info(f"[导入] 执行db.rollback()")
            db.rollback()
            logger.info(f"[导入] db.rollback() 完成")
            # 2026-06-10: 修复 -- row 必须 ≥1，使用 row=1 避免触发 schema 验证错误
            return ImportResponse(
                success=False,
                success_count=0,
                failed_count=max(0, len(rows) - 1),
                temp_model_count=0,
                errors=[ImportError(row=1, error=str(e), suggestions=["联系管理员"])],
                created_orders=[]
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _transform_row_data(row: List[str], header_mapping: dict, row_index: int = 0) -> tuple[dict, list]:
    """将Excel行数据转换为订单数据（基于表头动态映射）

    Args:
        row: Excel行数据
        header_mapping: 表头到字段的映射字典
            - MODEL/客户型号 -> model (匹配 PrdCustomerProduct.customer_model)
            - QTY/数量/QUANTITY -> qty (匹配数量)
        row_index: 行号（用于生成临时编号）

    Returns:
        tuple: (data_dict, errors_list)

    🔧 2026-06-22 升级：所有 41 列字段直接存入 pi_proforma_invoice_item 主表
    🔧 2026-06-29 升级：缺少 Model 时自动生成临时编号 TP+YYMMDD+序号
    """
    import random
    import string
    errors = []
    data = {}
    generated_temp_model = False

    for col_idx, value in enumerate(row):
        if col_idx >= len(header_mapping):
            continue

        field_name = list(header_mapping.values())[col_idx]

        # === A组: 基础信息 (Col 0-9) ===
        if field_name == 'order_date':
            data['order_date'] = _parse_date(value)
        elif field_name == 'pi_no':
            data['pi_no'] = value.strip() if value else None
        elif field_name == 'customer_code':
            data['customer_code'] = value.strip() if value else None
        elif field_name == 'oe_number':
            data['oe_number'] = value.strip() if value else None
        elif field_name == 'remark' or field_name == 'remarks':
            data['remark'] = value.strip() if value else None
        elif field_name == 'product_desc' or field_name == 'detail_desc':
            data['detail_desc'] = value.strip() if value else None
        elif field_name == 'customer_model':
            data['customer_model'] = value.strip() if value else None
        elif field_name == 'product_feature':
            data['product_feature'] = value.strip() if value else None
        elif field_name == 'qty' or field_name == 'quantity':
            qty = _parse_int(value) if value not in (None, "", 0) else None
            if qty is not None and qty <= 0:
                errors.append(f"QTY 必须大于0: {value}")
            data['quantity'] = qty
        elif field_name == 'unit_price':
            data['unit_price'] = _parse_decimal(value) if value else Decimal('0')

        # === B组: 价格与财务 (Col 13-20) ===
        elif field_name == 'customer_prepayment':
            data['customer_prepayment'] = _parse_decimal(value) if value else None
        elif field_name == 'remaining_payment':
            data['remaining_payment'] = _parse_decimal(value) if value else None
        elif field_name == 'purchase_price':
            data['purchase_price'] = _parse_decimal(value) if value else None
        elif field_name == 'shipping_fee':
            data['shipping_fee'] = _parse_decimal(value) if value else None
        elif field_name == 'misc_fee':
            data['misc_fee'] = _parse_decimal(value) if value else None
        elif field_name == 'total_order_amount':
            data['total_order_amount'] = _parse_decimal(value) if value else None

        # === C组: 供应商与采购 (Col 21-26) ===
        elif field_name == 'supplier_name':
            data['supplier_name'] = value.strip() if value else None
        elif field_name == 'shop_url':
            data['shop_url'] = value.strip() if value else None
        elif field_name == 'delivery_date':
            data['delivery_date'] = _parse_date(value)
        elif field_name == 'supplier_id':
            try:
                if value not in (None, ""):
                    data['supplier_id'] = int(str(value).strip())
            except (ValueError, TypeError):
                pass
        elif field_name == 'factory_code':
            data['factory_code'] = value.strip() if value else None
        elif field_name == 'storage_status':
            data['storage_status'] = value.strip() if value else None
        elif field_name == 'stocked_qty':
            data['stocked_qty'] = _parse_decimal(value) if value else None
        elif field_name == 'factory_deposit':
            data['factory_deposit'] = _parse_decimal(value) if value else None
        elif field_name == 'factory_balance':
            data['factory_balance'] = _parse_decimal(value) if value else None

        # === D/E组: 包装与采购选项 (Col 29-30, 33-35, 37) ===
        elif field_name == 'packaging' or field_name == 'package_method':
            data['packaging'] = value.strip() if value else None
        elif field_name == 'purchase_option_name' or field_name == 'purchase_option':
            data['purchase_option_name'] = value.strip() if value else None
        elif field_name == 'product_detail':
            data['product_detail'] = value.strip() if value else None
        elif field_name == 'carton_size':
            data['carton_size'] = value.strip() if value else None
        elif field_name == 'carton_size_length':
            data['carton_length_cm'] = _parse_decimal(value) if value else None
        elif field_name == 'carton_size_width':
            data['carton_width_cm'] = _parse_decimal(value) if value else None
        elif field_name == 'carton_size_height':
            data['carton_height_cm'] = _parse_decimal(value) if value else None
        elif field_name == 'pack_spec' or field_name == 'package_quantity':
            data['pack_spec'] = value.strip() if value else None
        elif field_name == 'carton_count':
            try:
                data['carton_count'] = int(float(str(value).strip())) if value else None
            except (ValueError, TypeError):
                data['carton_count'] = None
        elif field_name == 'carton_gross_weight' or field_name == 'gross_weight':
            data['carton_gross_weight'] = _parse_decimal(value) if value else None

        # === F组: 其他属性 (Col 39-40) ===
        elif field_name == 'brand':
            data['brand'] = value.strip() if value else None
        elif field_name == 'invoice_status':
            data['invoice_status'] = value.strip() if value else None

        # === 兼容旧字段名 ===
        elif field_name == 'model':
            data['model'] = value.strip() if value else None

    # 缺少 customer_model 时自动生成临时编号 TP+YYMMDD+随机2位
    if not data.get('customer_model'):
        today = datetime.now()
        date_part = today.strftime('%y%m%d')
        rand1 = random.choice(string.ascii_uppercase)
        rand2 = random.choice(string.ascii_uppercase)
        seq = str(row_index).zfill(2) if row_index else '01'
        data['customer_model'] = f"TP{date_part}{rand1}{rand2}{seq}"
        generated_temp_model = True
        data['_temp_model'] = True  # 标记，供后续状态灯使用

    return data, errors


def _parse_date(value: str) -> Optional[date]:
    """解析日期"""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
    except:
        try:
            return datetime.strptime(str(value).strip(), '%Y/%m/%d').date()
        except:
            return None


def _parse_int(value: str) -> int:
    """解析整数"""
    try:
        return int(float(str(value).replace(',', '').strip()))
    except:
        return 0


def _parse_decimal(value: str) -> Decimal:
    """解析小数"""
    try:
        cleaned = str(value).replace(',', '').replace('$', '').replace('¥', '').strip()
        return Decimal(cleaned)
    except:
        return Decimal('0')


def _auto_match_entities(data: dict, product_matcher: ProductMatcher, customer_id: int = None):
    """自动匹配产品（根据 Model 列匹配 PrdCustomerProduct.customer_model）
    匹配不到时自动创建临时产品

    🔧 2026-06-22 修复：同时支持 'model' 和 'customer_model' 字段
    """
    # 🔧 2026-06-22 修复：兼容两种字段名 'model' 和 'customer_model'
    model_code = data.get('model') or data.get('customer_model')

    logger.info(f"[导入匹配] 开始匹配 - model_code={model_code}, customer_id={customer_id}")
    logger.info(f"[导入匹配] 原始数据: {data}")
    
    if not customer_id:
        logger.warning(f"[导入匹配] 跳过 - customer_id={customer_id}")
        return
    
    db = product_matcher.db
    
    # Phase 5: 直接查 prd_customer_product（customer_id + customer_model 唯一）
    from models.customer_product import PrdCustomerProduct

    # 2026-06-29: 有 Model 时才尝试匹配已有产品，无 Model 时直接创建临时产品
    if model_code:
        logger.info(f"[导入匹配] 查询 PrdCustomerProduct - customer_id={customer_id}, model_code='{model_code}'")

        match = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.customer_id == customer_id,
            PrdCustomerProduct.customer_model == model_code
        ).first()

        if match:
            logger.info(f"[导入匹配] 匹配成功 - product_id={match.id}")
            data['product_id'] = match.id
            return

        logger.warning(f"[导入匹配] 未找到匹配，开始创建临时产品 - model_code='{model_code}'")
    else:
        logger.warning(f"[导入匹配] 无 Model，直接创建临时产品")

    # 2026-06-29: 优先使用导入的 Model 作为客户型号，无 Model 时自动生成 TP + 日期 + 随机字符
    import random
    import string
    if model_code:
        temp_code = model_code
    else:
        date_str = datetime.now().strftime("%y%m%d")
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
        temp_code = f"TP{date_str}{random_chars}"

    # Phase 5: 创建 PrdCustomerProduct 临时产品（is_temporary=1）
    # 2026-06-23 修复：统一 product_name 和 detail_desc，避免产品管理列表与订单详情表显示不一致
    # 2026-06-29: customer_model = customer_product_code = temp_code
    temp_name = f"临时产品-{temp_code}"
    temp_product = PrdCustomerProduct(
        customer_id=customer_id,
        customer_model=temp_code,
        customer_product_code=temp_code,
        detail_desc=temp_name,
        product_name=temp_name,
        is_temporary=True,
    )
    db.add(temp_product)
    db.flush()

    logger.info(f"[导入匹配] 临时产品创建成功 - id={temp_product.id}, code={temp_code}")

    data['product_id'] = temp_product.id
    logger.info(f"[导入匹配] 完成 - 最终product_id={temp_product.id}")


def _create_pi_order(items: list, customer_id: int, db: Session):
    """创建PI订单（一个Excel = 一个PI，多行 = 多个Items）"""
    from models.pi import PiProformaInvoice, PiProformaInvoiceItem
    from models.customer import CrmCustomer
    from models.customer_product import PrdCustomerProduct
    from utils.number_generator import NumberGenerator

    create_start = datetime.now()
    logger.info(f"\n{'─' * 80}")
    logger.info(f"[🏭 PI订单创建函数开始] _create_pi_order()")
    logger.info(f"  参数: customer_id={customer_id}, items数量={len(items)}")
    logger.info(f"{'─' * 80}")

    if not customer_id:
        logger.error("[❌ 错误] 缺少customer_id")
        raise ValueError("缺少客户ID")

    logger.info(f"[步骤1/6] 查询客户信息 - customer_id={customer_id}")
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if not customer:
        logger.error(f"[❌ 错误] 客户不存在: customer_id={customer_id}")
        raise ValueError("客户不存在")

    logger.info(f"[✅ 客户查询成功]")
    logger.info(f"  客户ID: {customer.id}")
    logger.info(f"  客户名称: {customer.customer_name}")
    logger.info(f"  客户编号: {customer.customer_code}")
    logger.info(f"  部门ID: {customer.dept_id}")

    dept_id = customer.dept_id or 'D01'

    try:
        logger.info(f"[步骤2/6] 生成PI号 - dept_id={dept_id}, customer_code={customer.customer_code}")
        pi_no = NumberGenerator.generate_pi_no(db, dept_id, customer.customer_code)
        logger.info(f"[✅ PI号生成成功]: {pi_no}")
    except Exception as e:
        logger.error(f"[❌ PI号生成失败]: {e}", exc_info=True)
        raise

    # 计算总金额
    logger.info(f"[步骤3/6] 计算订单总金额...")
    total_amount = Decimal('0')
    for idx, item_data in enumerate(items):
        # 🔧 2026-06-22 修复：兼容 'qty' 和 'quantity' 两种字段名
        qty = item_data.get('quantity', 0) or item_data.get('qty', 0) or 0
        price = item_data.get('unit_price', Decimal('0')) or Decimal('0')
        row_total = qty * price
        total_amount += row_total
        logger.debug(f"  Item {idx+1}: QTY={qty}, 单价={price}, 小计={row_total}")

    logger.info(f"[✅ 总金额计算完成]: {total_amount} USD")

    # 创建PI主表
    logger.info(f"[步骤4/6] 创建PI主表记录...")
    pi = PiProformaInvoice(
        pi_no=pi_no,
        customer_id=customer_id,
        dept_id=dept_id,
        total_amount=total_amount,
        currency='USD',
        status=1
    )
    db.add(pi)
    db.flush()  # 获取pi.id
    logger.info(f"[✅ PI主表创建成功]")
    logger.info(f"  pi_id={pi.id}")
    logger.info(f"  pi_no={pi.pi_no}")
    logger.info(f"  status={pi.status} (1=草稿)")

    # 创建Items
    logger.info(f"\n[步骤5/6] 创建PI明细项 (共{len(items)}个)...")
    items_created = 0
    temp_products_count = 0

    for idx, item_data in enumerate(items):
        item_start = datetime.now()
        # 🔧 2026-06-22 修复：兼容 'qty' 和 'quantity' 两种字段名
        qty = item_data.get('quantity', 0) or item_data.get('qty', 0) or 0
        price = item_data.get('unit_price', Decimal('0')) or Decimal('0')
        model = item_data.get('model') or item_data.get('customer_model')

        logger.info(f"\n  [Item {idx+1}/{len(items)}] 开始创建...")
        logger.info(f"    MODEL: {model}")
        logger.info(f"    QTY: {qty}")
        logger.info(f"    单价: {price} USD")
        logger.info(f"    小计: {qty * price} USD")

        # 检查产品状态
        item_is_temporary = False
        item_temp_model = None
        prod_id = item_data.get('product_id')

        if prod_id:
            logger.info(f"    [产品信息] product_id={prod_id}")
            prod_obj = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == prod_id).first()

            if prod_obj:
                item_is_temporary = bool(prod_obj.is_temporary)
                item_temp_model = prod_obj.customer_model or model
                # 🔧 2026-06-22 修复：PrdCustomerProduct 没有 oe_number 字段
                # OE号存储在关联表 PrdCustomerProductOE 中，通过 oes 关系访问
                prod_oe_number = None
                if prod_obj.oes:
                    primary_oe = next((oe for oe in prod_obj.oes if oe.is_primary), None)
                    prod_oe_number = primary_oe.oe_number if primary_oe else (prod_obj.oes[0].oe_number if prod_obj.oes else None)
                logger.info(f"    [产品详情]")
                logger.info(f"      产品ID: {prod_obj.id}")
                logger.info(f"      是否临时: {'是 (需要转正)' if item_is_temporary else '否'}")
                logger.info(f"      客户型号: {prod_obj.customer_model}")
                logger.info(f"      OE号: {prod_oe_number}")

                if item_is_temporary:
                    temp_products_count += 1
                    logger.warning(f"    ⚠️ 此产品为临时产品，后续需要转正操作")
            else:
                logger.warning(f"    [警告] product_id={prod_id} 在数据库中未找到!")
        else:
            logger.warning(f"    [警告] 无product_id! 可能是匹配失败")

        # 创建Item对象
        # 🔧 2026-06-22 升级：所有 41 列字段直接存入 pi_proforma_invoice_item 主表
        # 2026-06-29 修复：customer_model = customer_code，一般情况下两者相等
        item_code = item_data.get('customer_code') or item_data.get('customer_model') or model
        item = PiProformaInvoiceItem(
            pi_id=pi.id,
            product_id=prod_id,
            # === A组: 基础信息 (Col 0-9) ===
            oe_number=item_data.get('oe_number'),
            customer_code=item_code,
            customer_model=item_code,  # Col 7 - 与 customer_code 保持一致
            product_feature=item_data.get('product_feature'),         # Col 8
            detail_desc=item_data.get('product_desc') or item_data.get('detail_desc'),  # Col 5
            quantity=qty,                                              # Col 9
            unit_price=price,                                          # Col 10
            total_price=qty * price,                                   # Col 11
            remark=item_data.get('remark') or (f"QTY: {qty}, MODEL: {model}" if qty or model else None),  # Col 4
            is_temporary=item_is_temporary,
            temp_model=item_temp_model,

            # === B组: 价格与财务 (Col 13-20) ===
            customer_prepayment=item_data.get('customer_prepayment'),  # Col 13
            remaining_payment=item_data.get('remaining_payment'),      # Col 14
            purchase_price=item_data.get('purchase_price'),            # Col 17
            shipping_fee=item_data.get('shipping_fee'),                # Col 18
            misc_fee=item_data.get('misc_fee'),                        # Col 19
            total_order_amount=item_data.get('total_order_amount'),    # Col 20

            # === C组: 供应商与采购 (Col 21-26) ===
            supplier_name=item_data.get('supplier_name'),              # Col 21
            shop_url=item_data.get('shop_url'),                        # Col 22
            delivery_date=item_data.get('delivery_date'),              # Col 23
            storage_status=item_data.get('storage_status'),            # Col 24/27
            stocked_qty=item_data.get('stocked_qty'),                  # Col 28
            factory_deposit=item_data.get('factory_deposit'),          # Col 25
            factory_balance=item_data.get('factory_balance'),          # Col 26
            factory_code=item_data.get('factory_code'),                # Col 32

            # === D/E组: 包装与采购选项 (Col 29-30, 33-35, 37) ===
            packaging=item_data.get('packaging'),                      # Col 29
            purchase_option_name=item_data.get('purchase_option_name'),  # Col 30
            product_detail=item_data.get('product_detail'),            # Col 31
            carton_size=item_data.get('carton_size'),                  # Col 33
            pack_spec=item_data.get('pack_spec'),                      # Col 34
            carton_count=item_data.get('carton_count'),                # Col 35
            carton_gross_weight=item_data.get('carton_gross_weight'),  # Col 37
            # Col 33 细化字段
            carton_length_cm=item_data.get('carton_length_cm'),
            carton_width_cm=item_data.get('carton_width_cm'),
            carton_height_cm=item_data.get('carton_height_cm'),

            # === F组: 其他属性 (Col 39-40) ===
            brand=item_data.get('brand'),                              # Col 39
            invoice_status=item_data.get('invoice_status'),            # Col 40
        )
        db.add(item)
        items_created += 1

        item_duration = (datetime.now() - item_start).total_seconds()
        logger.info(f"    [✅ Item创建完成] 耗时={item_duration:.3f}s")

    logger.info(f"\n[✅ 所有Items创建完成]")
    logger.info(f"  成功创建: {items_created}/{len(items)} 个")
    logger.info(f"  临时产品数: {temp_products_count} 个 (需要后续转正)")
    logger.info(f"  正式产品数: {items_created - temp_products_count} 个")

    create_duration = (datetime.now() - create_start).total_seconds()
    logger.info(f"\n{'─' * 80}")
    logger.info(f"[✅ PI订单创建函数完成] 总耗时={create_duration:.3f}s")
    logger.info(f"  最终结果:")
    logger.info(f"    PI_ID: {pi.id}")
    logger.info(f"    PI_NO: {pi.pi_no}")
    logger.info(f"    总金额: {pi.total_amount}")
    logger.info(f"    Items数: {items_created}")
    logger.info(f"    临时产品: {temp_products_count}")
    logger.info(f"{'─' * 80}\n")

    return pi


def _get_suggestions(error_msg: str) -> List[str]:
    """根据错误信息提供修正建议"""
    suggestions = []
    
    if 'pi_no' in error_msg.lower():
        suggestions.append("检查PI号格式，应以'PI'开头后跟数字")
    if 'date' in error_msg.lower():
        suggestions.append("检查日期格式，应为'YYYY-MM-DD'")
    if 'customer' in error_msg.lower():
        suggestions.append("检查客户是否存在")
    if 'product' in error_msg.lower():
        suggestions.append("检查产品OE号是否正确")
    
    if not suggestions:
        suggestions.append("检查数据格式是否正确")
        suggestions.append("查看完整错误信息")
    
    return suggestions


# ============================================================
# 3. 产品搜索接口
# ============================================================

@product_router.get("/search", response_model=ProductSearchResponse)
async def search_products(
    keyword: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    threshold: float = Query(0.3, ge=0, le=1),
    db: Session = Depends(get_db)
):
    """
    模糊搜索产品
    - 使用Trigram索引加速查询
    - 支持OE号、产品名称模糊匹配
    - 返回结果按相似度排序
    """
    try:
        matcher = ProductMatcher(db)
        
        # 尝试OE号匹配
        oe_matches = matcher._match_by_oe_number(keyword, limit=limit)
        
        # 尝试产品名称匹配
        name_matches = matcher._match_by_product_name(keyword, limit=limit)
        
        # 合并结果
        all_matches = oe_matches + name_matches
        all_matches = matcher._deduplicate_and_sort(all_matches)
        
        # 过滤低于阈值的匹配
        threshold_score = threshold * 100
        filtered_matches = [m for m in all_matches if m['match_score'] >= threshold_score]
        
        # 构建返回结果
        results = []
        for match in filtered_matches[:limit]:
            results.append(ProductMatchResult(
                product_id=match['product_id'],
                match_type=match['match_type'],
                match_score=match['match_score'],
                detail_desc=match.get('detail_desc'),
                oe_number=match.get('oe_number'),
                brand=match.get('brand'),
                product=ProductDetail(
                    id=match['product_id'],
                    detail_desc=match.get('detail_desc'),
                    oe_number=match.get('oe_number'),
                    brand=match.get('brand')
                ) if match.get('product') else None
            ))
        
        return ProductSearchResponse(
            success=True,
            data=results,
            total=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 4. 批量产品匹配接口
# ============================================================

@product_router.post("/batch-match", response_model=BatchMatchResponse)
async def batch_match_products(
    request: BatchMatchRequest,
    db: Session = Depends(get_db)
):
    """
    批量匹配产品
    - 支持最多1000条同时匹配
    - 返回每个输入项的匹配结果
    - 2026-06-23 扩展：auto_create_temporary=True 时，未匹配项自动创建 temp 产品
    """
    try:
        from crud.customer_product import find_or_create_temp_customer_product
        from schemas.customer_product import CustomerProductResponse

        matcher = ProductMatcher(db)
        results = []

        # 2026-06-23 校验：auto_create_temporary=True 时 customer_id 必填
        # 2026-06-23 回滚说明：前端不发 auto_create_temporary=true 即关闭本特性，旧行为完全保留。
        if request.auto_create_temporary and not request.customer_id:
            raise HTTPException(
                status_code=422,
                detail="auto_create_temporary=True 时必须传入 customer_id",
            )

        for item in request.items:
            matches = matcher.match_product(
                customer_id=item.customer_id,
                customer_code=item.customer_code,
                oe_number=item.oe_number,
                product_name=item.product_name
            )

            best_match = matcher.get_best_match(matches)

            # 构建匹配结果
            match_results = []
            for m in matches:
                match_results.append(ProductMatchResult(
                    product_id=m['product_id'],
                    match_type=m['match_type'],
                    match_score=m['match_score'],
                    detail_desc=m.get('detail_desc'),
                    oe_number=m.get('oe_number'),
                    brand=m.get('brand')
                ))

            best = None
            if best_match:
                best = ProductMatchResult(
                    product_id=best_match['product_id'],
                    match_type=best_match['match_type'],
                    match_score=best_match['match_score'],
                    detail_desc=best_match.get('detail_desc'),
                    oe_number=best_match.get('oe_number'),
                    brand=best_match.get('brand')
                )

            # 2026-06-23 默认状态：未匹配
            status = "unmatched"
            product_id_out: Optional[int] = None
            dedup_hit = False
            product_dict: Optional[Dict[str, Any]] = None

            if best_match:
                # 命中现有产品
                status = "matched"
                product_id_out = best_match['product_id']
            elif request.auto_create_temporary:
                # 导入场景：未匹配 → 静默创建/复用 temp 产品
                # 优先使用 item.customer_id（导入行级别），回退到 request.customer_id
                cust_id = item.customer_id or request.customer_id
                row = {
                    'customer_model': item.model or item.customer_code,
                    'oe_number': item.oe_number,
                    'product_name': item.product_name,
                    'customer_remark': None,
                    'unit_price': None,
                }
                product, created = find_or_create_temp_customer_product(db, cust_id, row)
                status = "created_temp" if created else "reused_existing"
                dedup_hit = not created
                product_id_out = product.id
                product_dict = CustomerProductResponse.model_validate(product).model_dump(mode='json')

            results.append(BatchMatchResultItem(
                input=item,
                matches=match_results,
                best_match=best,
                status=status,
                product_id=product_id_out,
                dedup_hit=dedup_hit,
                product=product_dict,
            ))

        return BatchMatchResponse(
            success=True,
            results=results
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 5. 单个产品匹配接口
# ============================================================

@product_router.post("/match", response_model=MatchResponse)
async def match_product(
    request: MatchRequest,
    db: Session = Depends(get_db)
):
    """
    单个产品匹配
    - 根据客户产品编号、OE号、产品名称匹配
    - 返回最佳匹配结果
    """
    try:
        matcher = ProductMatcher(db)
        
        matches = matcher.match_product(
            customer_id=request.customer_id,
            customer_code=request.customer_code,
            oe_number=request.oe_number,
            product_name=request.product_name
        )
        
        best_match = matcher.get_best_match(matches)
        
        # 构建结果
        match_results = []
        for m in matches:
            match_results.append(ProductMatchResult(
                product_id=m['product_id'],
                match_type=m['match_type'],
                match_score=m['match_score'],
                detail_desc=m.get('detail_desc'),
                oe_number=m.get('oe_number'),
                brand=m.get('brand')
            ))
        
        best = None
        match_type = 'no_match'
        if best_match:
            best = ProductMatchResult(
                product_id=best_match['product_id'],
                match_type=best_match['match_type'],
                match_score=best_match['match_score'],
                detail_desc=best_match.get('detail_desc'),
                oe_number=best_match.get('oe_number'),
                brand=best_match.get('brand')
            )
            match_type = best_match['match_type']
        
        return MatchResponse(
            success=True,
            matches=match_results,
            best_match=best,
            match_type=match_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 6. 临时产品API
# ============================================================

from pydantic import BaseModel, ConfigDict
from typing import Optional


class TemporaryProductCreate(BaseModel):
    customer_code: str
    oe_number: Optional[str] = None
    product_name: Optional[str] = None
    qty: Optional[int] = 0
    model: Optional[str] = None
    brand: Optional[str] = None
    dept_id: Optional[str] = "P01"


class TemporaryProductResponse(BaseModel):
    id: int
    product_code: str
    detail_desc: str
    oe_number: Optional[str] = None
    is_temporary: bool
    model_config = ConfigDict(from_attributes=True)


@product_router.post("/temporary", response_model=TemporaryProductResponse)
async def create_temporary_product(
    product_data: TemporaryProductCreate,
    db: Session = Depends(get_db)
):
    """
    创建临时产品
    - 用于订单导入时未匹配的产品
    - 创建后返回临时产品信息
    """
    from crud.product import create_temporary_product
    
    try:
        product = create_temporary_product(db, product_data.model_dump())
        return TemporaryProductResponse(
            id=product.id,
            product_code=product.product_code,
            detail_desc=product.detail_desc,
            oe_number=product.oe_number,
            is_temporary=product.is_temporary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 7. 单条订单创建API
# ============================================================

from pydantic import BaseModel


class SingleOrderCreate(BaseModel):
    customer_id: int
    product_id: Optional[int] = None
    customer_code: Optional[str] = None
    oe_number: Optional[str] = None
    detail_desc: Optional[str] = None
    quantity: int = 1
    unit_price: float = 0.0
    delivery_date: Optional[str] = None
    remark: Optional[str] = None


class SingleOrderResponse(BaseModel):
    success: bool
    pi_id: Optional[int] = None
    pi_no: Optional[str] = None
    error: Optional[str] = None


@router.post("/single", response_model=SingleOrderResponse)
async def create_single_order(
    order_data: SingleOrderCreate,
    db: Session = Depends(get_db)
):
    """
    单条订单快速创建
    
    - 选择客户和产品
    - 输入数量和单价
    - 自动生成PI号
    """
    from models.pi import PiProformaInvoice, PiProformaInvoiceItem
    from models.customer import CrmCustomer
    from utils.number_generator import NumberGenerator
    from datetime import datetime
    
    try:
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == order_data.customer_id).first()
        if not customer:
            return SingleOrderResponse(success=False, error="客户不存在")
        
        dept_id = customer.dept_id if customer.dept_id else 'D01'
        pi_no = NumberGenerator.generate_pi_no(db, dept_id, customer.customer_code)
        
        total_amount = order_data.quantity * order_data.unit_price
        
        pi = PiProformaInvoice(
            pi_no=pi_no,
            customer_id=order_data.customer_id,
            dept_id=dept_id,
            total_amount=total_amount,
            currency='USD',
            status=1
        )
        db.add(pi)
        db.flush()
        
        item = PiProformaInvoiceItem(
            pi_id=pi.id,
            product_id=order_data.product_id,
            oe_number=order_data.oe_number,
            customer_code=order_data.customer_code,
            detail_desc=order_data.detail_desc,
            quantity=order_data.quantity,
            unit_price=order_data.unit_price,
            total_price=total_amount,
            remark=order_data.remark
        )
        db.add(item)
        db.commit()
        db.refresh(pi)
        
        return SingleOrderResponse(
            success=True,
            pi_id=pi.id,
            pi_no=pi.pi_no
        )
    except Exception as e:
        db.rollback()
        return SingleOrderResponse(success=False, error=str(e))


# ============================================
# 2. 生成/重新生成 PI 号
# ============================================

class GeneratePiResponse(BaseModel):
    success: bool
    pi_id: Optional[int] = None
    pi_no: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.post("/{order_id}/generate-pi", response_model=GeneratePiResponse)
async def generate_pi_for_order(
    order_id: int,
    force_regenerate: bool = False,
    db: Session = Depends(get_db)
):
    """
    为订单生成或重新生成 PI 号
    
    - 如果订单已有 PI 号且 force_regenerate=False，返回现有 PI 号
    - 如果 force_regenerate=True，生成新 PI 号并更新
    - 如果订单没有 PI 号，生成新 PI 号
    """
    from models.pi import PiProformaInvoice
    from models.customer import CrmCustomer
    from utils.number_generator import NumberGenerator
    
    order = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == order_id).first()
    if not order:
        return GeneratePiResponse(success=False, error=f"订单不存在 (ID: {order_id})")
    
    if order.pi_no and not force_regenerate:
        return GeneratePiResponse(
            success=True,
            pi_id=order.id,
            pi_no=order.pi_no,
            message="订单已有 PI 号"
        )
    
    try:
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == order.customer_id).first()
        customer_code = customer.customer_code if customer else "C001"
        
        new_pi_no = NumberGenerator.generate_pi_no(db, order.dept_id, customer_code)
        
        order.pi_no = new_pi_no
        db.commit()
        db.refresh(order)
        
        return GeneratePiResponse(
            success=True,
            pi_id=order.id,
            pi_no=new_pi_no,
            message="PI 号生成成功"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"生成 PI 号失败: {e}", exc_info=True)
        return GeneratePiResponse(success=False, error=f"生成失败: {str(e)}")


# ============================================
# 3. 补充商品接口
# ============================================

class SupplementItemsRequest(BaseModel):
    items: List[dict]
    is_temp: bool = True

class SupplementItemsResponse(BaseModel):
    success: bool
    created_count: int = 0
    failed_count: int = 0
    errors: List[str] = []
    message: Optional[str] = None

@router.post("/{order_id}/supplement-items", response_model=SupplementItemsResponse)
async def supplement_order_items(
    order_id: int,
    request: SupplementItemsRequest,
    db: Session = Depends(get_db)
):
    """
    补充订单商品
    
    - 将 Excel 预览中的商品追加到现有订单
    - 如果产品已存在，更新产品信息
    - 如果产品不存在，创建临时产品或正式产品
    """
    from models.pi import PiProformaInvoice, PiProformaInvoiceItem
    
    # 验证订单是否存在
    order = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"订单不存在 (ID: {order_id})")
    
    errors = []
    created_count = 0
    failed_count = 0
    
    for item_data in request.items:
        try:
            # 尝试匹配产品
            product_code = item_data.get('product_code', '')
            oe_number = item_data.get('oe_number', '')
            customer_id = order.customer_id
            
            # 查找是否已存在产品
            existing_product = None
            if product_code:
                from models.customer_product import PrdCustomerProduct
                existing_product = db.query(PrdCustomerProduct).filter(
                    PrdCustomerProduct.system_code == product_code
                ).first()
            
            if existing_product:
                # 产品已存在，创建订单项
                order_item = PiProformaInvoiceItem(
                    order_id=order_id,
                    product_id=existing_product.id,
                    quantity=item_data.get('qty', 1),
                    unit_price=item_data.get('unit_price') or 0,
                    amount=item_data.get('amount', 0)
                )
                db.add(order_item)
                created_count += 1
            else:
                # 产品不存在，根据 is_temp 创建临时或正式产品
                if request.is_temp:
                    # Phase 5: 创建 PrdCustomerProduct 临时产品
                    from models.customer_product import PrdCustomerProduct
                    new_product = PrdCustomerProduct(
                        customer_id=customer_id,
                        product_name=item_data.get('detail_desc', ''),
                        customer_model=oe_number or product_code,
                        detail_desc=item_data.get('detail_desc', ''),
                        is_temporary=True,
                        is_active=True,
                    )
                    db.add(new_product)
                    db.flush()
                    
                    order_item = PiProformaInvoiceItem(
                        order_id=order_id,
                        product_id=new_product.id,
                        quantity=item_data.get('qty', 1),
                        unit_price=item_data.get('unit_price') or 0,
                        amount=item_data.get('amount', 0)
                    )
                    db.add(order_item)
                    created_count += 1
                else:
                    # Phase 5: 直接创建 PrdCustomerProduct 正式产品
                    from models.customer_product import PrdCustomerProduct
                    from crud.customer_product import _generate_system_code
                    detail_desc = item_data.get('detail_desc', '') or product_code
                    category_code = item_data.get('category_id')
                    system_code = _generate_system_code(db, customer_id, category_code)
                    new_product = PrdCustomerProduct(
                        customer_id=customer_id,
                        product_name=detail_desc,
                        customer_model=oe_number or product_code,
                        detail_desc=detail_desc,
                        category_id=category_code,
                        price_usd=item_data.get('unit_price'),
                        is_active=True,
                        system_code=system_code,
                        is_temporary=False,
                    )
                    db.add(new_product)
                    db.flush()

                    # 创建客户产品编号记录（用于搜索匹配）
                    if product_code:
                        from models.customer_product_code import PrdCustomerProductCode
                        cp_code = PrdCustomerProductCode(
                            customer_product_id=new_product.id,
                            product_code=product_code,
                            is_primary=True
                        )
                        db.add(cp_code)

                    # 创建OE号记录（如果有）
                    if oe_number:
                        from models.customer_product_oe import PrdCustomerProductOE
                        cp_oe = PrdCustomerProductOE(
                            customer_product_id=new_product.id,
                            oe_number=oe_number,
                            is_primary=True
                        )
                        db.add(cp_oe)
                    
                    order_item = PiProformaInvoiceItem(
                        order_id=order_id,
                        product_id=new_product.id,
                        quantity=item_data.get('qty', 1),
                        unit_price=item_data.get('unit_price') or 0,
                        amount=item_data.get('amount', 0)
                    )
                    db.add(order_item)
                    created_count += 1
                    
        except Exception as e:
            errors.append(f"产品 {item_data.get('product_code', '未知')} 添加失败: {str(e)}")
            failed_count += 1
    
    try:
        db.commit()
        return SupplementItemsResponse(
            success=failed_count == 0,
            created_count=created_count,
            failed_count=failed_count,
            errors=errors,
            message=f"成功添加 {created_count} 个商品"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


# ============================================
# 4. 临时产品转正接口
# ============================================

class TemporaryProductResponse(BaseModel):
    id: int
    product_code: Optional[str] = None
    detail_desc: Optional[str] = None
    oe_number: Optional[str] = None
    is_temporary: bool

@product_router.post("/confirm", response_model=TemporaryProductResponse)
async def confirm_temporary_product(
    product_id: int,
    full_data: dict,
    db: Session = Depends(get_db)
):
    """
    确认临时产品为正式产品
    - 将 is_temporary=True 的产品转换为正式产品
    - 同步创建 PrdCustomerProduct 记录并生成系统编号
    """
    from crud.product import confirm_temporary_product
    from crud.customer_product import _generate_system_code

    try:
        product = confirm_temporary_product(db, product_id, full_data)

        # PrdCustomerProduct 已在 confirm_temporary_product -> _ensure_customer_product_exists 中创建
        # 此处只需补充客户产品编号和OE号（如果不存在）
        customer_id = full_data.get('customer_id')
        if customer_id:
            from models.customer_product import PrdCustomerProduct
            from models.customer_product_code import PrdCustomerProductCode
            from models.customer_product_oe import PrdCustomerProductOE

            detail_desc = product.detail_desc or product.product_code or ''

            # 查询已创建的 PrdCustomerProduct 记录
            cp_record = db.query(PrdCustomerProduct).filter(
                PrdCustomerProduct.customer_id == customer_id,
                PrdCustomerProduct.product_name == detail_desc
            ).first()

            if cp_record:
                # 补充客户产品编号（如果不存在）
                customer_product_code = full_data.get('customer_product_code') or product.product_code or ''
                if customer_product_code:
                    existing_code = db.query(PrdCustomerProductCode).filter(
                        PrdCustomerProductCode.customer_product_id == cp_record.id,
                        PrdCustomerProductCode.product_code == customer_product_code
                    ).first()
                    if not existing_code:
                        cp_code = PrdCustomerProductCode(
                            customer_product_id=cp_record.id,
                            product_code=customer_product_code,
                            is_primary=True
                        )
                        db.add(cp_code)

                # 补充OE号（如果不存在）
                oe_number = product.oe_number or ''
                if oe_number:
                    existing_oe = db.query(PrdCustomerProductOE).filter(
                        PrdCustomerProductOE.customer_product_id == cp_record.id,
                        PrdCustomerProductOE.oe_number == oe_number
                    ).first()
                    if not existing_oe:
                        cp_oe = PrdCustomerProductOE(
                            customer_product_id=cp_record.id,
                            oe_number=oe_number,
                            is_primary=True
                        )
                        db.add(cp_oe)

                db.commit()

        return TemporaryProductResponse(
            id=product.id,
            product_code=product.product_code,
            detail_desc=product.detail_desc,
            oe_number=product.oe_number,
            is_temporary=product.is_temporary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))