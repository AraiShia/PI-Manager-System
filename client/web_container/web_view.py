"""QWebEngineView 封装：Vue SPA 容器"""
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QUrl, QEvent
from PySide6.QtGui import QContextMenuEvent
from .channel_bridge import NativeBridge
from .native_api import NativeAPI


def build_web_url(remote_url: str, path: str) -> str:
    """构建 Web 容器 URL，自动去除重复斜杠并拒绝外部跳转。"""
    if path.startswith('//') or not path.startswith('/'):
        raise ValueError('Web 容器只允许站内路径')
    return f"{remote_url.rstrip('/')}{path}"


class WebContainerView(QWebEngineView):
    """Vue SPA 容器，通过 QWebChannel 与 Vue 通信"""

    def __init__(self, remote_url: str = None, parent=None):
        super().__init__(parent)
        if remote_url:
            self.remote_url = remote_url.rstrip('/')
        else:
            # 从本地配置读取前端地址
            try:
                from config.local_settings_manager import get_frontend_url
                self.remote_url = get_frontend_url().rstrip('/')
            except Exception as e:
                print(f"[WebContainer] 读取前端地址失败: {e}")
                self.remote_url = "https://piapi.wakabashia.tj.cn"

        print("[WebContainer] eventFilter will suppress native context menu")

        # 在 page 上安装 eventFilter，拦截 QEvent.Type.ContextMenu
        # 在 QWebEnginePage 层级捕捉并 accept()，比 QWebEngineView 更早拦截 Chromium 菜单
        self.page().installEventFilter(self)

        self.channel = QWebChannel(self)
        self.page().setWebChannel(self.channel)

        self._native_api = NativeAPI(self)
        self._native_bridge = NativeBridge(self._native_api)
        self.channel.registerObject('nativeBridge', self._native_bridge)

        self.load(QUrl(self.remote_url))

    def eventFilter(self, watched, event: QEvent) -> bool:
        """在 QWebEnginePage 层级拦截 ContextMenu 事件，阻止 Chromium 原生菜单弹出。

        QWebEnginePage 处理 ContextMenu 比 QWebEngineView 更早，
        在此处 accept() 能在 Chromium 弹出菜单前拦截，
        但仍允许事件继续派发到页面 JS，前端 contextmenu 监听器可收到。
        """
        if event.type() == QEvent.Type.ContextMenu:
            ev = event
            print(
                f"[WebContainer] eventFilter ContextMenu at "
                f"{ev.globalPos().x()},{ev.globalPos().y()} reason={ev.reason()}"
            )
            ev.accept()
            return True  # 拦截，不传递给 Chromium
        return super().eventFilter(watched, event)

    def navigate_to(self, path: str):
        """路由跳转"""
        self.load(QUrl(build_web_url(self.remote_url, path)))

    def reload_current(self):
        """刷新当前页面"""
        self.reload()

    @property
    def native_bridge(self) -> NativeBridge:
        return self._native_bridge
