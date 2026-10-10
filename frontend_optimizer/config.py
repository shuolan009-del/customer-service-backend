"""前端优化多智能体协作架构：全局常量配置。

本包是「构建期编排工具」，与客服后端运行时解耦，不参与 /api/chat 链路。
最高红线 R1：任何智能体都不得修改后端代码。
"""
from __future__ import annotations

import os
from pathlib import Path

# 项目根：frontend_optimizer/config.py -> parents[1] 即 F:\customer-service-backend
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 输出根：编排运行期产物（令牌、报告、演示包）默认落盘位置
DEFAULT_WORKSPACE = PROJECT_ROOT / "docs" / "frontend-optimizer" / "workspace"

# 外部 Skill 根目录（默认指向本机 .workbuddy，可用环境变量 SKILL_ROOT 覆盖）
SKILL_ROOT = Path(
    os.getenv("SKILL_ROOT", r"C:\Users\86195\.workbuddy")
)

# 4 个外部 Skill 的落位（与方案文档 §10 一致）
SKILL_PATHS: dict[str, Path] = {
    # 生产级前端界面设计（版式 / 配色 / 布局 / 动效）
    "frontend-design": SKILL_ROOT
    / "plugins"
    / "marketplaces"
    / "codebuddy-plugins-official"
    / "plugins"
    / "frontend-design"
    / "SKILL.md",
    # 晓得·设计解剖：设计参考 -> Design Token -> 风格一致页面
    "joy2know-design-tokens": SKILL_ROOT
    / "skills"
    / "joy2know-design-tokens"
    / "SKILL.md",
    # 真机 headless 渲染 + CDP 交互验证、性能指标采集
    "headless-cdp-verify": SKILL_ROOT / "skills" / "headless-cdp-verify" / "SKILL.md",
    # 批量页面采集、截图、交互回归
    "agent-browser": SKILL_ROOT
    / "plugins"
    / "marketplaces"
    / "codebuddy-plugins-official"
    / "plugins"
    / "agent-browser"
    / "SKILL.md",
}
