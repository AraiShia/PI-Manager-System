from crud.customer_product import _generate_temp_system_code, create_customer_product
from models.customer_product import PrdCustomerProduct
from schemas.customer_product import CustomerProductCreate


def test_generate_temp_system_code(db, customer_factory):
    customer = customer_factory(customer_code="A01")
    code1 = _generate_temp_system_code(db, customer.customer_code)
    assert code1.startswith("TMP-A01-")

    # 模拟已占用一个临时编号后再生成下一个
    db.add(PrdCustomerProduct(customer_id=customer.id, system_code=code1))
    db.commit()

    code2 = _generate_temp_system_code(db, customer.customer_code)
    assert code2.startswith("TMP-A01-")
    assert code1 != code2


def test_create_customer_product_uses_temp_code(db, customer_factory):
    customer = customer_factory(customer_code="B02")
    data = CustomerProductCreate(customer_id=customer.id, product_name="测试产品")
    cp = create_customer_product(db, data)
    assert cp.system_code.startswith("TMP-B02-")
