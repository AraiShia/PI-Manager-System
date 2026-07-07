"""采购重构客户端测试"""
from unittest.mock import MagicMock
import pytest
import os
import sys

# 强制使用 PySide6 offscreen 渲染（与其他客户端测试一致）
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# 让 client/ 内的导入能找到 api/, services/, widgets/
CLIENT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLIENT_ROOT)


def test_get_recent_1688_urls_calls_api_with_product_id_and_limit():
    """get_recent_1688_urls 应调 /purchase/1688?product_id=...&limit=..."""
    from api.client import ApiClient
    api = MagicMock(spec=ApiClient)
    api.get.return_value = [
        {"id": 1, "product_url": "https://detail.1688.com/a/1.html"},
        {"id": 2, "product_url": "https://detail.1688.com/a/2.html"},
    ]

    # 调用待实现方法
    result = ApiClient.get_recent_1688_urls(api, product_id=42, limit=5)

    # 应调 api.get 走 /purchase/1688
    api.get.assert_called_once()
    args, kwargs = api.get.call_args
    assert args[0] == "/purchase/1688"
    # 应传 product_id 和 limit 查询参数
    assert kwargs.get("params", {}).get("product_id") == 42
    assert kwargs.get("params", {}).get("limit") == 5
    # 返回 URL 列表
    assert result == [
        "https://detail.1688.com/a/1.html",
        "https://detail.1688.com/a/2.html",
    ]


def test_get_recent_1688_urls_default_limit():
    """默认 limit 应为 5"""
    from api.client import ApiClient
    api = MagicMock(spec=ApiClient)
    api.get.return_value = []
    ApiClient.get_recent_1688_urls(api, product_id=42)
    args, kwargs = api.get.call_args
    assert kwargs.get("params", {}).get("limit") == 5


def test_get_recent_1688_urls_filters_empty_urls():
    """空 product_url 应被过滤掉"""
    from api.client import ApiClient
    api = MagicMock(spec=ApiClient)
    api.get.return_value = [
        {"id": 1, "product_url": "https://detail.1688.com/a/1.html"},
        {"id": 2, "product_url": ""},
        {"id": 3, "product_url": None},
        {"id": 4, "product_url": "https://detail.1688.com/a/4.html"},
    ]
    result = ApiClient.get_recent_1688_urls(api, product_id=42, limit=10)
    assert result == [
        "https://detail.1688.com/a/1.html",
        "https://detail.1688.com/a/4.html",
    ]


def test_purchase_dialog_stores_prefill_urls(qapp):
    """PurchaseDialog 接受 prefill_urls 形参并存储为实例属性"""
    from widgets.purchase_dialog import PurchaseDialog

    api = MagicMock()
    items = [{"product_id": 42, "detail_desc": "测试产品"}]
    prefill = {42: ["https://detail.1688.com/a/1.html", "https://detail.1688.com/a/2.html"]}

    dialog = PurchaseDialog(api, items=items, prefill_urls=prefill)

    assert dialog._prefill_urls == prefill


def test_purchase_dialog_prefill_urls_default_empty(qapp):
    """PurchaseDialog 不传 prefill_urls 时默认为空 dict"""
    from widgets.purchase_dialog import PurchaseDialog

    api = MagicMock()
    items = [{"product_id": 42, "detail_desc": "测试产品"}]

    dialog = PurchaseDialog(api, items=items)

    assert dialog._prefill_urls == {}


def test_purchase_dialog_link_combo_is_combobox_editable(qapp):
    """1688 链接控件应改为可编辑 QComboBox"""
    from widgets.purchase_dialog import PurchaseDialog
    from PySide6.QtWidgets import QComboBox

    api = MagicMock()
    items = [{"product_id": 42, "detail_desc": "测试产品"}]

    dialog = PurchaseDialog(api, items=items)

    assert isinstance(dialog.link_combo, QComboBox)
    assert dialog.link_combo.isEditable() is True


