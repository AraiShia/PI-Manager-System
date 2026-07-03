# ============================================================
# 订单导入服务 - 产品匹配器
# 文件：services/product_matcher.py
# 创建日期：2026-05-29
# 更新日期：2026-06-16 (Phase 5: 改用 PrdCustomerProduct)
# 用途：实现产品模糊匹配和多优先级匹配逻辑
# ============================================================

from typing import List, Optional
import logging
import time
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.customer import CrmCustomer
from models.customer_product import PrdCustomerProduct
from models.customer_product_oe import PrdCustomerProductOE

logger = logging.getLogger(__name__)


class ProductMatcher:
    """产品匹配器 - 实现多优先级匹配策略（Phase 5 改用 PrdCustomerProduct）"""

    MATCH_TYPE_EXACT = 'exact_customer_code'
    MATCH_TYPE_OE = 'oe_number'
    MATCH_TYPE_NAME = 'product_name'

    SCORE_EXACT = 100
    SCORE_OE = 80
    SCORE_NAME_MIN = 60
    SCORE_NAME_MAX = 79

    def __init__(self, db: Session):
        self.db = db

    def match_product(
        self,
        customer_id: int = None,
        customer_code: str = None,
        oe_number: str = None,
        product_name: str = None,
        limit: int = 5
    ) -> List[dict]:
        logger.info(
            "[ProductMatcher.match_product] 入参 customer_id=%s, customer_code=%s, oe_number=%s, product_name=%s, limit=%s",
            customer_id, customer_code, oe_number, product_name, limit,
        )
        start = time.perf_counter()
        matches = []

        # 优先级1：客户ID + 客户型号（最精确）
        if customer_code and customer_id:
            logger.debug("[ProductMatcher] 进入优先级1：客户ID+客户型号精确匹配")
            exact_match = self._match_by_customer_code(customer_id, customer_code)
            if exact_match:
                matches.extend(exact_match)
                logger.info("[ProductMatcher] 优先级1命中 %d 条", len(exact_match))

        # 优先级2：OE号匹配
        if oe_number and not any(m['match_type'] == self.MATCH_TYPE_EXACT for m in matches):
            logger.debug("[ProductMatcher] 进入优先级2：OE号匹配 oe=%s", oe_number)
            oe_matches = self._match_by_oe_number(oe_number, limit=limit)
            if oe_matches:
                matches.extend(oe_matches)
                logger.info("[ProductMatcher] 优先级2命中 %d 条", len(oe_matches))
            else:
                logger.info("[ProductMatcher] 优先级2未命中 oe=%s", oe_number)

        # 优先级3：产品名称模糊匹配
        if product_name and not any(m['match_type'] == self.MATCH_TYPE_EXACT for m in matches):
            logger.debug("[ProductMatcher] 进入优先级3：产品名称匹配 name=%s", product_name)
            name_matches = self._match_by_product_name(product_name, limit=limit)
            if name_matches:
                matches.extend(name_matches)
                logger.info("[ProductMatcher] 优先级3命中 %d 条", len(name_matches))
            else:
                logger.info("[ProductMatcher] 优先级3未命中 name=%s", product_name)

        matches = self._deduplicate_and_sort(matches)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[ProductMatcher.match_product] 完成 总匹配=%d, 耗时=%.2fms",
            len(matches), elapsed_ms,
        )
        if elapsed_ms > 300:
            logger.warning(
                "[ProductMatcher.match_product] 慢匹配 耗时=%.2fms（建议排查索引或结果集）",
                elapsed_ms,
            )
        return matches[:limit]

    def _match_by_customer_code(self, customer_id: int, customer_code: str) -> List[dict]:
        """优先级1：通过 customer_id + customer_model 精确匹配"""
        logger.debug(
            "[_match_by_customer_code] 查询 customer_id=%s, customer_model=%s",
            customer_id, customer_code,
        )
        try:
            # 直接匹配客户产品（customer_id + customer_model 唯一）
            cp = self.db.query(PrdCustomerProduct).filter(
                PrdCustomerProduct.customer_id == customer_id,
                PrdCustomerProduct.customer_model == customer_code
            ).first()

            if cp:
                logger.info(
                    "[_match_by_customer_code] 命中 product_id=%s, model=%s",
                    cp.id, cp.customer_model,
                )
                return [{
                    'product_id': cp.id,
                    'match_type': self.MATCH_TYPE_EXACT,
                    'match_score': self.SCORE_EXACT,
                    'detail_desc': cp.detail_desc,
                    'product_name': cp.product_name,
                    'oe_number': cp.customer_model,
                    'customer_model': cp.customer_model,
                    'customer_product_code': cp.customer_product_code,
                    'brand': cp.brand,
                    'product': cp,
                }]
            logger.info(
                "[_match_by_customer_code] 未命中 customer_id=%s, customer_model=%s",
                customer_id, customer_code,
            )
        except Exception as e:
            logger.exception(
                "[_match_by_customer_code] 异常 customer_id=%s, model=%s, err=%s",
                customer_id, customer_code, e,
            )
        return []

    def _match_by_oe_number(self, oe_number: str, limit: int = 5) -> List[dict]:
        """优先级2：通过 OE号/客户产品编号/系统编号 模糊匹配"""
        logger.debug("[_match_by_oe_number] oe=%s, limit=%s", oe_number, limit)
        try:
            keyword = oe_number
            # 同时匹配 customer_model、customer_product_code、system_code
            cps = self.db.query(PrdCustomerProduct).filter(
                (PrdCustomerProduct.customer_model.ilike(f"%{keyword}%")) |
                (PrdCustomerProduct.customer_product_code.ilike(f"%{keyword}%")) |
                (PrdCustomerProduct.system_code.ilike(f"%{keyword}%"))
            ).limit(limit).all()
            logger.debug("[_match_by_oe_number] customer_model/code/system 模糊命中 %d 条", len(cps))

            # 同时查 prd_customer_product_oe 关系表
            oe_results = self.db.query(PrdCustomerProductOE).filter(
                PrdCustomerProductOE.oe_number.ilike(f"%{keyword}%")
            ).limit(limit).all()
            logger.debug("[_match_by_oe_number] customer_product_oe 命中 %d 条", len(oe_results))

            product_ids = set()
            matches = []

            for cp in cps:
                if cp.id not in product_ids:
                    product_ids.add(cp.id)
                    # 匹配得分：优先按 customer_model 计算，其次 customer_product_code
                    score = self._calculate_oe_score(cp.customer_model, keyword)
                    if score == self.SCORE_OE and cp.customer_product_code and keyword.upper() in cp.customer_product_code.upper():
                        score = self._calculate_oe_score(cp.customer_product_code, keyword)
                    if score == self.SCORE_OE and cp.system_code and keyword.upper() in cp.system_code.upper():
                        score = self._calculate_oe_score(cp.system_code, keyword)
                    matches.append({
                        'product_id': cp.id,
                        'match_type': self.MATCH_TYPE_OE,
                        'match_score': score,
                        'detail_desc': cp.detail_desc,
                        'product_name': cp.product_name,
                        'oe_number': cp.customer_model,
                        'customer_model': cp.customer_model,
                        'customer_product_code': cp.customer_product_code,
                        'brand': cp.brand,
                        'product': cp,
                    })

            for oe in oe_results:
                if oe.customer_product_id not in product_ids:
                    product_ids.add(oe.customer_product_id)
                    cp = self.db.query(PrdCustomerProduct).filter(
                        PrdCustomerProduct.id == oe.customer_product_id
                    ).first()
                    if cp:
                        matches.append({
                            'product_id': cp.id,
                            'match_type': self.MATCH_TYPE_OE,
                            'match_score': self._calculate_oe_score(oe.oe_number, keyword),
                            'detail_desc': cp.detail_desc,
                            'product_name': cp.product_name,
                            'oe_number': cp.customer_model,
                            'customer_model': cp.customer_model,
                            'customer_product_code': cp.customer_product_code,
                            'brand': cp.brand,
                            'product': cp,
                        })

            logger.info("[_match_by_oe_number] 去重后命中 %d 条 oe=%s", len(matches), oe_number)
            return matches
        except Exception as e:
            logger.exception("[_match_by_oe_number] 异常 oe=%s, err=%s", oe_number, e)
            return []

    def _match_by_product_name(self, product_name: str, limit: int = 5) -> List[dict]:
        """优先级3：通过产品名称/描述/品牌模糊匹配"""
        logger.debug("[_match_by_product_name] name=%s, limit=%s", product_name, limit)
        try:
            keyword = product_name
            # SQLite 不支持 similarity()，退化为 LIKE 匹配
            cps = self.db.query(PrdCustomerProduct).filter(
                (PrdCustomerProduct.product_name.ilike(f"%{keyword}%")) |
                (PrdCustomerProduct.detail_desc.ilike(f"%{keyword}%")) |
                (PrdCustomerProduct.brand.ilike(f"%{keyword}%"))
            ).limit(limit).all()
            logger.debug("[_match_by_product_name] name/desc/brand 命中 %d 条", len(cps))

            matches = []
            for cp in cps:
                # 简单匹配度：命中关键字即 SCORE_NAME_MIN
                score = self.SCORE_NAME_MIN
                matches.append({
                    'product_id': cp.id,
                    'match_type': self.MATCH_TYPE_NAME,
                    'match_score': score,
                    'detail_desc': cp.detail_desc,
                    'product_name': cp.product_name,
                    'oe_number': cp.customer_model,
                    'customer_model': cp.customer_model,
                    'customer_product_code': cp.customer_product_code,
                    'brand': cp.brand,
                    'product': cp,
                })
            logger.info("[_match_by_product_name] 完成 命中=%d name=%s", len(matches), product_name)
            return matches
        except Exception as e:
            logger.exception("[_match_by_product_name] 异常 name=%s, err=%s", product_name, e)
            return []

    def _calculate_oe_score(self, product_oe: str, search_oe: str) -> float:
        """计算OE号匹配的相似度"""
        if not product_oe or not search_oe:
            logger.debug("[_calculate_oe_score] 入参有空值 product_oe=%r search_oe=%r", product_oe, search_oe)
            return self.SCORE_OE
        if product_oe.upper() == search_oe.upper():
            return self.SCORE_EXACT
        if product_oe.upper().startswith(search_oe.upper()):
            return self.SCORE_OE + 10
        if product_oe.upper().endswith(search_oe.upper()):
            return self.SCORE_OE + 5
        return self.SCORE_OE

    def _deduplicate_and_sort(self, matches: List[dict]) -> List[dict]:
        """去重并按匹配度排序"""
        seen_ids = set()
        unique_matches = []
        for match in matches:
            if match['product_id'] not in seen_ids:
                seen_ids.add(match['product_id'])
                unique_matches.append(match)
        unique_matches.sort(key=lambda x: x['match_score'], reverse=True)
        logger.debug("[_deduplicate_and_sort] 去重前=%d 去重后=%d", len(matches), len(unique_matches))
        return unique_matches

    def get_best_match(self, matches: List[dict]) -> Optional[dict]:
        best = matches[0] if matches else None
        if best:
            logger.info(
                "[get_best_match] 最优匹配 product_id=%s, score=%s, type=%s",
                best.get('product_id'), best.get('match_score'), best.get('match_type'),
            )
        else:
            logger.info("[get_best_match] 无匹配结果")
        return best


