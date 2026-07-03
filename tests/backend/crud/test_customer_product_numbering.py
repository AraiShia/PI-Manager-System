from crud.customer_product import _generate_temp_system_code
from models.customer_product import PrdCustomerProduct


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