def test_order_detail_panel_emit_purchase_single(qapp):
    """右键未采产品行选'采购该产品'应发射 purchaseSingleRequested"""
    from widgets.order_summary import OrderDetailPanel

    api = MagicMock()
    panel = OrderDetailPanel(api)
    panel.show_order_detail(
        order={"pi_no": "TEST-1", "currency": "USD"},
        items=[
            {"product_id": 1, "is_temporary": False, "supplier_name": None},
            {"product_id": 2, "is_temporary": False, "supplier_name": "ACME"},
            {"product_id": 3, "is_temporary": True,  "supplier_name": None},
        ],
    )

    captured = []
    panel.purchaseSingleRequested.connect(lambda r: captured.append(r))
    panel.purchaseRepurchaseRequested.connect(lambda r: captured.append(("repurchase", r)))

    # 第 0 行：未采非临时 -> 采购该产品 可用
    menu0 = panel._build_context_menu(0)
    assert menu0 is not None
    actions = menu0.actions()
    assert actions[0].text() == "采购该产品"
    assert actions[0].isEnabled() is True
    assert actions[1].text() == "重新采购"
    assert actions[1].isEnabled() is False
    actions[0].trigger()
    assert captured == [0]

    # 第 1 行：已采非临时 -> 采购该产品 灰，重新采购 可用
    menu1 = panel._build_context_menu(1)
    actions1 = menu1.actions()
    assert actions1[0].isEnabled() is False
    assert actions1[1].isEnabled() is True
    actions1[1].trigger()
    assert ("repurchase", 1) in captured

    # 第 2 行：临时 -> 两项都灰
    menu2 = panel._build_context_menu(2)
    actions2 = menu2.actions()
    assert actions2[0].isEnabled() is False
    assert actions2[1].isEnabled() is False


def test_order_detail_panel_top_button_text(qapp):
    """顶部按钮文案应改为『采购全部』"""
    from widgets.order_summary import OrderDetailPanel

    api = MagicMock()
    panel = OrderDetailPanel(api)
    assert panel._purchase_btn.text() == "采购全部"


def test_prefill_1688_urls_returns_map(qapp):
    """_prefill_1688_urls 应返回 {product_id: [urls]} 的 map"""
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    api.get_recent_1688_urls.side_effect = lambda product_id, limit=5: {
        1: ["https://a.com/1", "https://a.com/2"],
        2: ["https://a.com/3"],
    }.get(product_id, [])

    tab = OrderSummaryTab(api, main_window=None)
    items = [
        {"product_id": 1, "is_temporary": False},
        {"product_id": 2, "is_temporary": False},
    ]

    result = tab._prefill_1688_urls(items)
    assert result == {
        1: ["https://a.com/1", "https://a.com/2"],
        2: ["https://a.com/3"],
    }
    # 每个 product 各调一次
    assert api.get_recent_1688_urls.call_count == 2


def test_prefill_1688_urls_skips_items_without_product_id(qapp):
    """_prefill_1688_urls 应跳过没有 product_id 的项"""
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    api.get_recent_1688_urls.return_value = []
    tab = OrderSummaryTab(api, main_window=None)
    items = [
        {"product_id": None, "is_temporary": True},
        {"product_id": 5, "is_temporary": False},
    ]
    result = tab._prefill_1688_urls(items)
    assert 5 in result
    assert None not in result
    assert api.get_recent_1688_urls.call_count == 1


def test_on_purchase_all_clicked_opens_dialog_with_all_items(qapp, monkeypatch):
    """_on_purchase_all_clicked 应使用全部 items 打开 PurchaseDialog"""
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    api.get_recent_1688_urls.return_value = []
    tab = OrderSummaryTab(api, main_window=None)
    tab._current_order = {"id": 100, "pi_no": "TEST-1"}
    tab._detail_panel._current_items = [
        {"product_id": 1, "is_temporary": False, "supplier_name": None},
        {"product_id": 2, "is_temporary": False, "supplier_name": None},
    ]
    tab._detail_panel._current_order = tab._current_order

    captured = {}
    class FakeDialog:
        def __init__(self, api, items, parent=None, dept_id=None, pi_id=None, prefill_urls=None):
            captured["items"] = items
            captured["prefill_urls"] = prefill_urls
            captured["dept_id"] = dept_id
            captured["pi_id"] = pi_id
            self.purchase_completed = MagicMock()
        def exec(self):
            return 0
    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", FakeDialog)

    tab._on_purchase_all_clicked()
    assert len(captured["items"]) == 2
    assert captured["prefill_urls"] == {1: [], 2: []}


def test_on_purchase_single_clicked_opens_dialog_with_one_item(qapp, monkeypatch):
    """_on_purchase_single_clicked 应只用对应行 item 打开对话框"""
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    api.get_recent_1688_urls.return_value = ["https://a.com/old"]
    tab = OrderSummaryTab(api, main_window=None)
    tab._current_order = {"id": 100, "pi_no": "TEST-1"}
    tab._detail_panel._current_items = [
        {"product_id": 1, "is_temporary": False, "supplier_name": None},
        {"product_id": 2, "is_temporary": False, "supplier_name": "ACME"},
    ]
    tab._detail_panel._current_order = tab._current_order

    captured = {}
    class FakeDialog:
        def __init__(self, api, items, parent=None, dept_id=None, pi_id=None, prefill_urls=None):
            captured["items"] = items
            captured["prefill_urls"] = prefill_urls
            self.purchase_completed = MagicMock()
        def exec(self):
            return 0
    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", FakeDialog)

    tab._on_purchase_single_clicked(0)
    # 仅传入 1 个 item
    assert len(captured["items"]) == 1
    assert captured["items"][0]["product_id"] == 1
    # 预填该 product_id 的 URL
    assert captured["prefill_urls"] == {1: ["https://a.com/old"]}


