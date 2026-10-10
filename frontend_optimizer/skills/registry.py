"""外部 Skill 落位注册表（文档 §10）+ 运行时依赖自检。

只登记，不加载。技能正文由各角色在真正执行时按提示词指引读取。
路径来自 config.SKILL_PATHS，可用环境变量 SKILL_ROOT 覆盖根目录。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from frontend_optimizer.agents.roles import RoleId
from frontend_optimizer.config import SKILL_PATHS


class SkillBinding(BaseModel):
    """一个外部技能的归属与用途。"""

    name: str
    path: Path
    purpose: str
    owners: list[RoleId]
    # 运行时依赖（可执行文件 / 外部二进制），缺一不可
    runtime_commands: list[str] = Field(default_factory=list)
    runtime_paths: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


SKILL_REGISTRY: dict[str, SkillBinding] = {
    "frontend-design": SkillBinding(
        name="frontend-design",
        path=SKILL_PATHS["frontend-design"],
        purpose="生产级前端界面设计（版式 / 配色 / 布局 / 动效）",
        owners=[RoleId.E1_DS, RoleId.E2_LY, RoleId.E3_ST, RoleId.E4_IX],
    ),
    "joy2know-design-tokens": SkillBinding(
        name="joy2know-design-tokens",
        path=SKILL_PATHS["joy2know-design-tokens"],
        purpose="把设计参考解剖为可复用 Design Token，并按 token 生成风格一致的页面代码",
        owners=[RoleId.E1_DS, RoleId.E3_ST],
        runtime_commands=["python"],
    ),
    "headless-cdp-verify": SkillBinding(
        name="headless-cdp-verify",
        path=SKILL_PATHS["headless-cdp-verify"],
        purpose="真机 headless 渲染 + CDP 交互验证、性能指标采集",
        owners=[RoleId.E5_PF, RoleId.E6_QA],
        runtime_commands=["node"],
        runtime_paths=[r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    ),
    "agent-browser": SkillBinding(
        name="agent-browser",
        path=SKILL_PATHS["agent-browser"],
        purpose="批量页面采集、截图、交互回归",
        owners=[RoleId.E6_QA],
        runtime_commands=["agent-browser"],
    ),
}


def skills_for(role_id: RoleId) -> list[SkillBinding]:
    """返回某角色可用的技能绑定。"""
    return [b for b in SKILL_REGISTRY.values() if role_id in b.owners]


def _check_binding(binding: SkillBinding) -> list[str]:
    """检查单个技能的 SKILL.md 与运行时依赖，返回问题清单。"""
    problems: list[str] = []
    if not binding.path.exists():
        problems.append(f"{binding.name}: 缺少 SKILL.md -> {binding.path}")
    for cmd in binding.runtime_commands:
        if shutil.which(cmd) is None:
            problems.append(f"{binding.name}: 依赖命令不可用 -> {cmd}")
    for raw in binding.runtime_paths:
        if not Path(raw).exists():
            problems.append(f"{binding.name}: 依赖路径不存在 -> {raw}")
    return problems


def missing_skills() -> list[str]:
    """返回技能缺失项（SKILL.md 或运行时依赖），供启动自检。"""
    problems: list[str] = []
    for binding in SKILL_REGISTRY.values():
        problems.extend(_check_binding(binding))
    return problems
