"""模拟 _preset_customer_id 时序问题"""
# 模拟场景
class MockCombo:
    def __init__(self):
        self.items = []
        self._enabled = True
        self._current = 0

    def addItem(self, text, data):
        self.items.append((text, data))

    def setCurrentIndex(self, i):
        self._current = i

    def currentIndex(self):
        return self._current

    def currentData(self):
        return self.items[self._current][1] if self._current < len(self.items) else None

    def setEnabled(self, b):
        self._enabled = b

    def count(self):
        return len(self.items)

    def itemData(self, i):
        return self.items[i][1] if i < len(self.items) else None


def simulate_init_ui(combo, customers, preset_customer_id, mode="confirm_temp"):
    """模拟 init_ui 中的客户下拉框初始化逻辑"""
    combo.addItem("-- 请选择客户 --", None)
    for c in customers:
        combo.addItem(c.get('customer_name', ''), c.get('id'))

    if mode == "confirm_temp" and preset_customer_id:
        found = False
        for i in range(combo.count()):
            if combo.itemData(i) == preset_customer_id:
                combo.setCurrentIndex(i)
                found = True
                break
        combo.setEnabled(False)  # 总是锁定
        return found
    return None


print("=== 场景A: customers 加载成功，找到匹配 ===")
combo = MockCombo()
found = simulate_init_ui(combo, [{"id": 100, "customer_name": "客户A"}], 100)
print(f"  currentData: {combo.currentData()}, enabled: {combo._enabled}, found: {found}")
print()

print("=== 场景B: customers 加载成功，customer_id 不在列表 ===")
combo = MockCombo()
found = simulate_init_ui(combo, [{"id": 100, "customer_name": "客户A"}], 999)
print(f"  currentData: {combo.currentData()}, enabled: {combo._enabled}, found: {found}")
print(f"  [BUG] 锁定但 currentData=None！用户无法选择")
print()

print("=== 场景C: customers 加载失败/为空 ===")
combo = MockCombo()
found = simulate_init_ui(combo, [], 100)
print(f"  currentData: {combo.currentData()}, enabled: {combo._enabled}, found: {found}")
print(f"  [BUG] 锁定但 currentData=None！用户无法选择")
