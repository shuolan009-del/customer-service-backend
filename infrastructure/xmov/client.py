# infrastructure/xmov/client.py
"""
魔珐星云统一接口调用层。

职责：
- 统一的请求构造（URL、请求头、序列化、鉴权）
- 超时控制、指数退避重试
- 错误归一化（把 HTTP/网络异常转换成 errors.py 中的语义异常）
- 响应解析（统一剥壳，提取业务数据）

=== 架构事实（已核对官方文档 developers/52-183，非推测）===

1. 数字人的「驱动」全部发生在浏览器端，由官方 JS SDK 完成：
   speak() / idle() / interactiveidle() / offlineMode() / onlineMode() / setVolume() …
   官方文档明确未暴露这些能力的后端接口。因此本客户端**不提供**驱动类接口。

2. 官方公开的后端接口只有消耗查询：
   GET  https://nebula-agent.xingyun3d.com/user/v1/external/consume_record
   鉴权头：X-APP-ID / X-TOKEN / X-TIMESTAMP

3. 因此本层的定位是：
   - 安全地保管凭据（不下发到浏览器）
   - 提供真实可用的后端接口（消耗查询）
   - 作为未来官方开放更多接口时的唯一扩展点
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from infrastructure.xmov.config import XmovConfig, load_xmov_config
from infrastructure.xmov.errors import (
    XmovAuthError,
    XmovError,
    XmovNotEnabledError,
    XmovSignatureError,
    XmovTimeoutError,
    XmovUpstreamError,
    XmovValidationError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 官方已确认的后端接口路径（来源：官方文档「消耗查询」章节）
# ---------------------------------------------------------------------------
_PATH_CONSUME_RECORD = "/user/v1/external/consume_record"

#: 可重试的 HTTP 状态码
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

#: 官方业务错误码中表示「签名错误」的值（实测确认）
_SIGNATURE_CODES = {4}


class XmovClient:
    """魔珐星云客户端。一个实例内部维护一个连接池。"""

    def __init__(self, config: XmovConfig | None = None) -> None:
        self._config = config or load_xmov_config()
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ 基础设施

    @property
    def config(self) -> XmovConfig:
        return self._config

    async def _get_client(self) -> httpx.AsyncClient:
        """懒加载 httpx 客户端（避免在未启用数字人时也占用连接）。"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self._config.timeout_seconds),
                        follow_redirects=True,
                    )
        return self._client

    async def aclose(self) -> None:
        """关闭连接池。在应用 lifespan 退出时调用。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------ 请求构造

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._config.api_base}{path}"

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """
        构造请求头。

        鉴权方式来源：官方文档「消耗查询」章节的请求参数表
            X-APP-ID    ：驱动应用 appid
            X-TOKEN     ：驱动应用 appsecret
            X-TIMESTAMP ：时间戳

        ⚠️ 实测证据（2026-10-07，本机真实请求）：
            GET /user/v1/external/consume_record
            → HTTP 200 {"error_code":4,"error_reason":"签名错误"}

        这说明：网关可达、AppID 被识别，但**仅有 X-TOKEN 直传是不够的**，
        上游还要求对请求做「签名」。签名算法官方公开文档未给出，
        故此处留出 _sign() 挂载点（见下），接入官方算法即可，
        调用方与路由层无需任何改动。
        """
        timestamp = self._timestamp()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-APP-ID": self._config.app_id or "",
            "X-TOKEN": self._config.app_secret or "",
            "X-TIMESTAMP": timestamp,
        }
        # 预留签名挂载点：官方算法到手后在 _sign() 内实现
        signature = self._sign(timestamp)
        if signature:
            headers["X-SIGN"] = signature
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _timestamp() -> str:
        """毫秒时间戳。若上游提示时间戳问题，改为 int(time.time()) 即可。"""
        return str(int(time.time() * 1000))

    def _sign(self, timestamp: str) -> str | None:
        """
        请求签名。

        ⚠️ 当前返回 None —— 因为官方公开文档未给出签名算法，且实测返回
        {"error_code":4,"error_reason":"签名错误"}，证实签名是必需的。

        需要补充的信息：签名算法（常见形态可能是
        md5(appId + timestamp + appSecret) 或 HMAC-SHA256，但**未经证实，切勿猜测上线**）。
        拿到官方说明后，在此实现并返回签名串即可，其余代码无需改动。
        """
        return None

    def _ensure_usable(self) -> None:
        if not self._config.enabled:
            raise XmovNotEnabledError("数字人能力未启用（xmov_enabled=False）")
        if not self._config.credentials_ready:
            raise XmovNotEnabledError("缺少 XMOV_APP_ID / XMOV_APP_SECRET 配置")

    # ------------------------------------------------------------------ 核心请求

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        expect_json: bool = True,
    ) -> Any:
        """
        统一请求入口：含超时、重试、错误归一化、响应解析。

        :return: 解析后的响应体（dict / list / str）
        :raises XmovNotEnabledError / XmovAuthError / XmovTimeoutError / XmovUpstreamError
        """
        self._ensure_usable()
        url = self._build_url(path)
        client = await self._get_client()

        last_error: XmovError | None = None
        attempts = self._config.max_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                logger.debug("[xmov] %s %s (attempt %d/%d)", method, url, attempt, attempts)
                response = await client.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                    headers=self._build_headers(headers),
                )
            except httpx.TimeoutException as exc:
                last_error = XmovTimeoutError(
                    f"请求魔珐星云超时（{self._config.timeout_seconds}s）", detail=str(exc)
                )
            except httpx.HTTPError as exc:
                last_error = XmovUpstreamError("请求魔珐星云失败", detail=str(exc))
            else:
                # ---- 状态码归一化 ----
                if response.status_code in (401, 403):
                    raise XmovAuthError(
                        "魔珐星云鉴权失败，请核对 App ID / App Secret（X-APP-ID / X-TOKEN）",
                        detail=self._safe_body(response),
                    )
                if response.status_code in _RETRYABLE_STATUS:
                    last_error = XmovUpstreamError(
                        f"魔珐星云返回可重试状态码 {response.status_code}",
                        detail=self._safe_body(response),
                    )
                elif response.status_code >= 400:
                    raise XmovUpstreamError(
                        f"魔珐星云返回错误状态码 {response.status_code}",
                        detail=self._safe_body(response),
                    )
                else:
                    return self._parse_response(response, expect_json)

            # 到这里说明本轮失败，判断是否需要退避重试
            if not last_error.retryable or attempt >= attempts:
                break
            backoff = min(2 ** (attempt - 1) * 0.5, 4.0)  # 0.5s, 1s, 2s, 最多 4s
            logger.warning("[xmov] %s，%.1fs 后重试", last_error, backoff)
            await asyncio.sleep(backoff)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _safe_body(response: httpx.Response) -> object:
        """尽量取响应体用于排障，但不因为解析失败而抛出新异常。"""
        try:
            return response.json()
        except Exception:  # noqa: BLE001 - 排障用途，任何解析失败都降级为文本
            return response.text[:500]

    @staticmethod
    def _parse_response(response: httpx.Response, expect_json: bool) -> Any:
        """
        响应解析。

        官方「消耗查询」返回结构为：
            { "error_code": int, "error_reason": str, "data": [ ... ] }
        与常见的 {code, data, msg} 略有不同（用 error_code / error_reason），
        因此这里对两种命名都做兼容，并优先识别 error_code。
        """
        if not expect_json:
            return response.text
        try:
            payload = response.json()
        except ValueError as exc:
            raise XmovUpstreamError("魔珐星云返回了非 JSON 响应", detail=response.text[:500]) from exc

        if isinstance(payload, dict):
            # 官方风格：error_code / error_reason
            if "error_code" in payload:
                code = payload.get("error_code")
                if str(code) not in {"0", "200"}:
                    reason = payload.get("error_reason")
                    if code in _SIGNATURE_CODES:
                        raise XmovSignatureError(
                            f"魔珐星云签名校验失败（error_code={code}）",
                            detail=(
                                f"{reason}｜需要在 XmovClient._sign() 中实现官方签名算法，"
                                "算法请向星云官方索取"
                            ),
                        )
                    raise XmovUpstreamError(
                        f"魔珐星云业务错误 error_code={code}", detail=reason
                    )
                return payload.get("data", payload)

            # 通用风格：code / message
            code = payload.get("code", payload.get("status"))
            if code is not None and str(code) not in {"0", "200", "success", "SUCCESS"}:
                raise XmovUpstreamError(
                    f"魔珐星云业务错误 code={code}",
                    detail=payload.get("message") or payload.get("msg"),
                )
            if "data" in payload:
                return payload["data"]
        return payload

    # ------------------------------------------------------------------ 具体能力

    async def ping(self) -> dict[str, Any]:
        """
        连通性与凭据探活（可安全调用）。

        设计取舍：不假设接口返回结构，只判断网关是否有 HTTP 响应；
        真正的鉴权结果取决于官方接口，这里如实回传状态码与片段供人工判断。
        """
        self._ensure_usable()
        client = await self._get_client()
        try:
            response = await client.get(
                self._config.gateway_server, headers=self._build_headers()
            )
        except httpx.TimeoutException as exc:
            raise XmovTimeoutError("探测魔珐星云网关超时", detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise XmovUpstreamError("探测魔珐星云网关失败", detail=str(exc)) from exc

        return {
            "reachable": True,
            "status_code": response.status_code,
            "gateway_server": self._config.gateway_server,
            "app_id_masked": self._config.masked_app_id(),
            "note": "仅表示网络可达；业务鉴权需以官方接口返回为准。",
        }

    async def consume_record(self) -> list[dict[str, Any]]:
        """
        查询积分消耗记录（官方已确认接口）。

        接口：GET /user/v1/external/consume_record
        鉴权：X-APP-ID / X-TOKEN / X-TIMESTAMP
        返回：记录列表，字段含 task_id / session_id / amount（积分消耗）/
              status / start_time / finish_time / duration

        典型用途：确认数字人会话消耗了多少积分，避免额度失控。
        """
        data = await self.request("GET", _PATH_CONSUME_RECORD)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        if not isinstance(data, list):
            return []
        return data


#: 全局单例，供 FastAPI 依赖注入使用（与项目 infrastructure/http_client.py 的写法保持一致）
xmov_client = XmovClient()