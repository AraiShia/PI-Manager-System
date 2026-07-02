from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from crud.pi import (
    create_pi_invoice, get_pi_invoice, get_pi_invoices, update_pi_status, get_price_history,
    update_pi_invoice, get_pi_invoice_detail, get_pi_invoices_with_customer,
    get_pi_item, update_pi_item,
    delete_pi_item, inbound_pi_item, inbound_pi_items_batch,  # 需求#40
    delete_pi_invoice,  # 2026-06-15 修复：之前漏导，调用时 NameError
    get_pi_versions, save_pi_snapshot,  # 需求#42
    save_formal_record, load_formal_record, formal_record_exists,  # 需求#42
)
from schemas.pi import PIInvoiceCreate, PIInvoiceResponse, PIInvoiceUpdate
from schemas.pi_detail import PIInvoiceDetailFullResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/pi", tags=["PI管理"])

@router.post("/")
def create_pi_api(pi: PIInvoiceCreate, db: Session = Depends(get_db)):
    try:
        result = create_pi_invoice(db, pi)
        return {
            "id": result.id,
            "dept_id": result.dept_id,
            "pi_no": result.pi_no,
            "customer_id": result.customer_id,
            "total_amount": float(result.total_amount) if result.total_amount else 0,
            "currency": result.currency or "USD",
            "status": result.status or 1,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[PIInvoiceResponse])
def read_pi_list(skip: int = 0, limit: int = 100, status: int = None, db: Session = Depends(get_db)):
    from models import InvInventory, PiProformaInvoiceItem
    from models import PiPaymentStage as _PS
    from models import PrdCustomerProduct
    results = get_pi_invoices_with_customer(db, skip=skip, limit=limit, status=status)
    # 2026-06-10: 修复 T5.3 + 总表回填 — 加上日期/产品数/已付金额/库存/临时产品等字段
    for r in results:
        pi_id = r.get("id")
        if not pi_id:
            continue
        # 1) 订单日期：取 PI 主单的 created_at
        if not r.get("order_date") and r.get("created_at"):
            r["order_date"] = r["created_at"][:10] if isinstance(r["created_at"], str) else r["created_at"].isoformat()[:10]
        # 2) 产品数
        item_count = db.query(PiProformaInvoiceItem).filter(
            PiProformaInvoiceItem.pi_id == pi_id
        ).count()
        r["product_count"] = item_count
        # 3) 已付款金额（2026-06-16 PI 通路修复：与 update_pi_payment_status 一致）
        #    优先以 ArCustomerPayment 水单为准，无水单时回退到分期表实付合计
        from models import ArCustomerPayment
        payments_for_pi = db.query(ArCustomerPayment).filter(ArCustomerPayment.pi_id == pi_id).all()
        if payments_for_pi:
            paid_amount_value = float(sum(float(p.actual_amount or p.amount or 0) for p in payments_for_pi))
        else:
            paid_rows = db.query(_PS).filter(
                _PS.pi_id == pi_id,
                _PS.status == 2
            ).all()
            paid_amount_value = float(sum(float(s.amount or 0) for s in paid_rows))
        r["paid_amount"] = paid_amount_value
        # 4) 库存字段（数值统计）
        inv_list = db.query(InvInventory).filter(InvInventory.pi_id == pi_id).all()
        total_qty = sum(float(i.total_quantity or 0) for i in inv_list)
        pending_qty = sum(float(i.pending_quantity or 0) for i in inv_list)
        r["has_inventory"] = total_qty > 0
        r["inventory_quantity"] = total_qty
        r["inventory_pending"] = pending_qty
        r["inventory_count"] = len(inv_list)

        # 4.5) storage_status 状态枚举（2026-06-23 收敛：与 /pi/detail/{id} 同源）
        # 期望总数量 = 所有 PI item 的 quantity 之和；inv_inventory.total_quantity 聚合后比较。
        from crud.storage_status import StorageStatus
        expected_qty_total = float(
            db.query(func.coalesce(func.sum(PiProformaInvoiceItem.quantity), 0))
            .filter(PiProformaInvoiceItem.pi_id == pi_id).scalar() or 0
        )
        r["storage_status"] = StorageStatus.from_order_inventory(
            db, pi_id=pi_id, expected_total=expected_qty_total
        )
        # 5) 2026-06-11 Phase 7.6: 出货回填
        from models import ShShipment
        sh_list = db.query(ShShipment).filter(ShShipment.pi_id == pi_id).all()
        r["shipment_count"] = len(sh_list)
        sh_qty = 0.0
        latest_date = None
        for sh in sh_list:
            for shi in (sh.items or []):
                sh_qty += float(shi.quantity or 0)
            if sh.created_at:
                ds = sh.created_at.isoformat()[:10]
                if latest_date is None or ds > latest_date:
                    latest_date = ds
        r["shipped_quantity"] = sh_qty
        r["latest_shipment_date"] = latest_date
        # 7) 2026-06-11 第 38 条: 派生未付款/进度/状态
        total = float(r.get("total_amount") or 0)
        paid = float(r.get("paid_amount") or 0)
        unpaid = max(total - paid, 0.0)
        progress = (paid / total * 100.0) if total > 0 else 0.0
        if total <= 0:
            status_text = "未付款"
        elif progress >= 99.9:
            status_text = "已结清"
        elif progress > 0:
            status_text = "部分付款"
        else:
            status_text = "未付款"
        r["unpaid_amount"] = round(unpaid, 2)
        r["payment_progress"] = round(progress, 1)
        r["payment_status"] = status_text
    print(f"DEBUG - read_pi_list returned {len(results)} items")
    return results

