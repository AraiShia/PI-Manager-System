"""导出API路由"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import List

from schemas.export import PreviewResponse
from exporters import PIExporter, CIExporter, PLExporter, PurchaseExporter, ContractExporter
from exporters.export_helper import inject_salesman_info

router = APIRouter(prefix="/api/export", tags=["导出"])


def get_db_session():
    """获取数据库会话"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        return db
    finally:
        pass


# ========== PI导出 ==========

@router.get("/pi/{pi_id}/preview")
def preview_pi(pi_id: int, db=None):
    """获取PI预览数据"""
    try:
        if db is None:
            db = get_db_session()

        from crud.pi import get_pi_invoice_detail
        pi_data = get_pi_invoice_detail(db, pi_id)
        if not pi_data:
            raise HTTPException(status_code=404, detail="PI单不存在")

        items = pi_data.get("items", [])
        return PreviewResponse(
            summary={
                "customer_name": pi_data.get("customer_name", ""),
                "total_amount": pi_data.get("total_amount", 0),
                "currency": pi_data.get("currency", "USD"),
                "items_count": len(items),
            },
            items=[{
                "product_name": item.get("product_name", ""),
                "quantity": item.get("quantity", 0),
                "unit_price": item.get("unit_price", 0),
            } for item in items],
            validation_errors=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pi/{pi_id}")
def export_pi(pi_id: int, format: str = "template"):
    """导出PI模板"""
    try:
        db = get_db_session()

        from crud.pi import get_pi_invoice_detail
        pi_data = get_pi_invoice_detail(db, pi_id)
        if not pi_data:
            raise HTTPException(status_code=404, detail="PI单不存在")

        exporter = PIExporter()
        excel_bytes = exporter.export_pi(pi_data, db)

        filename = f"PI_{pi_data.get('pi_no', pi_id)}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== CI导出 ==========

@router.get("/shipment/{shipment_id}/ci/preview")
def preview_ci(shipment_id: int, db=None):
    """获取CI预览数据"""
    try:
        if db is None:
            db = get_db_session()

        from crud.shipment import get_shipment_detail
        shipment_data = get_shipment_detail(db, shipment_id)
        if not shipment_data:
            raise HTTPException(status_code=404, detail="出货单不存在")

        items = shipment_data.get("items", [])
        return PreviewResponse(
            summary={
                "customer_name": shipment_data.get("customer_name", ""),
                "total_amount": shipment_data.get("total_amount", 0),
                "items_count": len(items),
            },
            items=[{
                "product_name": item.get("product_name", ""),
                "quantity": item.get("quantity", 0),
                "unit_price": item.get("unit_price", 0),
            } for item in items],
            validation_errors=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shipment/{shipment_id}/ci")
def export_ci(shipment_id: int):
    """导出CI商业发票"""
    try:
        db = get_db_session()

        from crud.shipment import get_shipment_detail
        shipment_data = get_shipment_detail(db, shipment_id)
        if not shipment_data:
            raise HTTPException(status_code=404, detail="出货单不存在")

        exporter = CIExporter()
        excel_bytes = exporter.export_ci(shipment_data)

        filename = f"CI_{shipment_data.get('shipment_no', shipment_id)}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== PL导出 ==========

@router.get("/shipment/{shipment_id}/pl")
def export_pl(shipment_id: int):
    """导出PL装箱单"""
    try:
        db = get_db_session()

        from crud.shipment import get_shipment_detail
        shipment_data = get_shipment_detail(db, shipment_id)
        if not shipment_data:
            raise HTTPException(status_code=404, detail="出货单不存在")

        exporter = PLExporter()
        excel_bytes = exporter.export_pl(shipment_data)

        filename = f"PL_{shipment_data.get('shipment_no', shipment_id)}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 采购合同导出 ==========

@router.get("/purchase/{po_id}/contract")
def export_purchase_contract(po_id: int):
    """导出国内采购合同（基于模板）"""
    try:
        db = get_db_session()

        from crud.purchase import get_purchase_order_detail
        purchase_data = get_purchase_order_detail(db, po_id)
        if not purchase_data:
            raise HTTPException(status_code=404, detail="采购单不存在")

        # 注入业务员信息到采购合同数据
        inject_salesman_info(purchase_data, db)

        # 使用基于模板的 ContractExporter
        exporter = ContractExporter()
        excel_bytes = exporter.export_contract(purchase_data)

        filename = f"Contract_{purchase_data.get('po_no', po_id)}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 批量导出 ==========

@router.post("/batch")
def batch_export(type: str, ids: List[int]):
    """批量导出"""
    # TODO: 实现批量导出逻辑
    return {"message": "Batch export not implemented yet"}