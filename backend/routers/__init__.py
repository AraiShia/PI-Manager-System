from .customer import router as customer_router
from .supplier import router as supplier_router
from .pi import router as pi_router
from .customer_reply import router as customer_reply_router
from .purchase_package import router as purchase_package_router

__all__ = [
    'customer_router',
    'supplier_router',
    'pi_router',
    'customer_reply_router',
    'purchase_package_router'
]