@router.get("/detail/{pi_id}", response_model=PIInvoiceDetailFullResponse)
def read_pi_detail(pi_id: int, db: Session = Depends(get_db)):
    detail = get_pi_invoice_detail(db, pi_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="PI单不存在")
    return detail


# 2026-06-10: 修复 T6.2 — 付款分期端点
@router.post("/{pi_id}/payment-stages")
def create_payment_stage(pi_id: int, payload: dict, db: Session = Depends(get_db)):
    from models import PiPaymentStage
    pi = get_pi_invoice(db, pi_id)
    if not pi:
        raise HTTPException(status_code=404, detail="PI单不存在")
    stage = PiPaymentStage(
        pi_id=pi_id,
        stage_type=payload.get("stage_type") or payload.get("stage_name") or "deposit",
        stage_no=payload.get("stage_no", 1),
        amount=payload.get("amount", 0),
        percentage=payload.get("percentage"),
        payment_method=payload.get("payment_method"),
        status=1,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return {
        "id": stage.id,
        "pi_id": stage.pi_id,
        "stage_type": stage.stage_type,
        "stage_no": stage.stage_no,
        "amount": float(stage.amount) if stage.amount else 0,
        "percentage": float(stage.percentage) if stage.percentage else None,
        "status": stage.status,
    }


@router.put("/{pi_id}/payment-stages/{stage_id}")
def update_payment_stage(pi_id: int, stage_id: int, payload: dict, db: Session = Depends(get_db)):
    from models import PiPaymentStage
    stage = db.query(PiPaymentStage).filter(
        PiPaymentStage.id == stage_id,
        PiPaymentStage.pi_id == pi_id
    ).first()
    if not stage:
        raise HTTPException(status_code=404, detail="分期不存在")
    for k in ("stage_type", "amount", "percentage", "status", "paid_date"):
        if k in payload:
            setattr(stage, k, payload[k])
    db.commit()
    db.refresh(stage)
    return {"id": stage.id, "status": stage.status}


@router.delete("/{pi_id}/payment-stages/{stage_id}")
def delete_payment_stage(pi_id: int, stage_id: int, db: Session = Depends(get_db)):
    from models import PiPaymentStage
    stage = db.query(PiPaymentStage).filter(
        PiPaymentStage.id == stage_id,
        PiPaymentStage.pi_id == pi_id
    ).first()
    if not stage:
        raise HTTPException(status_code=404, detail="分期不存在")
    db.delete(stage)
    db.commit()
    return {"deleted": stage_id}


# 2026-06-11 第 38 条: 一次性添加付款(创建 status=2 的分期)
@router.post("/{pi_id}/payments")
def add_payment(pi_id: int, payload: dict, db: Session = Depends(get_db)):
    """
    一次性添加付款(快捷入口):
    请求: { amount, payment_method?, remark? }
    - amount 必须 > 0
    - 自动取下一个 stage_no
    - 创建 PiPaymentStage(status=2, paid_date=today)
    - 返回新建的分期 + 累计 paid_amount / unpaid_amount
    """
    from models import PiPaymentStage, PiProformaInvoice
    from datetime import date

    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404, detail="PI单不存在")

    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount 必须大于 0")

    # 下一个 stage_no
    next_no = (db.query(PiPaymentStage)
                .filter(PiPaymentStage.pi_id == pi_id)
                .count()) + 1

    stage = PiPaymentStage(
        pi_id=pi_id,
        stage_type=payload.get("stage_type") or "deposit",
        stage_no=next_no,
        amount=amount,
        payment_method=payload.get("payment_method"),
        percentage=payload.get("percentage"),
        status=2,  # 2=已付
        paid_date=date.today(),
    )
    db.add(stage)

    # 更新 PI 的 updated_at
    pi.updated_at = __import__("datetime").datetime.utcnow()
    db.commit()
    db.refresh(stage)

    # 2026-06-16 PI 通路修复：写分期后同步 PI 主表 status
    from crud.payment import update_pi_payment_status
    update_pi_payment_status(db, pi_id)

    # 计算累计（2026-06-16 PI 通路修复：与 update_pi_payment_status 一致）
    from models import ArCustomerPayment
    total = float(pi.total_amount or 0)
    payments_for_pi = db.query(ArCustomerPayment).filter(ArCustomerPayment.pi_id == pi_id).all()
    if payments_for_pi:
        paid_amount = sum(float(p.actual_amount or p.amount or 0) for p in payments_for_pi)
    else:
        paid_rows = db.query(PiPaymentStage).filter(
            PiPaymentStage.pi_id == pi_id,
            PiPaymentStage.status == 2
        ).all()
        paid_amount = sum(float(s.amount or 0) for s in paid_rows)
    unpaid_amount = max(total - paid_amount, 0.0)
    progress = (paid_amount / total * 100.0) if total > 0 else 0.0

    return {
        "stage": {
            "id": stage.id,
            "pi_id": stage.pi_id,
            "stage_no": stage.stage_no,
            "stage_type": stage.stage_type,
            "amount": float(stage.amount) if stage.amount else 0,
            "status": stage.status,
            "paid_date": stage.paid_date.isoformat() if stage.paid_date else None,
        },
        "pi_id": pi_id,
        "total_amount": total,
        "paid_amount": round(paid_amount, 2),
        "unpaid_amount": round(unpaid_amount, 2),
        "payment_progress": round(progress, 1),
    }


