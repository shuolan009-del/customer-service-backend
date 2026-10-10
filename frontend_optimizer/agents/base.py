"""专家基类：把角色档案、技能、文件边界绑成一个可执行对象。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from frontend_optimizer.agents.roles import RoleId, RoleSpec
from frontend_optimizer.orchestrator.state import RunState
from frontend_optimizer.skills.registry import SkillBinding, skills_for


class BaseAgent(ABC):
    """所有专家的公共父类。"""

    def __init__(self, spec: RoleSpec) -> None:
        self.spec = spec

    @property
    def role_id(self) -> RoleId:
        return self.spec.id

    @property
    def skills(self) -> list[SkillBinding]:
        """本角色绑定的外部技能。"""
        return skills_for(self.spec.id)

    @abstractmethod
    async def act(self, state: RunState) -> None:
        """执行本角色的阶段动作，产物写入 state。"""
        raise NotImplementedError
