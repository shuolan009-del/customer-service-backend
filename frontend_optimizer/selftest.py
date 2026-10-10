"""架构自检：验证角色编制、阶段机、红线机制、令牌导出与技能依赖是否可用。

用法（项目要求用 uv run）：
    uv run python -m frontend_optimizer.selftest
不需要任何模型配置，纯离线校验。
"""
from __future__ import annotations

import asyncio

from frontend_optimizer.agents.roles import ROLE_SPECS, executive_roles, parallel_lanes
from frontend_optimizer.guardrails import red_line
from frontend_optimizer.model.router import ModelNotConfiguredError, ModelRouter
from frontend_optimizer.model.slots import ComplexityInput, ModelSlot, judge_model_slot
from frontend_optimizer.orchestrator.engine import Orchestrator
from frontend_optimizer.orchestrator.handlers import NoopHandlers
from frontend_optimizer.orchestrator.state import RunState
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
    """模型档位判定 + 未配置时明确报错。"""
    fast = judge_model_slot(ComplexityInput())
    hard = judge_model_slot(ComplexityInput(needs_decision=True))
    assert fast is ModelSlot.FAST and hard is ModelSlot.REASONING
    print(f"[OK] 档位判定：简单->{fast.value}，复杂->{hard.value}")

    router = ModelRouter()
    print(f"[..] 槽位状态：{router.describe()}")
    try:
        router.resolve(ModelSlot.REASONING)
        print("[FAIL] 未配置却解析成功，模型留空机制失效")
    except ModelNotConfiguredError:
        print("[OK] 模型留空机制生效：未配置即明确报错")


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


async def check_pipeline() -> None:
    """用 NoopHandlers 跑通 S0->S5 状态机 + 红线终审。"""
    handlers = NoopHandlers()
    orch = Orchestrator(handlers=handlers)
    state = RunState(goal="自检：跑通阶段机", workspace="docs/frontend-optimizer/workspace")
    result = await orch.run(state)
    stages = [log.stage.value for log in result.stage_log]
    assert stages == ["S0", "S1", "S2", "S3", "S4", "S5"], f"阶段流转异常：{stages}"
    assert result.red_line_audit == "PASS", f"红线终审异常：{result.red_line_audit}"
    print(f"[OK] 阶段机流转：{' -> '.join(stages)}")
    print(f"[OK] 红线终审：{result.red_line_audit}")


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
    check_tokens()
    check_prompts()
    asyncio.run(check_pipeline())
    print("=" * 60)
    print("自检完成：架构骨架可用，模型配置待填。")


if __name__ == "__main__":
    main()
