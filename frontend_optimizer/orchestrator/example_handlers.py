"""示例：把真实模型接进编排引擎（骨架，未填具体模型）。

用途：演示 orchestrator/handlers.py 的 StageHandler 三个方法该怎么实现。
你只需替换 call_model() 内的模型调用，编排逻辑无需改动。

运行前请先在 frontend_optimizer/model/profiles.py 补齐两个档位。
"""
from __future__ import annotations

from frontend_optimizer.model.router import ModelRouter
from frontend_optimizer.model.slots import ComplexityInput, ModelSlot, judge_model_slot
from frontend_optimizer.orchestrator.stages import ReviewOutcome, Stage
from frontend_optimizer.orchestrator.state import RunState
from frontend_optimizer.orchestrator.tasks import TaskUnit
from frontend_optimizer.prompts.loader import load_prompt


class LLMHandlers:
    """基于真实模型的 StageHandler 实现骨架。"""

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    async def plan(self, state: RunState, stage: Stage) -> list[TaskUnit]:
        """按阶段加载提示词，让 OR / E1 拆出任务单元。"""
        prompt_name = {
            Stage.S0_ALIGN: "orchestrator_plan",
            Stage.S1_FREEZE: "design_freeze",
            Stage.S2_PARALLEL: "lane_work",
            Stage.S3_INTEGRATE: "integrate",
            Stage.S4_ACCEPT: "accept",
            Stage.S5_DELIVER: "deliver",
        }[stage]
        template = load_prompt(prompt_name)
        # TODO: 用 template + 实际输入调用模型，解析 JSON 为 list[TaskUnit]
        raise NotImplementedError(
            f"待实现：调用模型生成 {stage.value} 任务单元（模板 {prompt_name}）"
        )

    async def run_task(self, state: RunState, task: TaskUnit) -> None:
        """执行单个任务；档位由复杂度判定决定。"""
        _profile = self.router.resolve(task.slot)  # 未配置时在此明确报错
        # TODO: 按 task.boundary.writable / read_only 读写文件
        raise NotImplementedError(f"待实现：执行任务 {task.task_id}")

    async def review(self, state: RunState, stage: Stage) -> ReviewOutcome:
        """阶段评审；S4 需返回真实验收结论。"""
        if stage is Stage.S4_ACCEPT:
            # TODO: 视觉回归 + a11y + 红线路径比对，聚合为 ReviewOutcome
            return ReviewOutcome.PASS
        return ReviewOutcome.PASS


def slot_for(task_complexity: ComplexityInput) -> ModelSlot:
    """按复杂度画像取档位，可直接用于构造 TaskUnit.slot。"""
    return judge_model_slot(task_complexity)
