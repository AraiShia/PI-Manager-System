"""QWebEngineView 封装：Vue SPA 容器"""
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QUrl
from PySide6.QtGui import QContextMenuEvent
from .channel_bridge import NativeBridge
from .native_api import NativeAPI


def build_web_url(remote_url: str, path: str) -> str:
    """构建 Web 容器 URL，自动去除重复斜杠并拒绝外部跳转。"""
    if path.startswith('//') or not path.startswith('/'):
        raise ValueError('Web 容器只允许站内路径')
    return f"{remote_url.rstrip('/')}{path}"


class NoContextMenuPage(QWebEnginePage):
    """禁用 Chromium 原生 context menu，让事件传到页面 JS。

    Chromium 原生菜单在 QWebEnginePage::contextMenuEvent() 层弹出，
    早于 QWebEngineView::contextMenuEvent()。
    重写 QWebEnginePage.contextMenuEvent() 并 accept()，在更早层级拦截。
    """

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        # 吞掉原生菜单（不调用 super），Chromium 仍会在页面 JS 层
        # 触发 contextmenu 事件，前端监听器可正常收到。
        print(
            f"[WebContainer] QWebEnginePage.contextMenuEvent suppressed at "
            f"{event.globalPos().x()},{event.globalPos().y()} reason={event.reason()}"
        )
        event.accept()


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

        print("[WebContainer] NoContextMenuPage installed; frontend contextmenu will work")

        # 替换默认 page 为禁用原生菜单的 page
        custom_page = NoContextMenuPage(self.page().profile(), self)
        self.channel = QWebChannel(custom_page)
        custom_page.setWebChannel(self.channel)
        self.setPage(custom_page)

        self._native_api = NativeAPI(self)
        self._native_bridge = NativeBridge(self._native_api)
        self.channel.registerObject('nativeBridge', self._native_bridge)

        self.load(QUrl(self.remote_url))

    def navigate_to(self, path: str):
        """路由跳转"""
        self.load(QUrl(build_web_url(self.remote_url, path)))

    def reload_current(self):
        """刷新当前页面"""
        self.reload()

    @property
    def native_bridge(self) -> NativeBridge:
        return self._native_bridge
