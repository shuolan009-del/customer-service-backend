# infrastructure/xmov/errors.py
"""
魔珐星云调用的统一异常体系。

设计取舍：用少量、语义明确的异常类型，替代到处 if resp.status_code == xxx。
上层只需捕获 XmovError 即可兜住所有数字人相关故障，并在 errors.retryable 上做重试决策。
"""
from __future__ import annotations

#: 官方业务错误码 → 语义异常的映射（仅收录已实测确认的）
_SIGNATURE_CODES = {4}


class XmovError(Exception):
    """魔珐星云相关错误的基类。"""

    #: 是否属于可重试错误（网络抖动、限流、上游 5xx）
    retryable: bool = False

    def __init__(self, message: str, *, detail: object = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - 仅用于日志可读性
        if self.detail is None:
            return self.message
        return f"{self.message} | detail={self.detail!r}"


class XmovNotEnabledError(XmovError):
    """数字人能力未启用或凭据缺失。属于配置问题，重试无意义。"""


class XmovAuthError(XmovError):
    """鉴权失败（App ID / App Secret 无效，或令牌过期）。"""


class XmovTimeoutError(XmovError):
    """请求超时。"""

    retryable = True


class XmovUpstreamError(XmovError):
    """上游返回了非预期的状态码或响应体。"""

    retryable = True


class XmovValidationError(XmovError):
    """调用方入参不合法（本地校验即失败，不发起网络请求）。"""


class XmovSignatureError(XmovError):
    """
    签名校验失败。

    实测：GET /user/v1/external/consume_record 在仅传
    X-APP-ID / X-TOKEN / X-TIMESTAMP 时返回
    {"error_code":4,"error_reason":"签名错误"}

    即：官方除了凭据，还要求对请求签名。算法未在公开文档给出，
    需向官方索取后在 XmovClient._sign() 中实现。
    这属于配置/实现问题，重试无意义。
    """