class CustomerMatcher:
    """客户匹配器"""

    MATCH_TYPE_CODE = 'customer_code'
    MATCH_TYPE_NAME = 'customer_name'

    def __init__(self, db: Session):
        self.db = db

    def match_customer(
        self,
        customer_code: str = None,
        customer_name: str = None,
        limit: int = 5
    ) -> List[dict]:
        logger.info(
            "[CustomerMatcher.match_customer] 入参 customer_code=%s, customer_name=%s, limit=%s",
            customer_code, customer_name, limit,
        )
        start = time.perf_counter()
        matches = []
        if customer_code:
            code_matches = self._match_by_code(customer_code)
            if code_matches:
                matches.extend(code_matches)
                logger.info("[CustomerMatcher] 编码匹配命中 %d 条", len(code_matches))
            else:
                logger.info("[CustomerMatcher] 编码未命中 code=%s", customer_code)
        if customer_name:
            name_matches = self._match_by_name(customer_name, limit=limit)
            if name_matches:
                matches.extend(name_matches)
                logger.info("[CustomerMatcher] 名称匹配命中 %d 条", len(name_matches))
            else:
                logger.info("[CustomerMatcher] 名称未命中 name=%s", customer_name)
        result = self._deduplicate_and_sort(matches)[:limit]
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[CustomerMatcher.match_customer] 完成 总匹配=%d, 耗时=%.2fms",
            len(result), elapsed_ms,
        )
        return result

    def _match_by_code(self, customer_code: str) -> List[dict]:
        logger.debug("[_match_by_code] code=%s", customer_code)
        try:
            customer = self.db.query(CrmCustomer).filter(
                CrmCustomer.customer_code == customer_code
            ).first()
            if customer:
                logger.info("[_match_by_code] 命中 customer_id=%s", customer.id)
                return [{
                    'customer_id': customer.id,
                    'match_type': self.MATCH_TYPE_CODE,
                    'match_score': 100,
                    'customer_name': customer.customer_name,
                    'customer_code': customer.customer_code,
                    'customer': customer,
                }]
        except Exception as e:
            logger.exception("[_match_by_code] 异常 code=%s, err=%s", customer_code, e)
        return []

    def _match_by_name(self, customer_name: str, limit: int = 5) -> List[dict]:
        logger.debug("[_match_by_name] name=%s, limit=%s", customer_name, limit)
        try:
            customers = self.db.query(CrmCustomer).filter(
                CrmCustomer.customer_name.ilike(f"%{customer_name}%")
            ).limit(limit).all()
            matches = []
            for customer in customers:
                matches.append({
                    'customer_id': customer.id,
                    'match_type': self.MATCH_TYPE_NAME,
                    'match_score': 60,
                    'customer_name': customer.customer_name,
                    'customer_code': customer.customer_code,
                    'customer': customer,
                })
            logger.info("[_match_by_name] 命中 %d 条 name=%s", len(matches), customer_name)
            return matches
        except Exception as e:
            logger.exception("[_match_by_name] 异常 name=%s, err=%s", customer_name, e)
            return []

    def _deduplicate_and_sort(self, matches: List[dict]) -> List[dict]:
        seen_ids = set()
        unique = []
        for m in matches:
            if m['customer_id'] not in seen_ids:
                seen_ids.add(m['customer_id'])
                unique.append(m)
        unique.sort(key=lambda x: x['match_score'], reverse=True)
        logger.debug("[CustomerMatcher._deduplicate] 去重前=%d 去重后=%d", len(matches), len(unique))
        return unique


