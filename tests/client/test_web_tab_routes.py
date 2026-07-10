"""Web 容器路由测试"""
import pytest
from client.web_container.web_view import build_web_url


def test_build_web_url_joins_base_and_route():
    assert build_web_url("https://example.com/", "/products") == "https://example.com/products"


def test_build_web_url_keeps_query_string():
    assert build_web_url("https://example.com", "/orders?pi_no=PI001") == "https://example.com/orders?pi_no=PI001"


def test_build_web_url_rejects_external_route():
    import pytest
    with pytest.raises(ValueError, match="站内路径"):
        build_web_url("https://example.com", "https://evil.example")


from client.web_container.routes import TAB_ROUTES


def test_tab_routes_cover_main_menu():
    assert list(TAB_ROUTES) == [
        'products', 'customers', 'suppliers', 'quotes', 'pi', 'purchase',
        'shipment', 'customer_payment', 'supplier_payment', 'inventory',
        'order_summary',
    ]


def test_tab_routes_use_final_server_paths():
    assert TAB_ROUTES['products'] == '/products'
    assert TAB_ROUTES['shipment'] == '/shipments'
    assert TAB_ROUTES['customer_payment'] == '/payments/customer'
    assert TAB_ROUTES['order_summary'] == '/orders'
