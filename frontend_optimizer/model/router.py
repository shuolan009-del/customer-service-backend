"""模型路由器：把任务档位解析为具体模型配置。

只做「解析 + 校验」；真正的模型调用由 orchestrator/handlers.py 注入实现。
"""
from __future__ import annotations

from frontend_optimizer.model.profiles import (
    MODEL_PROFILES,
    ModelProfile,
    describe_config,
    reload_profiles,
)
from frontend_optimizer.model.slots import ModelSlot


class ModelNotConfiguredError(RuntimeError):
    """模型档位尚未配置时抛出，避免静默使用错误模型。"""


class ModelRouter:
    """按档位取模型配置。"""

    def __init__(self, profiles: dict[ModelSlot, ModelProfile] | None = None) -> None:
        self._profiles = profiles if profiles is not None else MODEL_PROFILES

    def resolve(self, slot: ModelSlot) -> ModelProfile:
        """解析档位对应的模型配置；未配置则明确报错。"""
        profile = self._profiles.get(slot)
        if profile is None or not profile.configured:
            raise ModelNotConfiguredError(
                f"模型档位 {slot.value!r} 尚未配置 provider/model，"
                f"请在 .env 里设置 {'FRONTEND_OPTIMIZER_' + slot.value.upper() + '_MODEL'} "
                f"（或其 PROVIDER / BASE_URL / API_KEY），"
                f"或在 frontend_optimizer/model/profiles.py 的 RECOMMENDED_MODELS 中补齐。"
            )
        if not profile.resolved_base_url:
            raise ModelNotConfiguredError(
                f"模型档位 {slot.value!r} 缺少 base_url（provider={profile.provider!r} 无内置地址），"
                f"请设置 {'FRONTEND_OPTIMIZER_' + slot.value.upper() + '_BASE_URL'}"
                f"（或全局 FRONTEND_OPTIMIZER_BASE_URL）。"
            )
        return profile

    def resolve_with_fallback(
        self,
        slot: ModelSlot,
        fallback: ModelSlot = ModelSlot.REASONING,
    ) -> ModelProfile:
        """解析档位；该档位未配置时退回 fallback（用于可选的视觉档）。"""
        try:
            return self.resolve(slot)
        except ModelNotConfiguredError:
            if slot is fallback:
                raise
            return self.resolve(fallback)

    def available(self, slot: ModelSlot) -> bool:
        """该档位是否可用（不抛异常）。"""
        profile = self._profiles.get(slot)
        return bool(profile and profile.configured and profile.resolved_base_url)

    def describe(self) -> dict[str, str]:
        """返回各档位的可读状态，便于编排前自检 / 打印。"""
        return {slot.value: profile.label() for slot, profile in self._profiles.items()}

    def describe_lines(self) -> list[str]:
        """返回带 base_url / 密钥来源的详细配置摘要。"""
        return describe_config()


__all__ = [
    "ModelRouter",
    "ModelNotConfiguredError",
    "describe_config",
    "reload_profiles",
]
