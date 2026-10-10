"""7 名专家编制：1 名统筹规划（OR）+ 6 名执行（E1~E6）。

严格对齐《前端页面优化-多智能体协作架构方案.md》§1~§3。

编制说明（是否增删专家的判断）：
    - OR 不可省：唯一拥有「规范冻结」「变更准入」「冲突裁决」权的角色。
    - E1-DS（设计规范）不可省：商务风格需要唯一视觉来源，否则多页必然漂移。
    - E2/E3/E4 分设的理由是「一人一域」：结构 / 样式 / 交互分属不同文件类型，
      合并会立刻产生同一文件并行写入的冲突。
    - E5-PF（性能）不可省：验收标准含「性能不劣化」，需要独立采集与基线比对。
    - E6-QA（验收 + 红线执法）不可省，且必须独立于执行方，否则红线校验失去意义。
    结论：6 名执行专家全部保留，未做增删。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from frontend_optimizer.model.slots import ModelSlot


class RoleId(str, Enum):
    """专家编号。"""

    OR = "OR"        # 总控编排专家（前端优化总架构师）
    E1_DS = "E1-DS"  # 设计规范专家
    E2_LY = "E2-LY"  # 布局重构专家
    E3_ST = "E3-ST"  # 样式与主题专家
    E4_IX = "E4-IX"  # 交互与动效专家
    E5_PF = "E5-PF"  # 性能优化专家
    E6_QA = "E6-QA"  # 质量验收专家


class RoleKind(str, Enum):
    """角色类型。"""

    PLANNING = "planning"    # 统筹规划
    EXECUTIVE = "executive"  # 执行


class Lane(str, Enum):
    """并行泳道（文档 §4.1）。OR / E1 / E6 不占泳道。"""

    NONE = "-"
    A_LAYOUT = "A"        # E2-LY 布局重构
    B_STYLE = "B"         # E3-ST 样式主题
    C_INTERACTION = "C"   # E4-IX 交互动效
    D_PERFORMANCE = "D"   # E5-PF 性能优化


class RoleSpec(BaseModel):
    """单个专家的完整档案。"""

    id: RoleId
    name: str
    kind: RoleKind
    lane: Lane = Lane.NONE
    responsibility: str
    duties: list[str] = Field(default_factory=list)
    # 所用技能（对应 skills/registry.py 的键）
    skills: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    # 默认档位；实际执行按任务复杂度二次裁决（见 model/slots.py）
    default_slot: ModelSlot = ModelSlot.REASONING
    # 独占可写范围描述（实际以 guardrails/red_line.py 的路径规则为准）
    write_scope: str = ""
    read_only_scope: str = ""
    can_reject: bool = False
    can_admit_change: bool = False


ROLE_SPECS: dict[RoleId, RoleSpec] = {
    RoleId.OR: RoleSpec(
        id=RoleId.OR,
        name="总控编排专家（前端优化总架构师）",
        kind=RoleKind.PLANNING,
        responsibility="全局唯一指挥中枢：拆解任务、冻结规范、调度并行、集成对齐、交付把关",
        duties=[
            "需求拆解与任务 DAG 编排",
            "冻结设计规范（S1 出口签发规范冻结令）",
            "划分并行泳道与文件边界",
            "处理专家间冲突与依赖",
            "集成对齐（S3）",
            "汇总交付与红线终审（S5）",
        ],
        skills=["frontend-design"],
        deliverables=[
            "任务分解与泳道分配表",
            "规范冻结令",
            "集成验收报告",
            "最终交付清单",
        ],
        write_scope="编排产物（报告 / 任务单），不直接写业务代码",
        read_only_scope="前端代码、后端接口契约（只读）",
        can_reject=True,
        can_admit_change=True,
    ),
    RoleId.E1_DS: RoleSpec(
        id=RoleId.E1_DS,
        name="设计规范专家",
        kind=RoleKind.EXECUTIVE,
        responsibility="商务风格的“立法者”，产出所有视觉决策的唯一来源",
        duties=[
            "定义色彩体系（中性色 / 语义色）",
            "定义字体阶梯与间距节奏",
            "定义圆角与阴影基调",
            "定义栅格与断点",
            "输出设计令牌与组件规范",
        ],
        skills=["frontend-design", "joy2know-design-tokens"],
        deliverables=["design-tokens.json", "design-spec.md"],
        write_scope="设计令牌 / 规范文档",
        read_only_scope="页面代码",
    ),
    RoleId.E2_LY: RoleSpec(
        id=RoleId.E2_LY,
        name="布局重构专家",
        kind=RoleKind.EXECUTIVE,
        lane=Lane.A_LAYOUT,
        responsibility="页面“骨架工程师”：语义结构与信息层级",
        duties=[
            "语义化 HTML 重构",
            "统一栅格布局",
            "导航 / 卡片 / 表格 / 表单区块布局",
            "信息层级与留白节奏",
        ],
        skills=["frontend-design"],
        deliverables=["重构后的模板 / 结构文件", "布局说明"],
        write_scope="模板 / 结构文件",
        read_only_scope="样式文件、脚本",
    ),
    RoleId.E3_ST: RoleSpec(
        id=RoleId.E3_ST,
        name="样式与主题专家",
        kind=RoleKind.EXECUTIVE,
        lane=Lane.B_STYLE,
        responsibility="把设计令牌“翻译”为可维护的样式系统",
        duties=[
            "CSS 变量化落地",
            "亮 / 暗主题",
            "响应式断点实现",
            "组件视觉样式与状态样式（hover / focus / disabled / error）",
        ],
        skills=["frontend-design", "joy2know-design-tokens"],
        deliverables=["主题变量文件", "组件样式文件", "响应式样式"],
        write_scope="样式文件、主题变量",
        read_only_scope="模板结构、脚本",
    ),
    RoleId.E4_IX: RoleSpec(
        id=RoleId.E4_IX,
        name="交互与动效专家",
        kind=RoleKind.EXECUTIVE,
        lane=Lane.C_INTERACTION,
        responsibility="商务风格下的“克制体验”实现者（稳重、短促、不炫技）",
        duties=[
            "交互状态机",
            "过渡与微动效",
            "表单校验反馈",
            "加载 / 空态",
            "键盘可达与焦点管理",
        ],
        skills=["frontend-design"],  # 辅以原生 JS / WAAPI，无额外依赖
        deliverables=["交互脚本", "动效参数表", "键盘操作说明"],
        write_scope="前端脚本",
        read_only_scope="模板结构、样式文件",
    ),
    RoleId.E5_PF: RoleSpec(
        id=RoleId.E5_PF,
        name="性能优化专家",
        kind=RoleKind.EXECUTIVE,
        lane=Lane.D_PERFORMANCE,
        responsibility="性能守门人，保证“升级不降级”",
        duties=[
            "静态资源与图片优化（格式 / 尺寸 / 懒加载）",
            "字体加载策略",
            "关键渲染路径优化",
            "CSS / JS 体积与无用样式清理",
            "性能指标采集与基线对比",
        ],
        skills=["headless-cdp-verify"],
        deliverables=["性能基线对比报告", "优化清单"],
        write_scope="资源与构建配置（前端侧）",
        read_only_scope="后端目录、接口契约",
    ),
    RoleId.E6_QA: RoleSpec(
        id=RoleId.E6_QA,
        name="质量验收专家",
        kind=RoleKind.EXECUTIVE,
        responsibility="独立验收方，同时是红线的唯一执法者",
        duties=[
            "视觉回归比对（多断点截图）",
            "跨浏览器 / 跨端一致性",
            "可访问性检查",
            "红线校验：确认未修改任何后端文件",
            "缺陷分级与复现步骤输出",
        ],
        skills=["headless-cdp-verify", "agent-browser"],
        deliverables=["验收报告", "红线校验报告", "缺陷清单"],
        write_scope="报告（不写业务代码）",
        read_only_scope="全部业务代码（只读校验）",
        can_reject=True,
    ),
}


def get_role(role_id: RoleId | str) -> RoleSpec:
    """按编号取专家档案。"""
    return ROLE_SPECS[RoleId(role_id)]


def executive_roles() -> list[RoleSpec]:
    """返回 6 名执行专家。"""
    return [spec for spec in ROLE_SPECS.values() if spec.kind is RoleKind.EXECUTIVE]


def parallel_lanes() -> list[RoleSpec]:
    """返回 4 条并行泳道对应的专家（E2~E5，文档 §4.1）。"""
    return [spec for spec in ROLE_SPECS.values() if spec.lane is not Lane.NONE]
