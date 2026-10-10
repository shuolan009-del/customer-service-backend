# api/schemas_xmov.py
"""
魔珐星云数字人接口的出参 / 入参模型。

设计取舍：独立成文件，不修改既有 api/schemas.py，避免影响原有 /api/chat 契约（最小改动）。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AvatarStatusResponse(BaseModel):
    """数字人能力状态。"""

    enabled: bool = Field(description="功能开关是否打开")
    credentials_ready: bool = Field(description="App ID / App Secret 是否齐备")
    usable: bool = Field(description="是否真正可用（开关打开且凭据齐备）")
    app_id_masked: str = Field(description="脱敏后的 App ID")
    gateway_server: str = Field(description="会话网关地址（SDK 参数）")
    js_sdk_url: str = Field(description="官方 JS SDK 脚本地址")
    default_avatar_id: str = Field(description="默认形象标识")
    secret_to_client_allowed: bool = Field(description="是否允许下发密钥到浏览器（仅演示用）")
    drive_mode: str = Field(
        default="client-sdk",
        description="驱动方式：官方驱动能力在前端 SDK，后端不提供驱动接口",
    )


class AvatarSessionRequest(BaseModel):
    """前端初始化 SDK 前向后端索取会话配置。"""

    avatar_id: str | None = Field(default=None, description="形象标识，留空则用默认值")


class AvatarSessionResponse(BaseModel):
    """
    返回给前端的 SDK 初始化配置。

    安全约定：appSecret 默认恒为 None；仅当服务器显式开启
    xmov_allow_secret_to_client 时才会返回（本地演示用）。
    """

    app_id: str = Field(description="App ID（SDK 的 appId 参数）")
    app_secret: str | None = Field(
        default=None, description="App Secret，生产环境恒为 None（官方 SDK 要求前端传入，故演示模式才下发）"
    )
    gateway_server: str = Field(description="SDK 的 gatewayServer 参数")
    js_sdk_url: str = Field(description="SDK 脚本地址，前端可直接用它动态加载")
    avatar_id: str = Field(description="形象标识")
    notice: str = Field(description="给前端的使用提示")


class PingResponse(BaseModel):
    """连通性探活结果。"""

    reachable: bool
    status_code: int
    gateway_server: str
    app_id_masked: str
    note: str


class ConsumeRecordItem(BaseModel):
    """单条积分消耗记录（官方返回字段）。"""

    id: int | None = None
    task_id: str | None = None
    session_id: str | None = None
    amount: float | None = Field(default=None, description="积分消耗")
    status: int | None = None
    app_name: str | None = None
    app_id: str | None = None
    start_time: int | None = None
    finish_time: int | None = None
    duration: int | None = None


class ConsumeRecordResponse(BaseModel):
    """积分消耗查询结果。"""

    count: int = Field(description="记录条数")
    total_amount: float = Field(description="本次返回记录的积分消耗合计")
    records: list[ConsumeRecordItem] = Field(default_factory=list)


class DriveGuideResponse(BaseModel):
    """
    驱动能力使用指引。

    存在原因：官方数字人驱动（说话/待机/离线）全部在前端 SDK 完成，
    后端无对应接口，故提供本指引而非伪造接口。
    """

    mode: str = Field(default="client-sdk", description="固定为 client-sdk")
    methods: list[str] = Field(description="SDK 提供的驱动方法名")
    example: str = Field(description="前端调用示例")
    remark: str = Field(description="注意事项")