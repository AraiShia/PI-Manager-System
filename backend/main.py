from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi import Request
from fastapi.exceptions import RequestValidationError
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from app.database import engine, Base
from routers import customer_router, supplier_router, pi_router
from routers.purchase import router as purchase_router
from routers.shipment import router as shipment_router
from routers.inventory import router as inventory_router
from routers.payment import router as payment_router
from routers.quote import router as quote_router
from routers.product_category import router as category_router
from routers.image import router as image_router
from routers.auth import router as auth_router
from routers.customer_reply import router as customer_reply_router
from routers.customer_product import router as customer_product_router
from routers.product_compat import router as product_compat_router
from routers.setting import router as setting_router
from routers.memo_record import router as memo_router
from routers.order_file import router as order_file_router
from routers.purchase_package import router as purchase_package_router
from routers.order_import import router as order_import_router, product_router as order_product_router
from routers.export import router as export_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PI订单管理系统", 
    version="1.0.0",
    limit_max_request_size=500 * 1024 * 1024  # 500MB
)

# 全局验证错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"\n[DEBUG] ===== Validation Error =====")
    print(f"[DEBUG] URL: {request.url}")
    print(f"[DEBUG] Method: {request.method}")
    print(f"[DEBUG] Error details:")
    for error in exc.errors():
        print(f"  - {error}")
    print(f"[DEBUG] Request body: {exc.body}")
    print(f"[DEBUG] =============================\n")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customer_router)
app.include_router(supplier_router)
app.include_router(pi_router)
app.include_router(purchase_router)
app.include_router(shipment_router)
app.include_router(inventory_router)
app.include_router(payment_router)
app.include_router(quote_router)
app.include_router(category_router, prefix="/api/product-categories", tags=["product-categories"])
app.include_router(image_router, prefix="/api/images", tags=["images"])
app.include_router(auth_router)
app.include_router(customer_reply_router)
app.include_router(customer_product_router)
app.include_router(product_compat_router)
app.include_router(setting_router)
app.include_router(memo_router)
app.include_router(order_file_router)
app.include_router(purchase_package_router)
app.include_router(export_router)

# 订单导入相关路由（router已自带prefix：/orders, /products）
app.include_router(order_import_router, prefix="/api")
app.include_router(order_product_router, prefix="/api")

static_dir = os.path.join(base_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 挂载图片上传目录
uploads_dir = os.path.join(base_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=uploads_dir), name="images")

@app.get("/")
async def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "PI订单管理系统 API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
