"""Web 容器模块：QWebEngineView + QWebChannel 桥接"""
from .web_view import WebContainerView
from .channel_bridge import NativeBridge

__all__ = ['WebContainerView', 'NativeBridge']
