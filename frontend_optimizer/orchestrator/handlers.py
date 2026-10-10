"""LLM 回调协议：骨架与真实模型之间的唯一接口。

骨架阶段用 NoopHandlers；把具体模型接进来时，实现这几个方法即可，
编排逻辑（engine.py）完全不用改。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from frontend_optimizer.orchestrator.stages import ReviewOutcome, Stage
from frontend_optimizer.orchestrator.state import RunState
from frontend_optimizer.orchestrator.tasks import TaskStatus, TaskUnit


@runtime_checkable
class StageHandler(Protocol):
    """一个阶段的执行器。"""

    async def plan(self, state: RunState, stage: Stage) -> list[TaskUnit]:
        """为该阶段拆出任务单元。"""
        ...

    async def run_task(self, state: RunState, task: TaskUnit) -> None:
        """执行单个任务单元，产物写进 state.artifacts。"""
        ...

    async def review(self, state: RunState, stage: Stage) -> ReviewOutcome:
        """阶段评审；S4 返回 ReviewOutcome。"""
        ...


class NoopHandlers:
    """骨架默认实现：只推进状态机，不做任何真实改动。

    用于验证编排、DAG、红线机制本身是否跑通。
    """

    def __init__(self, log: list[str] | None = None) -> None:
        self.log: list[str] = log if log is not None else []

    async def plan(self, state: RunState, stage: Stage) -> list[TaskUnit]:
        self.log.append(f"[plan] {stage.value}")
        return []

    async def run_task(self, state: RunState, task: TaskUnit) -> None:
        self.log.append(f"[run] {task.task_id} by {task.owner.value}")
        task.status = TaskStatus.DONE

    async def review(self, state: RunState, stage: Stage) -> ReviewOutcome:
        self.log.append(f"[review] {stage.value}")
        return ReviewOutcome.PASS