# 注意：/pi/{pi_id} 路由在下方 line 440 重新定义（修复后版本）
# 2026-06-22 修复：原 line 274 路由（已删除，因为与 line 440 重复会导致Python函数重定义错误）
# 错误版本直接返回 db_pi，不包含 items
# 修复版本使用 get_pi_invoice_detail 返回包含 items 的完整数据

@router.delete("/{pi_id}")
def delete_pi_api(pi_id: int, db: Session = Depends(get_db)):
    try:
        delete_pi_invoice(db, pi_id)
        return {"success": True, "message": "PI已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch-delete")
def batch_delete_pi_api(pi_ids: List[int], db: Session = Depends(get_db)):
    """批量删除PI订单

    2026-06-15 强化：捕获所有 Exception 而非仅 ValueError，
    防止 SQLAlchemy / 级联删除等异常变成 500，前端能收到可读错误消息。
    """
    deleted = 0
    errors = []
    for pi_id in pi_ids:
        try:
            delete_pi_invoice(db, pi_id)
            deleted += 1
        except Exception as e:
            # 业务错误（ValueError）+ 底层异常（SQLAlchemy等）都归一为 errors
            errors.append(f"ID {pi_id}: {type(e).__name__}: {e}")
    return {"deleted": deleted, "total": len(pi_ids), "errors": errors}

