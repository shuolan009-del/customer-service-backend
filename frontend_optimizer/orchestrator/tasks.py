"""任务单元 / 泳道 / 交付物 / 依赖 DAG（文档 §4.2、§4.3、§5）。"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from frontend_optimizer.agents.roles import Lane, RoleId
from frontend_optimizer.model.slots import ModelSlot


class TaskStatus(str, Enum):
    """任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class Deliverable(BaseModel):
    """交付物。"""

    name: str
    path: str | None = None   # 相对项目根
    produced: bool = False


class FileBoundary(BaseModel):
    """一人一域的文件边界（文档 §4.2）。"""

    writable: list[str] = Field(default_factory=list)    # 相对路径 / glob
    read_only: list[str] = Field(default_factory=list)


class TaskUnit(BaseModel):
    """一个可调度任务单元。"""

    task_id: str
    title: str
    stage: str                                       # 对应 Stage 值，例如 "S2"
    owner: RoleId
    lane: Lane = Lane.NONE
    slot: ModelSlot = ModelSlot.REASONING            # 按复杂度判定后的档位
    depends_on: list[str] = Field(default_factory=list)
    boundary: FileBoundary = Field(default_factory=FileBoundary)
    deliverables: list[Deliverable] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING


class TaskGraph(BaseModel):
    """任务依赖图。"""

    tasks: list[TaskUnit] = Field(default_factory=list)

    def by_id(self, task_id: str) -> TaskUnit:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(task_id)

    def parallel_groups(self) -> list[list[TaskUnit]]:
        """按依赖拓扑分层，同层可并行执行。"""
        remaining = {t.task_id: set(t.depends_on) for t in self.tasks}
        groups: list[list[TaskUnit]] = []
        while remaining:
            ready = [tid for tid, deps in remaining.items() if not deps]
            if not ready:  # 存在环
                raise ValueError(f"任务依赖存在环：{sorted(remaining)}")
            groups.append([self.by_id(tid) for tid in ready])
            for tid in ready:
                remaining.pop(tid)
            for deps in remaining.values():
                deps.difference_update(ready)
        return groups
