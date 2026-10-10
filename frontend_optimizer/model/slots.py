"""模型档位与任务复杂度判定（方案文档 §6）。

注意：本文件只定义「档位」，不定义「具体模型」。
具体模型名在 profiles.py 留空待填。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ModelSlot(str, Enum):
    """模型档位：按任务复杂度动态选择。"""

    REASONING = "reasoning"  # 高性能：设计 / 取舍 / 架构 / 根因分析
    FAST = "fast"            # 轻量：执行既定规范、批量替换、采集整理


class ComplexityDimension(str, Enum):
    """复杂度判定维度（文档 §6.1）。"""

    DECISION = "决策性"
    IMPACT = "影响面"
    DEPTH = "推理深度"
    REVERSIBILITY = "可逆性"


class ComplexityInput(BaseModel):
    """一次任务的复杂度画像。每项 True 表示「偏复杂 / 偏重」。"""

    needs_decision: bool = False   # 需要设计 / 取舍 / 架构决策
    cross_scope: bool = False      # 跨页面 / 跨泳道 / 全局
    deep_reasoning: bool = False   # 根因分析 / 冲突消解 / 方案设计
    hard_to_revert: bool = False   # 牵一发动全身


def judge_model_slot(profile: ComplexityInput) -> ModelSlot:
    """按文档 §6.1 判定模型档位：任一维度偏复杂 -> 高性能，否则轻量。"""
    if (
        profile.needs_decision
        or profile.cross_scope
        or profile.deep_reasoning
        or profile.hard_to_revert
    ):
        return ModelSlot.REASONING
    return ModelSlot.FAST
