from .product import router as product_router
from .customer import router as customer_router
from .supplier import router as supplier_router
from .pi import router as pi_router
from .customer_reply import router as customer_reply_router

__all__ = [
    'product_router',
    'customer_router',
    'supplier_router',
    'pi_router',
    'customer_reply_router'
]
