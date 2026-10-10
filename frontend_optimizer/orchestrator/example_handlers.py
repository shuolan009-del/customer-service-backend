"""兼容层：真实模型接入已迁到 orchestrator/handlers.py 的 LLMHandlers。

保留本文件只为不破坏既有引用；新代码请直接从 handlers 导入：

    from frontend_optimizer.orchestrator.handlers import LLMHandlers
"""
from __future__ import annotations

from frontend_optimizer.model.slots import ComplexityInput, ModelSlot, judge_model_slot
from frontend_optimizer.orchestrator.handlers import (  # noqa: F401
    LLMHandlers,
    OpenAIChatGateway,
    extract_json,
    render_prompt,
    slot_for,
)

__all__ = [
    "LLMHandlers",
    "OpenAIChatGateway",
    "extract_json",
    "render_prompt",
    "slot_for",
    "ComplexityInput",
    "ModelSlot",
    "judge_model_slot",
]
