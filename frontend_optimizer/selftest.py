"""架构自检：验证角色编制、阶段机、红线机制、令牌导出、模型档位与执行器接线。

用法（项目要求用 uv run）：
    uv run python -m frontend_optimizer.selftest

全部离线，不需要真实密钥；真实连通性另用：
    uv run python -m frontend_optimizer.run --check
"""
from __future__ import annotations

import asyncio
import json
import tempfile

from frontend_optimizer.agents.roles import ROLE_SPECS, executive_roles, parallel_lanes
from frontend_optimizer.guardrails import red_line
from frontend_optimizer.model.profiles import MODEL_PROFILES, ModelProfile, describe_config
from frontend_optimizer.model.router import ModelNotConfiguredError, ModelRouter
from frontend_optimizer.model.slots import ComplexityInput, ModelSlot, judge_model_slot
from frontend_optimizer.orchestrator.engine import Orchestrator
from frontend_optimizer.orchestrator.handlers import (
    LLMHandlers,
    NoopHandlers,
    extract_json,
    render_prompt,
)
from frontend_optimizer.orchestrator.state import RunState
from frontend_optimizer.orchestrator.tasks import FileBoundary, TaskStatus, TaskUnit
from frontend_optimizer.prompts.loader import available_prompts
from frontend_optimizer.skills.registry import SKILL_REGISTRY, missing_skills
from frontend_optimizer.tokens.schema import DesignTokens, TokenSource, TokenValue


def check_roster() -> None:
    """编制检查：1 名统筹 + 6 名执行 + 4 条泳道。"""
    assert len(ROLE_SPECS) == 7, "专家总数应为 7"
    assert len(executive_roles()) == 6, "执行专家应为 6 名"
    assert len(parallel_lanes()) == 4, "并行泳道应为 4 条"
    print(
        f"[OK] 编制：{len(ROLE_SPECS)} 名"
        f"（1 统筹 + {len(executive_roles())} 执行），泳道 {len(parallel_lanes())} 条"
    )


def check_skills() -> None:
    """技能登记与本机完整性检查（含 SKILL.md 与运行时依赖）。"""
    print(f"[..] 技能登记 {len(SKILL_REGISTRY)} 个")
    problems = missing_skills()
    if problems:
        for item in problems:
            print(f"[WARN] {item}")
    else:
        print("[OK] 4 个外部技能：SKILL.md + 运行时依赖均就绪")


def check_model_slots() -> None:
    """模型档位判定 + 未配置时明确报错 + 当前真实配置打印。"""
    fast = judge_model_slot(ComplexityInput())
    hard = judge_model_slot(ComplexityInput(needs_decision=True))
    assert fast is ModelSlot.FAST and hard is ModelSlot.REASONING
    print(f"[OK] 档位判定：简单->{fast.value}，复杂->{hard.value}")

    # 留空机制：显式给一个空档位，必须报错而不是静默跑
    empty = ModelRouter({ModelSlot.REASONING: ModelProfile()})
    try:
        empty.resolve(ModelSlot.REASONING)
        raise AssertionError("未配置却解析成功，模型留空机制失效")
    except ModelNotConfiguredError:
        print("[OK] 模型留空机制生效：未配置即明确报错")

    router = ModelRouter()
    print(f"[..] 槽位状态：{router.describe()}")
    vision = "可用" if router.available(ModelSlot.VISION) else "未配置（自动降级为 reasoning）"
    print(f"[..] 视觉档：{vision}")
    for line in describe_config():
        if line.startswith("  ["):
            print(f"[..]{line}")


def check_red_line() -> None:
    """红线路径比对。"""
    ok = red_line.check_changes(["static/avatar_demo.html"])
    bad = red_line.check_changes(["service/dialogue_service.py"])
    assert ok.passed, "前端文件不应被拦"
    assert not bad.passed, "后端文件必须被拦"
    print("[OK] 红线：前端放行、后端拦截")
    edge = red_line.check_changes(["docs/whatever.md"])
    assert not edge.passed
    print("[OK] 红线：白名单外路径拦截")

    # 持久化基线：保存 -> 校验（要求无变化）
    saved = red_line.save_baseline()
    changed = red_line.audit_against_saved_baseline()
    assert changed == [], f"基线自比对不应有变化：{changed}"
    print(f"[OK] 后端哈希基线：{saved}（自比对无改动）")


def check_write_gate() -> None:
    """写入门禁：后端路径 / 越界路径的产出必须被拒绝，前端白名单内放行。"""
    handlers = LLMHandlers(apply_changes=False)
    task = TaskUnit(
        task_id="gate",
        title="门禁测试",
        stage="S2",
        owner=parallel_lanes()[0].id,
        boundary=FileBoundary(writable=["external/customer-service-frontend/**"]),
    )
    changed, proposed, violations = handlers._apply_files(
        task,
        [
            {"path": "service/dialogue_service.py", "content": "x = 1"},
            {"path": "docs/notes.md", "content": "# hi"},
            {"path": "external/customer-service-frontend/index.html", "content": "<html></html>"},
        ],
    )
    assert not changed, "dry-run 不应写盘"
    assert len(violations) == 2, f"应拦下 2 条越界改动，实际 {violations}"
    assert proposed == ["external/customer-service-frontend/index.html"], proposed
    print(f"[OK] 写入门禁：后端与白名单外被拦（{len(violations)} 条），前端放行")