def test_on_purchase_single_clicked_invalid_row(qapp, monkeypatch):
    """非法行索引应直接返回，不开对话框"""
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    tab = OrderSummaryTab(api, main_window=None)
    tab._detail_panel._current_items = [{"product_id": 1}]
    tab._current_order = {"id": 1}

    opened = {"count": 0}
    class FakeDialog:
        def __init__(self, *a, **kw):
            opened["count"] += 1
            self.purchase_completed = MagicMock()
        def exec(self):
            return 0
    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", FakeDialog)

    tab._on_purchase_single_clicked(99)  # 越界
    assert opened["count"] == 0


def test_on_purchase_repurchase_clicked_requires_confirm(qapp, monkeypatch):
    """重新采购：先弹确认框，确认后打开对话框"""
    from PySide6.QtWidgets import QMessageBox
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    api.get_recent_1688_urls.return_value = []
    tab = OrderSummaryTab(api, main_window=None)
    tab._current_order = {"id": 100, "pi_no": "TEST-1"}
    item = {"product_id": 1, "is_temporary": False, "supplier_name": "ACME"}
    tab._detail_panel._current_items = [item]
    tab._detail_panel._current_order = tab._current_order

    opened = {"count": 0}
    captured = {}

    def make_dialog(tag):
        class _F:
            def __init__(self, api, items, parent=None, dept_id=None, pi_id=None, prefill_urls=None):
                if tag == "real":
                    captured["items"] = items
                    captured["prefill_urls"] = prefill_urls
                opened["count"] += 1
                self.purchase_completed = MagicMock()
            def exec(self):
                return 0
        return _F

    # 第一次拒绝 → 不开对话框
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question",
                        lambda *a, **k: QMessageBox.StandardButton.No)
    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", make_dialog("noop"))
    tab._on_purchase_repurchase_clicked(0)
    assert opened["count"] == 0

    # 第二次确认 → 开对话框，传入同一行
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", make_dialog("real"))
    tab._on_purchase_repurchase_clicked(0)
    assert opened["count"] == 1
    assert len(captured["items"]) == 1
    assert captured["items"][0]["supplier_name"] == "ACME"


def test_detail_panel_purchase_signals_connected_to_tab_slots(qapp, monkeypatch):
    """详情面板的三个 purchase 信号应连接 tab 槽函数（任务 8）"""
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    api.get_recent_1688_urls.return_value = []
    tab = OrderSummaryTab(api, main_window=None)
    tab._current_order = {"id": 100, "pi_no": "TEST-1"}
    tab._detail_panel._current_items = [
        {"product_id": 1, "is_temporary": False, "supplier_name": None},
        {"product_id": 2, "is_temporary": False, "supplier_name": "ACME"},
    ]
    tab._detail_panel._current_order = tab._current_order

    opened = {"count": 0}

    def make_dialog():
        class _F:
            def __init__(self, *a, **kw):
                opened["count"] += 1
                self.purchase_completed = MagicMock()
            def exec(self):
                return 0
        return _F

    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", make_dialog())

    # 顶部按钮 → purchaseRequested → _on_purchase_all_clicked → 2 个 item
    tab._detail_panel.purchaseRequested.emit()
    assert opened["count"] == 1

    # 单产品右键 → purchaseSingleRequested(row) → 1 个 item
    tab._detail_panel.purchaseSingleRequested.emit(0)
    assert opened["count"] == 2

    # 重采购右键 → purchaseRepurchaseRequested(row) → 弹确认
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question",
                        lambda *a, **k: __import__("PySide6").QtWidgets.QMessageBox.StandardButton.Yes)
    tab._detail_panel.purchaseRepurchaseRequested.emit(1)
    assert opened["count"] == 3


def test_purchase_completed_signal_propagated(qapp, monkeypatch):
    """PurchaseDialog.purchase_completed → tab.purchaseCompleted（任务 8 透传）"""
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QDialog
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    api.get_recent_1688_urls.return_value = []
    tab = OrderSummaryTab(api, main_window=None)
    tab._current_order = {"id": 1}
    tab._detail_panel._current_items = [{"product_id": 1, "is_temporary": False}]
    tab._detail_panel._current_order = tab._current_order

    captured = []
    tab.purchaseCompleted.connect(lambda data: captured.append(data))

    class FakeDialog(QDialog):
        purchase_completed = Signal(dict)
        def __init__(self, *a, **kw):
            super().__init__()
        def exec(self):
            self.purchase_completed.emit({"ok": True})
            return 0
    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", FakeDialog)

    tab._on_purchase_all_clicked()
    assert captured == [{"ok": True}]