@router.get("/export/{pi_id}")
def export_pi_excel(pi_id: int, db: Session = Depends(get_db)):
    from crud.pi import get_pi_invoice_detail
    import io
    from fastapi.responses import StreamingResponse
    
    detail = get_pi_invoice_detail(db, pi_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="PI单不存在")
    
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"PI-{detail['pi_no']}"
        
        # 样式定义
        title_font = Font(name='Arial', size=16, bold=True)
        header_font = Font(name='Arial', size=11, bold=True)
        normal_font = Font(name='Arial', size=10)
        header_fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
        header_font_white = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        
        # 标题
        ws.merge_cells('A1:H1')
        ws['A1'] = f"PROFORMA INVOICE - {detail['pi_no']}"
        ws['A1'].font = title_font
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # 基本信息
        status_map = {1: '草稿', 2: '已确认', 3: '已发货', 4: '已完成'}
        info_data = [
            ('客户编号', detail.get('customer_code', '')),
            ('客户名称', detail.get('customer_name', '')),
            ('币种', detail.get('currency', 'USD')),
            ('总金额', detail.get('total_amount', 0)),
            ('状态', status_map.get(detail.get('status', 1), '草稿')),
            ('创建日期', str(detail.get('created_at', ''))[:10] if detail.get('created_at') else ''),
        ]
        for i, (label, value) in enumerate(info_data, start=3):
            ws[f'A{i}'] = label
            ws[f'A{i}'].font = header_font
            ws[f'B{i}'] = value
            ws[f'B{i}'].font = normal_font
        
        # 明细表头
        row = 10
        headers = ['序号', '产品编号', 'OE号', '客户编码', '描述', '数量', '单价', '总价', '备注']
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = header_font_white
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center')
        
        # 明细数据
        for idx, item in enumerate(detail.get('items', []), 1):
            r = row + idx
            values = [
                idx,
                item.get('product_code', ''),
                item.get('oe_number', ''),
                item.get('customer_code', ''),
                item.get('detail_desc', ''),
                item.get('quantity', 0),
                item.get('unit_price', 0),
                item.get('total_price', 0),
                item.get('remark', '')
            ]
            for col, v in enumerate(values, 1):
                cell = ws.cell(row=r, column=col, value=v)
                cell.font = normal_font
                cell.border = thin_border
        
        # 合计行
        total_row = row + len(detail.get('items', [])) + 1
        ws.cell(row=total_row, column=6, value='合计').font = header_font
        ws.cell(row=total_row, column=8, value=detail.get('total_amount', 0)).font = header_font
        
        # 付款阶段
        if detail.get('payment_stages'):
            pay_row = total_row + 2
            ws.cell(row=pay_row, column=1, value='付款阶段').font = header_font
            pay_row += 1
            pay_headers = ['阶段类型', '序号', '金额', '应付日期', '状态']
            for col, h in enumerate(pay_headers, 1):
                cell = ws.cell(row=pay_row, column=col, value=h)
                cell.font = header_font_white
                cell.fill = header_fill
                cell.border = thin_border
            
            for stage in detail['payment_stages']:
                pay_row += 1
                stage_type_map = {'deposit': '定金', 'balance': '尾款'}
                stage_status_map = {1: '待付', 2: '已付'}
                values = [
                    stage_type_map.get(stage['stage_type'], stage['stage_type']),
                    stage.get('stage_no', ''),
                    stage.get('amount', 0),
                    str(stage['due_date'])[:10] if stage.get('due_date') else '',
                    stage_status_map.get(stage['status'], '待付')
                ]
                for col, v in enumerate(values, 1):
                    cell = ws.cell(row=pay_row, column=col, value=v)
                    cell.font = normal_font
                    cell.border = thin_border
        
        # 调整列宽
        col_widths = [8, 15, 15, 15, 30, 10, 12, 12, 20]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = w
        
        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"PI_{detail['pi_no']}.xlsx"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except ImportError:
        raise HTTPException(status_code=500, detail="服务器缺少openpyxl库，无法导出Excel")

