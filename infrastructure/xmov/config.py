# infrastructure/xmov/config.py
"""
魔珐星云配置装载与安全校验。

核心设计取舍：
- 密钥只从环境变量（.env）读取，绝不硬编码，也绝不写进任何前端可访问的文件。
- 提供 enabled 开关：未配置账号时整条链路自动降级，不影响原有对话功能。
- 提供 sanitize / masked 方法，用于日志和接口回显时脱敏。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from conf.config import settings

logger = logging.getLogger(__name__)

# AppSecret 在日志中只保留的字符数（用于排障时核对是否为同一密钥）
_SECRET_HEAD = 4
_SECRET_TAIL = 4


@dataclass(frozen=True)
class XmovConfig:
    """魔珐星云运行期配置（不可变）。"""

    enabled: bool
    app_id: str | None
    app_secret: str | None
    gateway_server: str
    api_base: str
    js_sdk_url: str
    default_avatar_id: str
    timeout_seconds: float
    max_retries: int
    allow_secret_to_client: bool

    @property
    def credentials_ready(self) -> bool:
        """凭据是否齐备。"""
        return bool(self.app_id) and bool(self.app_secret)

    @property
    def usable(self) -> bool:
        """真正可用：开关打开 且 凭据齐备。"""
        return self.enabled and self.credentials_ready

    def masked_secret(self) -> str:
        """脱敏后的 AppSecret，可安全写日志。"""
        if not self.app_secret:
            return "<empty>"
        s = self.app_secret
        if len(s) <= _SECRET_HEAD + _SECRET_TAIL:
            return "*" * len(s)
        return f"{s[:_SECRET_HEAD]}{'*' * (len(s) - _SECRET_HEAD - _SECRET_TAIL)}{s[-_SECRET_TAIL:]}"

    def masked_app_id(self) -> str:
        """脱敏后的 App ID，可安全写日志。"""
        if not self.app_id:
            return "<empty>"
        a = self.app_id
        if len(a) <= 8:
            return a[:2] + "*" * max(len(a) - 2, 0)
        return f"{a[:4]}{'*' * (len(a) - 8)}{a[-4:]}"


def load_xmov_config() -> XmovConfig:
    """从全局 settings（其数据源为 .env / 环境变量）构造配置对象。"""
    cfg = XmovConfig(
        enabled=bool(getattr(settings, "xmov_enabled", False)),
        app_id=getattr(settings, "xmov_app_id", None),
        app_secret=getattr(settings, "xmov_app_secret", None),
        gateway_server=str(getattr(settings, "xmov_gateway_server", "")).strip(),
        api_base=str(getattr(settings, "xmov_api_base", "")).strip().rstrip("/"),
        js_sdk_url=str(getattr(settings, "xmov_js_sdk_url", "")).strip(),
        default_avatar_id=str(getattr(settings, "xmov_default_avatar_id", "default")).strip(),
        timeout_seconds=float(getattr(settings, "xmov_timeout_seconds", 15.0)),
        max_retries=int(getattr(settings, "xmov_max_retries", 2)),
        allow_secret_to_client=bool(getattr(settings, "xmov_allow_secret_to_client", False)),
    )

    if cfg.enabled and not cfg.credentials_ready:
        logger.warning(
            "[xmov] 已开启 xmov_enabled，但缺少 XMOV_APP_ID / XMOV_APP_SECRET，"
            "数字人能力将不可用。"
        )
    if cfg.allow_secret_to_client:
        logger.warning(
            "[xmov] xmov_allow_secret_to_client=True：AppSecret 会被下发给浏览器，"
            "仅可用于本地演示，生产环境务必关闭。"
        )
    return cfg