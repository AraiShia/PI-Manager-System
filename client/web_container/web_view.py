"""QWebEngineView 封装：Vue SPA 容器"""
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QUrl
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

        # 用 Qt 官方 API 禁用原生菜单，但页面 JS 的 contextmenu 事件不受影响
        print("[WebContainer] disabling native context menu via Qt API")
        self.page().settings().setAttribute(
            QWebEngineSettings.WebAttribute.ContextMenuEnabled, False
        )

        # 保留默认 page，安装自定义 channel
        self.channel = QWebChannel(self)
        self.page().setWebChannel(self.channel)

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