def check_tokens() -> str:
    """令牌自检 + CSS 导出。"""
    def tv(v: str, src: TokenSource = TokenSource.USER) -> TokenValue:
        return TokenValue(value=v, source=src)

    tokens = DesignTokens(
        color_primary=tv("#1F4E79"),
        color_success=tv("#2E7D32"),
        color_warning=tv("#B7791F"),
        color_danger=tv("#C0392B"),
        gray_scale={"50": tv("#F7F8FA"), "900": tv("#1F2329")},
        bg_base=tv("#FFFFFF"),
        bg_subtle=tv("#F7F8FA"),
        fg_base=tv("#1F2329"),
        fg_muted=tv("#6B7280"),
        font_sans=tv('"PingFang SC", "Microsoft YaHei", sans-serif'),
        text_scale={"sm": tv("14px"), "lg": tv("20px")},
        space_scale={"4": tv("16px"), "6": tv("24px")},
        reference="自检样例",
    )
    assert not tokens.missing_minimum_set(), "最小集合不应缺失"
    from frontend_optimizer.tokens.exporter import export

    out = export(tokens, "docs/frontend-optimizer/workspace/_selftest-tokens.css")
    print(f"[OK] 令牌导出：{out}（推断项 {len(tokens.inferred_fields())} 个）")
    return out


def check_prompt_tools() -> None:
    """提示词渲染 + JSON 抽取（含代码围栏、尾逗号、前后废话）。"""
    rendered = render_prompt("orchestrator_plan", goal="把首页改成商务风格", pages="index.html", contracts="只读")
    assert "把首页改成商务风格" in rendered, "模板未渲染 goal"
    print("[OK] 提示词渲染：变量已注入")

    samples = [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '好的，结果如下：\n```json\n{"a": 1,}\n```\n以上。',
        '前缀 {"a": 1} 后缀',
    ]
    for sample in samples:
        assert extract_json(sample) == {"a": 1}, f"JSON 抽取失败：{sample!r}"
    print(f"[OK] JSON 抽取：{len(samples)} 种脏输出均可解析")


async def check_pipeline() -> None:
    """用 NoopHandlers 跑通 S0->S5 状态机 + 红线终审。"""
    handlers = NoopHandlers()
    orch = Orchestrator(handlers=handlers)
    state = RunState(goal="自检：跑通阶段机", workspace="docs/frontend-optimizer/workspace")
    result = await orch.run(state)
    stages = [log.stage.value for log in result.stage_log]
    assert stages[:6] == ["S0", "S1", "S2", "S3", "S4", "S5"], f"阶段流转异常：{stages}"
    assert result.red_line_audit == "PASS", f"红线终审异常：{result.red_line_audit}"
    print(f"[OK] 阶段机流转：{' -> '.join(stages)}")
    print(f"[OK] 红线终审：{result.red_line_audit}")


class _FakeGateway:
    """离线假网关：按提示词特征词回放预置回答，验证 LLMHandlers 端到端接线。"""

    MARKERS = {
        "任务 DAG": "orchestrator_plan",
        "8 项最小集合": "design_freeze",
        "你独占的可写范围": "lane_work",
        "集成对齐": "integrate",
        "红线的唯一执法者": "accept",
        "汇总最终交付物": "deliver",
    }

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete(self, profile, prompt: str, system: str | None = None) -> str:
        name = next((v for k, v in self.MARKERS.items() if k in prompt), "unknown")
        self.calls.append(name)
        return json.dumps(self._reply(name), ensure_ascii=False)

    @staticmethod
    def _reply(name: str) -> dict | str:
        if name == "orchestrator_plan":
            return {
                "tasks": [
                    {
                        "task_id": "S2-E2-LY",
                        "title": "首页布局重构",
                        "owner": "E2-LY",
                        "lane": "A",
                        "complexity": {"needs_decision": True},
                        "writable": ["external/customer-service-frontend/**"],
                        "deliverables": ["布局说明"],
                    },
                    {
                        "task_id": "S2-E5-PF",
                        "title": "资源压缩",
                        "owner": "E5-PF",
                        "lane": "D",
                        "complexity": {},
                        "depends_on": ["S2-E2-LY"],
                        "writable": ["external/customer-service-frontend/public/**"],
                        "deliverables": ["性能报告"],
                    },
                ]
            }
        if name == "design_freeze":
            tv = lambda v: {"value": v, "source": "inferred", "note": "[推断]"}  # noqa: E731
            return {
                "color_primary": {"value": "#1F4E79", "source": "user", "note": ""},
                "color_success": {"value": "#2E7D32", "source": "user", "note": ""},
                "color_warning": {"value": "#B7791F", "source": "user", "note": ""},
                "color_danger": {"value": "#C0392B", "source": "user", "note": ""},
                "bg_base": {"value": "#FFFFFF", "source": "user", "note": ""},
                "bg_subtle": {"value": "#F7F8FA", "source": "user", "note": ""},
                "fg_base": {"value": "#1F2329", "source": "user", "note": ""},
                "fg_muted": {"value": "#6B7280", "source": "user", "note": ""},
                "font_sans": {"value": "system-ui, sans-serif", "source": "user", "note": ""},
                "gray_scale": {"50": tv("#F7F8FA"), "900": tv("#1F2329")},
                "reference": "自检样例",
            }
        if name == "lane_work":
            return {"files": [], "self_check": "离线自检：不改动任何文件", "needs_escalation": "无"}
        if name == "integrate":
            return {"conflicts": [], "conclusion": "无冲突，风格统一"}
        if name == "accept":
            return {"outcome": "pass", "defects": [], "red_line": {"passed": True, "violations": []}}
        if name == "deliver":
            return "最终交付清单（离线自检）"
        raise AssertionError(f"假网关收到未知提示词：{name}")


