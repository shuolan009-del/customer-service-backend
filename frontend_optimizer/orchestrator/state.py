"""一次前端优化运行的状态对象。"""
from __future__ import annotations

import time
import uuid

from pydantic import BaseModel, Field

from frontend_optimizer.orchestrator.stages import Stage
from frontend_optimizer.orchestrator.tasks import TaskGraph


class StageLog(BaseModel):
    """阶段流转日志。"""

    stage: Stage
    entered_at: float
    note: str = ""


class RunState(BaseModel):
    """编排运行的聚合根。"""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""                                       # 优化需求
    workspace: str = ""                                  # 产物落盘目录
    current_stage: Stage = Stage.S0_ALIGN
    frozen: bool = False                                 # 规范是否已冻结
    graph: TaskGraph = Field(default_factory=TaskGraph)
    tokens: dict = Field(default_factory=dict)           # E1-DS 产出的设计令牌
    artifacts: dict[str, str] = Field(default_factory=dict)   # 名称 -> 路径
    red_line_audit: str = ""                             # 红线终审结论
    stage_log: list[StageLog] = Field(default_factory=list)
    started_at: float = Field(default_factory=time.time)
    finished_at: float | None = None
