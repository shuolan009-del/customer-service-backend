# api/routers/avatar_router.py
"""
魔珐星云数字人路由。

架构事实（已核对官方文档 developers/52-183）：
- 数字人「驱动」（说话/待机/离线）全部在浏览器端由官方 JS SDK 完成，
  官方未暴露后端驱动接口 → 本路由**不提供** /speak、/video/tasks 这类伪造接口。
- 官方公开的后端接口只有消耗查询 → 本路由提供 /consume-record。
- 后端主要职责：安全保管凭据、下发 SDK 初始化配置、查询用量。

设计取舍：
- 独立 router，不碰 chat_router，保证原有对话链路零风险。
- 只做「参数校验 + 调 client + 组装响应」，业务逻辑不在此层堆积。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.schemas_xmov import (
    AvatarSessionRequest,
    AvatarSessionResponse,
    AvatarStatusResponse,
    ConsumeRecordItem,
    ConsumeRecordResponse,
    DriveGuideResponse,
    PingResponse,
)
from infrastructure.xmov import XmovError, xmov_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/avatar", tags=["数字人 · 魔珐星云"])


def _handle_xmov_error(exc: XmovError) -> HTTPException:
    """把语义化异常翻译成合适的 HTTP 状态码，避免所有错误都变成 500。"""
    from infrastructure.xmov import (
        XmovAuthError,
        XmovNotEnabledError,
        XmovSignatureError,
        XmovTimeoutError,
    )

    if isinstance(exc, XmovNotEnabledError):
        return HTTPException(status_code=503, detail=f"数字人能力不可用：{exc.message}")
    if isinstance(exc, XmovAuthError):
        return HTTPException(status_code=502, detail=f"数字人鉴权失败：{exc.message}")
    if isinstance(exc, XmovSignatureError):
        return HTTPException(
            status_code=501,
            detail=(
                f"{exc.message}｜官方要求请求签名，但公开文档未给出算法；"
                f"请在 infrastructure/xmov/client.py 的 _sign() 中实现。({exc.detail})"
            ),
        )
    if isinstance(exc, XmovTimeoutError):
        return HTTPException(status_code=504, detail=f"数字人服务超时：{exc.message}")
    return HTTPException(status_code=502, detail=f"数字人服务异常：{exc.message}")


@router.get("/status", response_model=AvatarStatusResponse, summary="查询数字人能力状态")
async def avatar_status() -> AvatarStatusResponse:
    """
    查询是否已正确配置魔珐星云。

    典型用途：前端决定要不要显示数字人入口；部署后自检配置是否生效。
    """
    cfg = xmov_client.config
    return AvatarStatusResponse(
        enabled=cfg.enabled,
        credentials_ready=cfg.credentials_ready,
        usable=cfg.usable,
        app_id_masked=cfg.masked_app_id(),
        gateway_server=cfg.gateway_server,
        js_sdk_url=cfg.js_sdk_url,
        default_avatar_id=cfg.default_avatar_id,
        secret_to_client_allowed=cfg.allow_secret_to_client,
    )


@router.get("/ping", response_model=PingResponse, summary="探测星云网关连通性")
async def avatar_ping() -> PingResponse:
    """探测网关是否可达（不做业务鉴权判定）。"""
    try:
        data = await xmov_client.ping()
    except XmovError as exc:
        raise _handle_xmov_error(exc) from exc
    return PingResponse(**data)


@router.post("/session", response_model=AvatarSessionResponse, summary="获取前端 SDK 初始化配置")
async def create_avatar_session(payload: AvatarSessionRequest | None = None) -> AvatarSessionResponse:
    """
    前端初始化 XmovAvatar 前调用本接口，拿到官方 SDK 所需的三个参数。

    官方 SDK 的 appSecret 是必填参数（见官方文档「创建实例」），
    因此若要在浏览器端初始化，必须由后端下发密钥 —— 这正是
    XMOV_ALLOW_SECRET_TO_CLIENT 开关的意义所在。
    """
    cfg = xmov_client.config
    if not cfg.usable:
        raise HTTPException(status_code=503, detail="数字人能力未启用或凭据缺失")

    avatar_id = (payload.avatar_id if payload else None) or cfg.default_avatar_id

    if not cfg.allow_secret_to_client:
        # 未开启下发时，仍然返回结构完整的响应，但密钥为 None，并给出明确提示
        notice = (
            "⚠️ XMOV_ALLOW_SECRET_TO_CLIENT=false，未下发 appSecret，前端无法直接初始化 SDK。"
            "若仅用于本地演示，可在 .env 中改为 true 并重启服务；"
            "生产环境请改用官方服务端方案或联系星云获取更安全的接入方式。"
        )
    else:
        notice = (
            "已下发 appSecret（演示模式）。请勿在生产环境开启此项；"
            "官方 SDK 文档提示部分方法仅支持 localhost 或 https 访问。"
        )

    return AvatarSessionResponse(
        app_id=cfg.app_id or "",
        app_secret=cfg.app_secret if cfg.allow_secret_to_client else None,
        gateway_server=cfg.gateway_server,
        js_sdk_url=cfg.js_sdk_url,
        avatar_id=avatar_id,
        notice=notice,
    )


@router.get("/drive-guide", response_model=DriveGuideResponse, summary="驱动能力使用指引")
async def drive_guide() -> DriveGuideResponse:
    """
    说明数字人驱动能力的正确使用方式。

    存在原因：官方驱动能力全在前端 SDK，后端无对应接口。
    与其伪造一个必然报错的 /speak，不如给出准确指引。
    """
    return DriveGuideResponse(
        mode="client-sdk",
        methods=[
            "speak(ssml, is_start, is_end)  控制数字人说话，支持流式",
            "idle()                        进入待机等待",
            "interactiveidle()             待机互动；可用于打断当前状态",
            "offlineMode() / onlineMode()  离线/在线模式切换",
            "setVolume(volume)             音量 0→1",
            "changeAvatarVisible(visible)  UI 层隐藏/显示数字人",
            "stopSession() / destroy()     断开会话 / 销毁实例",
        ],
        example=(
            "// 前端拿到 /api/avatar/session 的配置后\n"
            "const sdk = new XmovAvatar({ containerId:'#sdk', appId, appSecret, gatewayServer });\n"
            "await sdk.init({ onDownloadProgress: p => console.log(p) });\n"
            "sdk.speak('欢迎使用魔珐星云', true, true);"
        ),
        remark=(
            "1) speak 不允许连续多次调用，两次之间建议插入 interactiveidle()；"
            "2) onVoiceStateChange 会抛 voice_start / voice_end，可用于管理说话状态；"
            "3) 官方提示部分方法仅支持 localhost 或 https 访问；"
            "4) 长时间无互动时调 offlineMode() 可避免积分消耗。"
        ),
    )


@router.get("/consume-record", response_model=ConsumeRecordResponse, summary="查询积分消耗记录")
async def consume_record() -> ConsumeRecordResponse:
    """
    查询数字人会话的积分消耗（官方已确认的后端接口）。

    接口：GET /user/v1/external/consume_record
    鉴权：X-APP-ID / X-TOKEN / X-TIMESTAMP（由 client 层统一注入）

    典型用途：确认演示消耗了多少积分，避免额度失控。
    """
    try:
        raw_records = await xmov_client.consume_record()
    except XmovError as exc:
        raise _handle_xmov_error(exc) from exc

    items = []
    total = 0.0
    for item in raw_records:
        if not isinstance(item, dict):
            continue
        record = ConsumeRecordItem(**{k: v for k, v in item.items() if k in ConsumeRecordItem.model_fields})
        items.append(record)
        if isinstance(record.amount, (int, float)):
            total += float(record.amount)

    return ConsumeRecordResponse(count=len(items), total_amount=round(total, 4), records=items)