@router.get("/{pi_id}", response_model=PIInvoiceResponse)
def read_pi(pi_id: int, db: Session = Depends(get_db)):
    """🔧 2026-06-22 修复：原路由不返回items导致前端刷新拿不到数据
    改用 get_pi_invoice_detail 获取包含items的完整数据
    """
    from crud.pi import get_pi_invoice_detail
    return get_pi_invoice_detail(db, pi_id)

@router.put("/{pi_id}")
def update_pi_api(pi_id: int, pi_update: PIInvoiceUpdate, db: Session = Depends(get_db)):
    try:
        db_pi = update_pi_invoice(db, pi_id, pi_update)
        if db_pi is None:
            raise HTTPException(status_code=404, detail="PI单不存在")
        return {
            "id": db_pi.id,
            "dept_id": db_pi.dept_id,
            "pi_no": db_pi.pi_no,
            "customer_id": db_pi.customer_id,
            "total_amount": float(db_pi.total_amount) if db_pi.total_amount else 0,
            "currency": db_pi.currency or "USD",
            "status": db_pi.status or 1,
            "created_at": db_pi.created_at.isoformat() if db_pi.created_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{pi_id}/status")
def update_pi_status_api(pi_id: int, status_data: dict, db: Session = Depends(get_db)):
    """更新PI单状态（草稿1→已确认2→已发货3→已完成4）"""
    try:
        status = status_data.get('status')
        if status not in [1, 2, 3, 4]:
            raise HTTPException(status_code=400, detail="无效的状态值")
        db_pi = update_pi_status(db, pi_id, status)
        return {
            "id": db_pi.id,
            "pi_no": db_pi.pi_no,
            "status": db_pi.status,
            "success": True
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{pi_id}/storage-status")
def update_pi_storage_status_api(pi_id: int, data: dict, db: Session = Depends(get_db)):
    """更新PI单库存状态（支持'缺货'标记）"""
    from models.pi import PiProformaInvoice

    db_pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not db_pi:
        raise HTTPException(status_code=404, detail="PI单不存在")

    new_status = data.get('storage_status')
    valid_values = {'已入库', '部分入库', '未入库', '缺货', None, ''}
    if new_status not in valid_values:
        raise HTTPException(status_code=400, detail=f"无效的库存状态值: {new_status}")

    db_pi.storage_status = new_status if new_status else None
    db.commit()

    return {"id": pi_id, "storage_status": db_pi.storage_status}

@router.get("/price-history/{customer_id}/{product_id}")
def read_price_history(customer_id: int, product_id: int, db: Session = Depends(get_db)):
    history = get_price_history(db, customer_id, product_id)
    if history is None:
        return {"message": "暂无历史价格记录"}
    return {
        "unit_price": history.unit_price,
        "remark": history.remark,
        "created_at": history.created_at
    }

# 2026-06-15 新增：获取PI下所有订单项
@router.get("/{pi_id}/items")
def read_pi_items(pi_id: int, db: Session = Depends(get_db)):
    """获取PI下的所有订单项"""
    from models import PiProformaInvoiceItem, PiProformaInvoice, CrmCustomer
    # Phase 4: 统一产品访问
    from services.product_lookup import unified_product_lookup

    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[获取订单项-API] pi_id={pi_id}")

    items = db.query(PiProformaInvoiceItem).filter(
        PiProformaInvoiceItem.pi_id == pi_id
    ).all()

    logger.info(f"[获取订单项-API] 查询到 {len(items)} 个订单项")

    result = []
    for item in items:
        # 获取关联的产品信息（Phase 4: 统一查找）
        product = None
        product_name = ""
        model = ""
        customer_name = ""
        if item.product_id:
            product = unified_product_lookup(db, item.product_id)
            if product:
                # 2026-06-23 修复：优先使用 product_name，与产品管理列表保持一致
                product_name = product.product_name or product.detail_desc or ""

        # 获取PI信息
        pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
        pi_no = pi.pi_no if pi else ""
        if pi and pi.customer_id:
            customer = db.query(CrmCustomer).filter(CrmCustomer.id == pi.customer_id).first()
            if customer:
                customer_name = customer.customer_name or ""
        
        # 获取已出货数量
        shipped_quantity = 0.0
        # TODO: 从出货表计算已出货数量
        
        result.append({
            "id": item.id,
            "pi_id": item.pi_id,
            "pi_no": pi_no,
            "product_id": item.product_id,
            "product_name": product_name or item.detail_desc or "",
            "model": item.customer_code or item.customer_model or "",
            "customer_name": customer_name,
            "quantity": float(item.quantity) if item.quantity else 0,
            "shipped_quantity": shipped_quantity,
            "unit_price": float(item.unit_price) if item.unit_price else 0,
        })
    
    return result


# 2026-06-10 新增：PI订单项API
@router.get("/items/{item_id}")
def read_pi_item(item_id: int, db: Session = Depends(get_db)):
    """获取PI订单项详情"""
    item = get_pi_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="订单项不存在")
    return {
        "id": item.id,
        "pi_id": item.pi_id,
        "product_id": item.product_id,
        "oe_number": item.oe_number,
        "customer_code": item.customer_code,
        "detail_desc": item.detail_desc,
        "quantity": float(item.quantity) if item.quantity else 0,
        "unit_price": float(item.unit_price) if item.unit_price else 0,
    }

@router.put("/items/{item_id}")
def update_pi_item_api(item_id: int, update_data: dict, db: Session = Depends(get_db)):
    """更新PI订单项"""

    # 🔧 2026-06-22 修复：使用 ASCII 避免 Windows GBK 终端的 UnicodeEncodeError
    print(f"\n{'='*60}")
    print(f"[DEBUG-API] === update_pi_item_api CALLED ===")
    print(f"[DEBUG-API] item_id: {item_id}")
    print(f"[DEBUG-API] field count: {len(update_data)}")
    print(f"[DEBUG-API] field list: {list(update_data.keys())}")

    # 检查关键字段是否存在
    key_fields = ['packaging', 'purchase_option_name', 'pack_spec',
                  'customer_prepayment', 'factory_deposit']
    for field in key_fields:
        if field in update_data:
            print(f"[DEBUG-API] [OK] key field '{field}' = {update_data[field]}")
        else:
            print(f"[DEBUG-API] [MISSING] field '{field}'")
    
    print(f"{'='*60}\n")
    
    db_item = update_pi_item(db, item_id, update_data)
    if not db_item:
        raise HTTPException(status_code=404, detail="订单项不存在")
    
    # 🔍 DEBUG: 返回更新后的数据以便前端验证
    return {
        "success": True,
        "id": db_item.id,
        "product_id": db_item.product_id,
        "message": "订单项更新成功",
        # ✅ 新增：返回关键字段值供验证
        "debug_fields": {
            "detail_desc": getattr(db_item, 'detail_desc', None),
            "packaging": getattr(db_item, 'packaging', None),
            "purchase_option_name": getattr(db_item, 'purchase_option_name', None),
            "pack_spec": getattr(db_item, 'pack_spec', None),
        }
    }


# 2026-06-12 需求#40：软删除 / 入库接口
class InboundSingleRequest(BaseModel):
    quantity: float
    inspector: Optional[str] = None
    remark: Optional[str] = None

class InboundBatchRequest(BaseModel):
    items: list[dict]  # [{"pi_item_id": int, "quantity": float, "remark": str}]
    inspector: Optional[str] = None

@router.delete("/items/{item_id}")
def delete_pi_item_api(item_id: int, db: Session = Depends(get_db)):
    """软删除 PI 单品"""
    item = delete_pi_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在或已删除")
    return {"success": True, "item_id": item_id}

@router.post("/items/{item_id}/inbound")
def inbound_pi_item_api(item_id: int, body: InboundSingleRequest, db: Session = Depends(get_db)):
    """单品入库"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[🌐ROUTER] POST /pi/items/{item_id}/inbound  payload: quantity={body.quantity}, inspector={body.inspector}, remark={body.remark!r}")
    try:
        inv = inbound_pi_item(db, item_id, body.quantity, body.inspector, body.remark)
        logger.info(f"[🌐ROUTER] ✅ POST /pi/items/{item_id}/inbound  returned inventory_log_id={inv.id}")
        return {"success": True, "inventory_log_id": inv.id}
    except ValueError as e:
        logger.error(f"[🌐ROUTER] ❌ POST /pi/items/{item_id}/inbound  ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{pi_id}/inbound-batch")
def inbound_pi_items_batch_api(pi_id: int, body: InboundBatchRequest, db: Session = Depends(get_db)):
    """批量入库"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[🌐ROUTER] POST /pi/{pi_id}/inbound-batch  items_count={len(body.items)}, inspector={body.inspector}")
    for i, it in enumerate(body.items):
        logger.info(f"[🌐ROUTER]   item[{i}]: {it}")
    result = inbound_pi_items_batch(db, pi_id, body.items, body.inspector)
    logger.info(f"[🌐ROUTER] ✅ POST /pi/{pi_id}/inbound-batch  result: {result}")
    return {"success": True, **result}


