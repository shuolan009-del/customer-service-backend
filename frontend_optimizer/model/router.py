"""模型路由器：把任务档位解析为具体模型配置。

骨架阶段只做「解析 + 校验」；真正的 LLM 调用由 orchestrator/handlers.py 注入实现。
"""
from __future__ import annotations

from frontend_optimizer.model.profiles import MODEL_PROFILES, ModelProfile
from frontend_optimizer.model.slots import ModelSlot


class ModelNotConfiguredError(RuntimeError):
    """模型档位尚未配置时抛出，避免静默使用错误模型。"""


class ModelRouter:
    """按档位取模型配置。"""

    def __init__(self, profiles: dict[ModelSlot, ModelProfile] | None = None) -> None:
        self._profiles = profiles or MODEL_PROFILES

    def resolve(self, slot: ModelSlot) -> ModelProfile:
        """解析档位对应的模型配置；未配置则明确报错。"""
        profile = self._profiles.get(slot)
        if profile is None or not profile.configured:
            raise ModelNotConfiguredError(
                f"模型档位 {slot.value!r} 尚未配置 provider/model，"
                f"请在 frontend_optimizer/model/profiles.py 中补齐。"
            )
        return profile

    def describe(self) -> dict[str, str]:
        """返回各档位的可读状态，便于编排前自检 / 打印。"""
        return {
            slot.value: (
                f"{profile.provider}/{profile.model}"
                if profile.configured
                else "未配置"
            )
            for slot, profile in self._profiles.items()
        }