# ============== 任务 10：集成测试 ==============

def test_integration_end_to_end_all_three_flows(qapp, monkeypatch):
    """集成测试：三种采购入口（顶部全部 / 右键采购该产品 / 右键重新采购）最终都打开 PurchaseDialog 并透传 purchaseCompleted"""
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QDialog
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    # 历史 1688 URL 仓库（按 product_id 索引）
    url_map = {1: ["https://a.com/p1-old"], 2: ["https://a.com/p2-old"], 3: []}
    api.get_recent_1688_urls.side_effect = lambda pid, limit=5: url_map.get(pid, [])

    tab = OrderSummaryTab(api, main_window=None)
    tab._current_order = {"id": 99, "pi_no": "PI-INTEG-1"}
    items = [
        {"product_id": 1, "is_temporary": False, "supplier_name": "ACME"},
        {"product_id": 2, "is_temporary": False, "supplier_name": None},
        {"product_id": 3, "is_temporary": True,  "supplier_name": None},
    ]
    tab._detail_panel._current_items = items
    tab._detail_panel._current_order = tab._current_order

    # 收集对话框调用
    calls = []
    class FakeDialog(QDialog):
        purchase_completed = Signal(dict)
        def __init__(self, api, items, parent=None, dept_id=None, pi_id=None, prefill_urls=None):
            super().__init__()
            calls.append({
                "items": items,
                "prefill_urls": prefill_urls,
                "pi_id": pi_id,
            })
        def exec(self):
            self.purchase_completed.emit({"ok": True, "items_count": len(calls[-1]["items"])})
            return 0
    monkeypatch.setattr("widgets.purchase_dialog.PurchaseDialog", FakeDialog)

    # 订阅 tab 透传的完成信号
    completed = []
    tab.purchaseCompleted.connect(lambda d: completed.append(d))

    # 1) 顶部『采购全部』
    tab._on_purchase_all_clicked()
    assert len(calls) == 1
    assert len(calls[0]["items"]) == 3
    assert calls[0]["prefill_urls"] == {1: ["https://a.com/p1-old"], 2: ["https://a.com/p2-old"], 3: []}
    assert calls[0]["pi_id"] == 99
    assert completed[-1] == {"ok": True, "items_count": 3}

    # 2) 右键『采购该产品』row=1
    tab._on_purchase_single_clicked(1)
    assert len(calls) == 2
    assert len(calls[1]["items"]) == 1
    assert calls[1]["items"][0]["product_id"] == 2
    assert calls[1]["prefill_urls"] == {2: ["https://a.com/p2-old"]}

    # 3) 右键『重新采购』row=0（确认）
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question",
                        lambda *a, **k: __import__("PySide6").QtWidgets.QMessageBox.StandardButton.Yes)
    tab._on_purchase_repurchase_clicked(0)
    assert len(calls) == 3
    assert calls[2]["items"][0]["supplier_name"] == "ACME"

    # 三次都触发了 purchaseCompleted
    assert len(completed) == 3


def test_integration_signal_wired_at_construction(qapp):
    """集成：构造 OrderSummaryTab 后，三个购买信号应已连接到 tab 内部槽（任务 8）"""
    from widgets.order_summary.order_summary_tab import OrderSummaryTab

    api = MagicMock()
    tab = OrderSummaryTab(api, main_window=None)

    # 反射：tab 应有这些槽/信号
    assert hasattr(tab, "_on_purchase_all_clicked")
    assert hasattr(tab, "_on_purchase_single_clicked")
    assert hasattr(tab, "_on_purchase_repurchase_clicked")
    assert hasattr(tab, "purchaseCompleted")

    # 验证连接：detail_panel 的信号应连接到 tab 的槽
    dp = tab._detail_panel
    # Qt 中 connection 的反射：直接发射后观察副作用
    api.get_recent_1688_urls.return_value = []
    tab._current_order = {"id": 1}
    tab._detail_panel._current_items = [{"product_id": 1, "is_temporary": False, "supplier_name": None}]
    tab._detail_panel._current_order = tab._current_order
    # 通过发射信号后看是否调用到 _on_purchase_all_clicked（用 api 调用次数验证）
    api.get_recent_1688_urls.reset_mock()
    try:
        dp.purchaseRequested.emit()
    except Exception:
        # 可能因 PurchaseDialog 缺失等失败，这里只关心 signal 是否有响应（即 _on_purchase_all_clicked 被调用）
        pass
    # _prefill_1688_urls 应至少调用了一次 get_recent_1688_urls
    assert api.get_recent_1688_urls.called
