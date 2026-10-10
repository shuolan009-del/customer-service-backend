# infrastructure/xmov/__init__.py
"""
魔珐星云（Xmov Xingyun）具身智能 3D 数字人对接包。

设计取舍：
1. 不编造官方接口规格 —— 官方公开文档只描述了前端 JS SDK（XmovAvatar），
   后端 REST 接口未公开。因此本包把「可确认的部分」做扎实，
   把「未知的部分」显式声明为占位符并集中在一个文件里，便于官方文档到手后替换。
2. 密钥不出后端 —— AppSecret 默认只在服务端拼接，客户端只拿到短期会话令牌。
"""
from infrastructure.xmov.config import XmovConfig, load_xmov_config
from infrastructure.xmov.errors import (
    XmovError,
    XmovNotEnabledError,
    XmovAuthError,
    XmovSignatureError,
    XmovTimeoutError,
    XmovUpstreamError,
)
from infrastructure.xmov.client import XmovClient, xmov_client

__all__ = [
    "XmovConfig",
    "load_xmov_config",
    "XmovClient",
    "xmov_client",
    "XmovError",
    "XmovNotEnabledError",
    "XmovAuthError",
    "XmovSignatureError",
    "XmovTimeoutError",
    "XmovUpstreamError",
]