class SupplierMatcher:
    """供应商匹配器"""

    def __init__(self, db: Session):
        self.db = db

    def match_supplier(
        self,
        supplier_name: str = None,
        factory_code: str = None,
        limit: int = 5
    ) -> List[dict]:
        logger.info(
            "[SupplierMatcher.match_supplier] 入参 supplier_name=%s, factory_code=%s, limit=%s",
            supplier_name, factory_code, limit,
        )
        start = time.perf_counter()
        matches = []
        if factory_code:
            code_matches = self._match_by_factory_code(factory_code)
            if code_matches:
                matches.extend(code_matches)
                logger.info("[SupplierMatcher] 工厂编号命中 %d 条", len(code_matches))
            else:
                logger.info("[SupplierMatcher] 工厂编号未命中 code=%s", factory_code)
        if supplier_name:
            name_matches = self._match_by_name(supplier_name, limit=limit)
            if name_matches:
                matches.extend(name_matches)
                logger.info("[SupplierMatcher] 名称匹配命中 %d 条", len(name_matches))
            else:
                logger.info("[SupplierMatcher] 名称未命中 name=%s", supplier_name)
        result = self._deduplicate_and_sort(matches)[:limit]
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[SupplierMatcher.match_supplier] 完成 总匹配=%d, 耗时=%.2fms",
            len(result), elapsed_ms,
        )
        return result

    def _match_by_factory_code(self, factory_code: str) -> List[dict]:
        logger.debug("[_match_by_factory_code] code=%s", factory_code)
        try:
            from models.supplier import SupSupplier
            supplier = self.db.query(SupSupplier).filter(
                SupSupplier.factory_code == factory_code
            ).first()
            if supplier:
                logger.info("[_match_by_factory_code] 命中 supplier_id=%s", supplier.id)
                return [{
                    'supplier_id': supplier.id,
                    'match_type': 'factory_code',
                    'match_score': 100,
                    'supplier_name': supplier.supplier_name,
                    'factory_code': supplier.factory_code,
                    'supplier': supplier,
                }]
        except Exception as e:
            logger.exception("[_match_by_factory_code] 异常 code=%s, err=%s", factory_code, e)
        return []

    def _match_by_name(self, supplier_name: str, limit: int = 5) -> List[dict]:
        logger.debug("[_match_by_name] name=%s, limit=%s", supplier_name, limit)
        try:
            from models.supplier import SupSupplier
            suppliers = self.db.query(SupSupplier).filter(
                SupSupplier.supplier_name.ilike(f"%{supplier_name}%")
            ).limit(limit).all()
            matches = []
            for supplier in suppliers:
                matches.append({
                    'supplier_id': supplier.id,
                    'match_type': 'supplier_name',
                    'match_score': 60,
                    'supplier_name': supplier.supplier_name,
                    'factory_code': supplier.factory_code,
                    'supplier': supplier,
                })
            logger.info("[_match_by_name] 命中 %d 条 name=%s", len(matches), supplier_name)
            return matches
        except Exception as e:
            logger.exception("[_match_by_name] 异常 name=%s, err=%s", supplier_name, e)
            return []

    def _deduplicate_and_sort(self, matches: List[dict]) -> List[dict]:
        seen_ids = set()
        unique = []
        for m in matches:
            if m['supplier_id'] not in seen_ids:
                seen_ids.add(m['supplier_id'])
                unique.append(m)
        unique.sort(key=lambda x: x['match_score'], reverse=True)
        logger.debug("[SupplierMatcher._deduplicate] 去重前=%d 去重后=%d", len(matches), len(unique))
        return unique