# ============== 2026-06-12 需求#42：历史记录 + 正式纪录 API ==============
class SaveSnapshotRequest(BaseModel):
    change_desc: Optional[str] = ""
    version_no: int

class VersionsResponse(BaseModel):
    id: int
    pi_id: int
    version_no: int
    change_desc: Optional[str]
    created_at: str

@router.get("/{pi_id}/versions", response_model=list[VersionsResponse])
def get_versions(pi_id: int, db: Session = Depends(get_db)):
    """获取 PI 所有历史版本"""
    versions = get_pi_versions(db, pi_id)
    return [
        VersionsResponse(
            id=v.id, pi_id=v.pi_id, version_no=v.version_no,
            change_desc=v.change_desc,
            created_at=v.created_at.isoformat() if v.created_at else "",
        )
        for v in versions
    ]


@router.get("/{pi_id}/versions/{version_id}/snapshot")
def get_version_snapshot(pi_id: int, version_id: int, db: Session = Depends(get_db)):
    """获取指定版本的完整快照数据"""
    from models.pi import PiProformaInvoiceVersion
    
    version = db.query(PiProformaInvoiceVersion).filter(
        PiProformaInvoiceVersion.id == version_id,
        PiProformaInvoiceVersion.pi_id == pi_id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")
    
    return {
        "id": version.id,
        "pi_id": version.pi_id,
        "version_no": version.version_no,
        "change_desc": version.change_desc,
        "created_at": version.created_at.isoformat() if version.created_at else "",
        "created_by": version.created_by,
        "snapshot": version.snapshot_data
    }


@router.post("/{pi_id}/versions")
def save_version(pi_id: int, body: SaveSnapshotRequest, db: Session = Depends(get_db)):
    """保存新快照（乐观锁）"""
    try:
        v = save_pi_snapshot(db, pi_id, body.change_desc, body.version_no)
        return {"success": True, "version_no": v.version_no}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/{pi_id}/formal-record")
def save_formal(pi_id: int, db: Session = Depends(get_db)):
    """保存正式纪录（JSON 文件）"""
    try:
        path = save_formal_record(db, pi_id)
        return {"success": True, "file_path": path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{pi_id}/formal-record")
def get_formal(pi_id: int, db: Session = Depends(get_db)):
    """读取正式纪录"""
    pi = get_pi_invoice(db, pi_id)
    if not pi:
        raise HTTPException(status_code=404, detail="PI 不存在")
    data = load_formal_record(pi.pi_no)
    if not data:
        raise HTTPException(status_code=404, detail="正式纪录不存在")
    return data

@router.get("/{pi_id}/formal-record/exists")
def formal_exists(pi_id: int, db: Session = Depends(get_db)):
    """检查正式纪录是否存在"""
    pi = get_pi_invoice(db, pi_id)
    if not pi:
        return {"exists": False}
    return {"exists": formal_record_exists(pi.pi_no)}

