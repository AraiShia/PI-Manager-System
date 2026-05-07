from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Request
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from app.database import engine, Base
from routers import product_router, customer_router, supplier_router, pi_router
from routers.purchase import router as purchase_router
from routers.shipment import router as shipment_router
from routers.inventory import router as inventory_router
from routers.payment import router as payment_router
from routers.quote import router as quote_router
from routers.product_category import router as category_router
from routers.image import router as image_router
from routers.auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PI订单管理系统", 
    version="1.0.0",
    limit_max_request_size=500 * 1024 * 1024  # 500MB
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_router)
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
