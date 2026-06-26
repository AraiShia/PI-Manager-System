# -*- coding: utf-8 -*-
"""pi 相关 Dialog（延迟加载）

2026-06-23 修复：原代码 `from main import PIDialog as PID` 在 PIDialog.__init__ 里
实例化 main.PIDialog，而 main.PIDialog.__init__ 又实例化本类 → 无限递归
（RecursionError: maximum recursion depth exceeded）。

修复方案：本模块直接 `from main import PIDialog` 把 main.PIDialog 当成自己的类
（class 别名）。这样无论外部用 `from main import PIDialog` 还是
`from dialogs.pi import PIDialog`，拿到的都是**同一个类**——main.PIDialog
（真正的实现类，继承自 QDialog）。不再互相实例化。
"""
from main import PIDialog  # noqa: F401  (class alias; 真正的实现在 main.py)