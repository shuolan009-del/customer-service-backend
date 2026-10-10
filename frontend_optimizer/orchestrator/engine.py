"""编排引擎主循环：S0 -> S1 -> S2(并行) -> S3 -> S4 -> S5。

回退规则由 stages.resolve_rollback 决定。
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


class Orchestrator:
    """总控编排专家（OR）的实现载体。"""

    def __init__(
        self,
        handlers: StageHandler,
        router: ModelRouter | None = None,
    ) -> None:
        self.handlers = handlers
        self.router = router or ModelRouter()
        # 变更前快照：后端文件哈希（用于 S5 终审）
        self._backend_baseline = red_line.hash_files(red_line.snapshot_backend_paths())

    def _enter(self, state: RunState, note: str = "") -> None:
        state.stage_log.append(
            StageLog(stage=state.current_stage, entered_at=time.time(), note=note)
        )

    async def _run_stage(self, state: RunState) -> ReviewOutcome:
        """执行当前阶段；S2 并行跑任务，其余阶段串行。"""
        tasks = await self.handlers.plan(state, state.current_stage)
        state.graph.tasks.extend(tasks)

        if state.current_stage is Stage.S2_PARALLEL and tasks:
            for group in state.graph.parallel_groups():
                await asyncio.gather(
                    *(self.handlers.run_task(state, task) for task in group)
                )
        else:
            for task in tasks:
                await self.handlers.run_task(state, task)

        outcome = await self.handlers.review(state, state.current_stage)
        if not isinstance(outcome, ReviewOutcome):
            outcome = ReviewOutcome.PASS
        return outcome

    async def run(self, state: RunState) -> RunState:
        """驱动整条流水线。"""
        while True:
            self._enter(state)
            outcome = await self._run_stage(state)

            if state.current_stage is Stage.S4_ACCEPT and outcome is not ReviewOutcome.PASS:
                state.current_stage = resolve_rollback(outcome)
                continue

            nxt = next_stage(state.current_stage)
            if nxt is None:
                # S5 交付：红线终审
                changed = red_line.final_backend_audit(self._backend_baseline)
                state.red_line_audit = (
                    "PASS" if not changed else f"VIOLATION:{changed}"
                )
                break
            state.current_stage = nxt

        state.finished_at = time.time()
        return state
