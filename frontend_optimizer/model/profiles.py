"""模型档位 -> 具体模型的映射表。

⚠️ 当前为「只搭架构、不写模型」状态：
   所有槽位都是 None，router 会在真正调用时报错，提示补齐配置。

两个预置能力档位与方案文档 §1 / §6 完全一致：
    - reasoning -> 高性能模型
    - fast      -> 轻量模型
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from frontend_optimizer.model.slots import ModelSlot


class ModelProfile(BaseModel):
    """一个模型档位的配置（provider 与 model 待填）。"""

    provider: str | None = None   # 例如 "openai" / "anthropic" / "dashscope"
    model: str | None = None      # 具体模型名，留空
    base_url: str | None = None   # 兼容 OpenAI 协议的自定义网关
    temperature: float = 0.0      # 前端代码生成建议低温，保证可复现
    extra: dict = Field(default_factory=dict)

    @property
    def configured(self) -> bool:
        """是否已配置可用的 provider + model。"""
        return bool(self.provider and self.model)


# 待配置的槽位表。补齐时只改这里，不触碰编排逻辑。
MODEL_PROFILES: dict[ModelSlot, ModelProfile] = {
    ModelSlot.REASONING: ModelProfile(),  # TODO 待填：高性能模型
    ModelSlot.FAST: ModelProfile(),       # TODO 待填：轻量模型
}
