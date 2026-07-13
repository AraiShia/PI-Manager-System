"""QWebEngineView 封装：Vue SPA 容器"""
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QUrl, QObject
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

        # 不设置 NoContextMenu：该策略会拦截右键事件，导致页面 JS 收不到 contextmenu
        # 通过 createStandardContextMenu 返回空菜单，仅屏蔽浏览器原生菜单
        print("[WebContainer] standard context menu suppressed; frontend contextmenu enabled")

        self.channel = QWebChannel(self)
        self.page().setWebChannel(self.channel)

        self._native_api = NativeAPI(self)
        self._native_bridge = NativeBridge(self._native_api)
        self.channel.registerObject('nativeBridge', self._native_bridge)

        self.load(QUrl(self.remote_url))

    def createStandardContextMenu(self):
        """禁用浏览器原生右键菜单，但不吞掉页面内的 contextmenu 事件。"""
        return None

    def navigate_to(self, path: str):
        """路由跳转"""
        self.load(QUrl(build_web_url(self.remote_url, path)))

    def reload_current(self):
        """刷新当前页面"""
        self.reload()

    @property
    def native_bridge(self) -> NativeBridge:
        return self._native_bridge