async def check_llm_pipeline() -> None:
    """用假网关 + LLMHandlers 跑通真实执行器（dry-run，不写业务文件）。"""
    profiles = {
        ModelSlot.REASONING: ModelProfile(provider="fake", model="fake-reasoning", base_url="http://127.0.0.1:1/v1"),
        ModelSlot.FAST: ModelProfile(provider="fake", model="fake-fast", base_url="http://127.0.0.1:1/v1"),
        ModelSlot.VISION: ModelProfile(),  # 故意不配，验证视觉档自动降级
    }
    with tempfile.TemporaryDirectory(prefix="fo-selftest-") as tmp:
        gateway = _FakeGateway()
        handlers = LLMHandlers(
            router=ModelRouter(profiles), gateway=gateway, apply_changes=False
        )
        orch = Orchestrator(handlers=handlers)
        state = RunState(goal="自检：LLM 执行器接线", workspace=tmp)
        result = await orch.run(state)

        stages = [log.stage.value for log in result.stage_log]
        assert stages == ["S0", "S1", "S2", "S3", "S4", "S5"], f"阶段流转异常：{stages}"
        assert result.artifacts, "未产出任何产物"
        assert result.red_line_audit == "PASS", result.red_line_audit
        assert not handlers.failures(result), f"不应有失败任务：{handlers.failures(result)}"
        lane_tasks = [t for t in result.graph.tasks if t.stage == "S2"]
        assert {t.task_id for t in lane_tasks} == {"S2-E2-LY", "S2-E5-PF"}, lane_tasks
        slots = {t.task_id: t.slot for t in lane_tasks}
        assert slots["S2-E2-LY"] is ModelSlot.REASONING, "复杂任务应走高性能档"
        assert slots["S2-E5-PF"] is ModelSlot.FAST, "简单任务应走轻量档"
        assert all(t.status is TaskStatus.DONE for t in lane_tasks), [t.status for t in lane_tasks]
        qa = [t for t in result.graph.tasks if t.stage == "S4"][0]
        assert qa.slot is ModelSlot.REASONING, "视觉档未配置时应降级为高性能档"

    print(f"[OK] LLM 执行器：假网关跑通 S0->S5，产物 {len(result.artifacts)} 项")
    print(f"[OK] 档位路由：复杂任务->reasoning，简单任务->fast，视觉档缺失->降级")


def check_prompts() -> None:
    """提示词模板齐备。"""
    names = available_prompts()
    expected = {
        "orchestrator_plan",
        "design_freeze",
        "lane_work",
        "integrate",
        "accept",
        "deliver",
    }
    assert expected.issubset(set(names)), f"缺少提示词：{expected - set(names)}"
    print(f"[OK] 提示词模板：{len(names)} 个 {names}")


def main() -> None:
    print("=" * 60)
    print("前端优化多智能体协作架构 - 自检")
    print("=" * 60)
    check_roster()
    check_skills()
    check_model_slots()
    check_red_line()
    check_write_gate()
    check_tokens()
    check_prompt_tools()
    check_prompts()
    asyncio.run(check_pipeline())
    asyncio.run(check_llm_pipeline())
    print("=" * 60)
    configured = sum(1 for p in MODEL_PROFILES.values() if p.configured)
    print(f"自检完成：架构 + 执行器可用；模型档位已配置 {configured}/{len(MODEL_PROFILES)} 个。")
    print("真实连通性请执行：uv run python -m frontend_optimizer.run --check")


if __name__ == "__main__":
    main()
