"""编排引擎主循环：S0 -> S1 -> S2(并行) -> S3 -> S4 -> S5。

回退规则由 stages.resolve_rollback 决定，回退次数有上限（防止模型反复挑刺导致死循环）。
S5 交付前做红线终审：比对后端文件哈希，确认零改动。
"""
from __future__ import annotations

import asyncio
import time

from frontend_optimizer.guardrails import red_line
from frontend_optimizer.model.router import ModelRouter
from frontend_optimizer.orchestrator.handlers import StageHandler
from frontend_optimizer.orchestrator.stages import (
    ReviewOutcome,
    Stage,
    next_stage,
    resolve_rollback,
)
from frontend_optimizer.orchestrator.state import RunState, StageLog
from frontend_optimizer.orchestrator.tasks import TaskStatus, TaskUnit


class Orchestrator:
    """总控编排专家（OR）的实现载体。"""

    def __init__(
        self,
        handlers: StageHandler,
        router: ModelRouter | None = None,
        max_rollbacks: int = 2,
    ) -> None:
        self.handlers = handlers
        self.router = router or ModelRouter()
        self.max_rollbacks = max_rollbacks
        self._rollbacks = 0
        # 变更前快照：后端文件哈希（用于 S5 终审）
        self._backend_baseline = red_line.hash_files(red_line.snapshot_backend_paths())

    def _enter(self, state: RunState, note: str = "") -> None:
        state.stage_log.append(
            StageLog(stage=state.current_stage, entered_at=time.time(), note=note)
        )

    @staticmethod
    def _finished(state: RunState) -> set[str]:
        """已完成（成功或已驳回）的任务 id —— 都不会再重跑。"""
        return {
            t.task_id
            for t in state.graph.tasks
            if t.status in {TaskStatus.DONE, TaskStatus.REJECTED, TaskStatus.ROLLED_BACK}
        }

    async def _run_stage(self, state: RunState) -> ReviewOutcome:
        """执行当前阶段；S2 并行跑任务，其余阶段串行。

        只执行「本次 plan 新产出且仍待办」的任务，避免回退后重跑历史任务。
        """
        tasks = await self.handlers.plan(state, state.current_stage)
        state.graph.tasks.extend(tasks)
        pending = [t for t in tasks if t.status is TaskStatus.PENDING]

        if state.current_stage is Stage.S2_PARALLEL and pending:
            await self._run_lanes(state)
        else:
            for task in pending:
                await self.handlers.run_task(state, task)

        outcome = await self.handlers.review(state, state.current_stage)
        if not isinstance(outcome, ReviewOutcome):
            outcome = ReviewOutcome.PASS
        return outcome

    async def _run_lanes(self, state: RunState) -> None:
        """按依赖拓扑分层并行执行泳道任务（依赖未完成的任务自动跳过）。"""
        for group in state.graph.parallel_groups():
            finished = self._finished(state)
            runnable: list[TaskUnit] = [
                t
                for t in group
                if t.status is TaskStatus.PENDING and set(t.depends_on) <= finished
            ]
            if not runnable:
                continue
            await asyncio.gather(*(self.handlers.run_task(state, task) for task in runnable))

    async def run(self, state: RunState) -> RunState:
        """驱动整条流水线。"""
        while True:
            self._enter(state)
            outcome = await self._run_stage(state)

            if state.current_stage is Stage.S4_ACCEPT and outcome is not ReviewOutcome.PASS:
                if self._rollbacks >= self.max_rollbacks:
                    state.stage_log.append(
                        StageLog(
                            stage=Stage.S4_ACCEPT,
                            entered_at=time.time(),
                            note=f"回退次数达上限 {self.max_rollbacks}，强制进入交付：{outcome.value}",
                        )
                    )
                    state.current_stage = Stage.S5_DELIVER
                    continue
                self._rollbacks += 1
                target = resolve_rollback(outcome)
                state.stage_log.append(
                    StageLog(
                        stage=Stage.S4_ACCEPT,
                        entered_at=time.time(),
                        note=f"验收未通过（{outcome.value}），回退到 {target.value}",
                    )
                )
                state.current_stage = target
                continue

            nxt = next_stage(state.current_stage)
            if nxt is None:
                # S5 交付：红线终审
                changed = red_line.final_backend_audit(self._backend_baseline)
                state.red_line_audit = "PASS" if not changed else f"VIOLATION:{changed}"
                break
            state.current_stage = nxt

        state.finished_at = time.time()
        return state
