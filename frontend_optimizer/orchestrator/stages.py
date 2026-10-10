"""S0~S5 阶段机与回退规则（文档 §5）。"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from frontend_optimizer.agents.roles import RoleId


class Stage(str, Enum):
    """端到端协作阶段。"""

    S0_ALIGN = "S0"        # 需求对齐
    S1_FREEZE = "S1"       # 规范冻结
    S2_PARALLEL = "S2"     # 并行改造
    S3_INTEGRATE = "S3"    # 集成对齐
    S4_ACCEPT = "S4"       # 验收
    S5_DELIVER = "S5"      # 交付


class ReviewOutcome(str, Enum):
    """S4 验收结论。"""

    PASS = "pass"                        # 通过
    FIX_LANE = "fix_lane"                # 退回对应泳道修复
    REFREEZE_SPEC = "refreeze"           # 涉及规范本身 -> 退回 S1
    REJECT_REDLINE = "reject_redline"    # 触碰红线 -> 无条件回退


class StageMeta(BaseModel):
    """阶段元信息。"""

    stage: Stage
    title: str
    owner: RoleId
    participants: list[RoleId] = Field(default_factory=list)
    exit_criteria: str


STAGE_META: dict[Stage, StageMeta] = {
    Stage.S0_ALIGN: StageMeta(
        stage=Stage.S0_ALIGN,
        title="需求对齐",
        owner=RoleId.OR,
        exit_criteria="任务分解表确认",
    ),
    Stage.S1_FREEZE: StageMeta(
        stage=Stage.S1_FREEZE,
        title="规范冻结",
        owner=RoleId.E1_DS,
        participants=[RoleId.OR],
        exit_criteria="规范冻结令（OR 签发）",
    ),
    Stage.S2_PARALLEL: StageMeta(
        stage=Stage.S2_PARALLEL,
        title="并行改造",
        owner=RoleId.OR,
        participants=[RoleId.E2_LY, RoleId.E3_ST, RoleId.E4_IX, RoleId.E5_PF],
        exit_criteria="各泳道自检通过",
    ),
    Stage.S3_INTEGRATE: StageMeta(
        stage=Stage.S3_INTEGRATE,
        title="集成对齐",
        owner=RoleId.OR,
        participants=[RoleId.E1_DS],
        exit_criteria="无冲突、风格统一",
    ),
    Stage.S4_ACCEPT: StageMeta(
        stage=Stage.S4_ACCEPT,
        title="验收",
        owner=RoleId.E6_QA,
        exit_criteria="缺陷清零、红线通过",
    ),
    Stage.S5_DELIVER: StageMeta(
        stage=Stage.S5_DELIVER,
        title="交付",
        owner=RoleId.OR,
        exit_criteria="交付清单签署",
    ),
}

# 正常前向流转
_FORWARD: dict[Stage, Stage] = {
    Stage.S0_ALIGN: Stage.S1_FREEZE,
    Stage.S1_FREEZE: Stage.S2_PARALLEL,
    Stage.S2_PARALLEL: Stage.S3_INTEGRATE,
    Stage.S3_INTEGRATE: Stage.S4_ACCEPT,
    Stage.S4_ACCEPT: Stage.S5_DELIVER,
}


def next_stage(stage: Stage) -> Stage | None:
    """取正常流转的下一阶段；S5 之后为 None。"""
    return _FORWARD.get(stage)


def resolve_rollback(outcome: ReviewOutcome) -> Stage:
    """按 S4 验收结论计算回退目标（文档 §5 回退规则）。"""
    if outcome is ReviewOutcome.REFREEZE_SPEC:
        return Stage.S1_FREEZE
    # FIX_LANE / REJECT_REDLINE 都退回并行改造
    return Stage.S2_PARALLEL
