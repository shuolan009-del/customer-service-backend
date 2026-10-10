"""前端优化多智能体协作架构包。

只搭架构、不绑定具体模型；模型配置见 model/profiles.py。
本包不参与客服后端运行时链路，也不得修改任何后端代码（红线 R1）。
"""
from frontend_optimizer.agents.roles import ROLE_SPECS, RoleId, get_role
from frontend_optimizer.orchestrator.engine import Orchestrator
from frontend_optimizer.orchestrator.stages import Stage

__all__ = ["ROLE_SPECS", "RoleId", "get_role", "Orchestrator", "Stage"]
