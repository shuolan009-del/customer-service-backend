"""命令行入口：看配置、验连通、跑流水线。

用法（统一走 uv run）：
    uv run python -m frontend_optimizer.run --print-config    # 看当前生效的档位配置
    uv run python -m frontend_optimizer.run --check           # 真实调用每个档位一次（花 token，验证连通）
    uv run python -m frontend_optimizer.run --goal "把首页改成商务风格"   # 跑完整 S0->S5
    uv run python -m frontend_optimizer.run --goal "..." --dry-run        # 只出报告，不落盘改代码
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

from frontend_optimizer.config import DEFAULT_WORKSPACE, PROJECT_ROOT
from frontend_optimizer.model.profiles import MODEL_PROFILES, describe_config
from frontend_optimizer.model.router import ModelNotConfiguredError, ModelRouter
from frontend_optimizer.model.slots import ModelSlot
from frontend_optimizer.orchestrator.engine import Orchestrator
from frontend_optimizer.orchestrator.handlers import (
    LLMHandlers,
    OpenAIChatGateway,
    extract_json,
)
from frontend_optimizer.orchestrator.state import RunState


def _print_config() -> None:
    print("=" * 72)
    print("前端优化多智能体协作架构 - 模型档位配置")
    print("=" * 72)
    for line in describe_config():
        print(line)


async def _check() -> int:
    """真实调用每个已配置档位一次，验证 provider/model/base_url/key 是否可用。"""
    router = ModelRouter()
    gateway = OpenAIChatGateway()
    print("=" * 72)
    print("连通性自检（会真实调用模型，消耗少量 token）")
    print("=" * 72)
    failures = 0
    prompt = '请只输出 JSON：{"ok": true, "model": "<你实际的模型名>"}'
    for slot in ModelSlot:
        try:
            profile = router.resolve(slot)
        except ModelNotConfiguredError as exc:
            print(f"[跳过] {slot.value:<9} 未配置：{exc}")
            continue
        started = time.time()
        try:
            text = await gateway.complete(profile, prompt, system="你是连通性探针。")
            elapsed = time.time() - started
            try:
                payload = extract_json(text)
                detail = json.dumps(payload, ensure_ascii=False)[:120]
            except Exception:
                detail = text.strip().replace("\n", " ")[:120]
            print(f"[OK]   {slot.value:<9} {profile.label()}  {elapsed:.1f}s  -> {detail}")
        except Exception as exc:  # noqa: BLE001 - 探针要报告而不是崩掉
            failures += 1
            print(f"[FAIL] {slot.value:<9} {profile.label()}  {type(exc).__name__}: {str(exc)[:200]}")
    print("-" * 72)
    print("结论：全部可用" if failures == 0 else f"结论：{failures} 个档位调用失败，请核对型号/密钥")
    return 1 if failures else 0


async def _run(goal: str, workspace: str, apply_changes: bool) -> int:
    handlers = LLMHandlers(apply_changes=apply_changes)
    orchestrator = Orchestrator(handlers=handlers)
    state = RunState(goal=goal, workspace=workspace)
    print("=" * 72)
    print(f"开始编排：{goal}")
    print(f"工作区：{PROJECT_ROOT / workspace}")
    print(f"写入模式：{'真实落盘' if apply_changes else '只出报告（dry-run）'}")
    print("=" * 72)

    started = time.time()
    try:
        await orchestrator.run(state)
    except Exception as exc:  # noqa: BLE001 - CLI 顶层兜底
        print(f"[FATAL] {type(exc).__name__}: {exc}")
        return 1
    elapsed = time.time() - started

    print("-" * 72)
    print(f"阶段流转：{' -> '.join(log.stage.value for log in state.stage_log)}")
    print(f"红线终审：{state.red_line_audit}")
    print(f"耗时：{elapsed:.1f}s")
    print("\n产物：")
    for name, path in state.artifacts.items():
        print(f"  - {name} -> {path}")
    failures = handlers.failures(state)
    if failures:
        print("\n被驳回的任务：")
        for item in failures:
            print(f"  - {item}")
    if handlers.log:
        print("\n执行日志：")
        for line in handlers.log:
            print(f"  {line}")
    return 0


def _force_utf8_stdout() -> None:
    """Windows 控制台默认 GBK，打印 emoji/特殊符号会 UnicodeEncodeError 炸在最后一步。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - 老解释器/被重定向的流忽略即可
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frontend_optimizer.run",
        description="前端优化多智能体协作架构：配置查看 / 连通自检 / 流水线执行",
    )
    parser.add_argument("--print-config", action="store_true", help="打印当前生效的档位与型号")
    parser.add_argument("--check", action="store_true", help="真实调用每个档位一次，验证连通性")
    parser.add_argument("--goal", help="优化需求，提供则跑完整 S0->S5 流水线")
    parser.add_argument(
        "--workspace", default=str(DEFAULT_WORKSPACE.relative_to(PROJECT_ROOT)).replace("\\", "/")
    )
    parser.add_argument("--dry-run", action="store_true", help="只出报告，不把泳道产出写进磁盘")
    _force_utf8_stdout()
    args = parser.parse_args(argv)

    if args.print_config:
        _print_config()
        return 0
    if args.check:
        return asyncio.run(_check())
    if args.goal:
        return asyncio.run(_run(args.goal, args.workspace, not args.dry_run))
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
