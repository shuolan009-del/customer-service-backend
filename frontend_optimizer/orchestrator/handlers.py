"""阶段执行器：离线骨架（NoopHandlers）与真实模型接入（LLMHandlers）。

engine.py 只依赖 StageHandler 协议，所以换执行器不需要动编排逻辑。

LLMHandlers 的职责分工：
    plan()      按阶段拆任务：S0 让 OR 拆 DAG，S2 把 DAG 变成四条泳道任务
    run_task()  调模型干活：渲染提示词 -> 取档位 -> 调用 -> 解析 JSON -> 落盘/改文件
    review()    阶段评审：S4 由 E6-QA 出结论，且**红线由代码强制裁决**（模型说了不算）
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from frontend_optimizer.agents.roles import Lane, RoleId, get_role, parallel_lanes
from frontend_optimizer.config import PROJECT_ROOT
from frontend_optimizer.guardrails import red_line
from frontend_optimizer.model.profiles import ModelProfile
from frontend_optimizer.model.router import ModelNotConfiguredError, ModelRouter
from frontend_optimizer.model.slots import ComplexityInput, ModelSlot, judge_model_slot
from frontend_optimizer.orchestrator.stages import ReviewOutcome, Stage
from frontend_optimizer.orchestrator.state import RunState
from frontend_optimizer.orchestrator.tasks import (
    Deliverable,
    FileBoundary,
    TaskStatus,
    TaskUnit,
)
from frontend_optimizer.prompts.loader import load_prompt

RENDER_ENTRY_CANDIDATES = (
    "external/customer-service-frontend/index.html",
    "static/avatar_demo.html",
)

# 前端根目录（相对项目根）：用于把可写范围统一成同一套坐标系
FRONTEND_ROOT = "external/customer-service-frontend"

# 本次前端优化任务的硬约束：只允许改造既有文件，禁止新建文件
# （用户要求「整体框架不变、已有功能不删」）。设 0 关闭。
DENY_NEW_FILES = os.getenv("FRONTEND_OPTIMIZER_DENY_NEW_FILES", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}

# 「禁止写入」哨兵：可写范围非空但任何路径都匹配不上，使落盘校验把一切写入判为越界。
# 用于「退让后已无可用文件」的泳道，防止空边界被当作无限制。
DENY_WRITE = "\x00__deny_write__"

# 补丁模式：单条任务允许的 find/replace 补丁条数上限（防模型倾泻式改文件）
MAX_EDITS_PER_TASK = int(os.getenv("FRONTEND_OPTIMIZER_MAX_EDITS", "40"))

# 一人一域的文件认领优先级：单文件 SFC 工程里 App.vue 是唯一载体，样式专家优先
# （视觉改造的主场），其余专家退让，避免多条泳道并行写同一文件互相覆盖。
_CLAIM_PRIORITY: tuple[RoleId, ...] = (
    RoleId.E3_ST,
    RoleId.E2_LY,
    RoleId.E1_DS,
    RoleId.E4_IX,
    RoleId.E5_PF,
)


# ============================================================ 提示词 / JSON 工具
def render_prompt(name: str, **context: Any) -> str:
    """渲染 prompts/jinja2 下的模板（jinja2 已是本项目依赖）。"""
    from jinja2 import Template

    return Template(load_prompt(name)).render(**context)


_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def extract_json(text: str) -> dict:
    """从模型输出里抠出第一个 JSON 对象。

    容忍：```json 围栏、前后解释性废话、多余尾逗号。
    """
    if not text or not text.strip():
        raise ValueError("模型返回为空，无法解析 JSON")
    fenced = _FENCE_RE.search(text)
    raw = fenced.group(1) if fenced else text
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"未找到 JSON 对象：{text[:200]!r}")
    candidate = raw[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return json.loads(_TRAILING_COMMA_RE.sub(r"\1", candidate))


# ------------------------------------------------------------ 令牌字段归一化
# 模型经常不按 schema 输出：裸字符串值、background_base 之类的别名、把说明塞进 notes。
# 这里做一次宽容归一化，让 E1-DS 的产出能真正落到 DesignTokens / CSS 导出。
_TOKEN_ALIASES: dict[str, str] = {
    "background_base": "bg_base",
    "background_subtle": "bg_subtle",
    "background": "bg_base",
    "foreground_base": "fg_base",
    "foreground_muted": "fg_muted",
    "foreground": "fg_base",
    "font_family": "font_sans",
    "font": "font_sans",
}

_TOKEN_VALUE_FIELDS: tuple[str, ...] = (
    "color_primary",
    "color_success",
    "color_warning",
    "color_danger",
    "bg_base",
    "bg_subtle",
    "fg_base",
    "fg_muted",
    "font_sans",
)

_TOKEN_SCALE_FIELDS: tuple[str, ...] = (
    "gray_scale",
    "text_scale",
    "space_scale",
    "radius_scale",
    "shadow_scale",
    "breakpoints",
)


def _coerce_token(value: Any, fallback_note: str = "") -> dict | None:
    """把「裸值」或「不完整字典」统一成 TokenValue 结构。"""
    note = fallback_note or "[推断] 模型未标注来源"
    if isinstance(value, dict):
        for key in ("value", "hex", "color", "val"):
            if value.get(key) not in (None, ""):
                return {
                    "value": str(value[key]),
                    "source": str(value.get("source") or "inferred"),
                    "note": str(value.get("note") or note),
                }
        return None
    if isinstance(value, (str, int, float)) and str(value).strip():
        return {"value": str(value), "source": "inferred", "note": note}
    return None


def normalize_tokens(payload: dict) -> dict | None:
    """把 design_freeze 的松散输出归一化成 DesignTokens 可校验的结构。

    返回 None 表示完全无法归一化（此时调用方回退到原始结构）。
    """
    if not isinstance(payload, dict):
        return None
    note = str(payload.get("note") or payload.get("notes") or "")
    flat: dict[str, Any] = {_TOKEN_ALIASES.get(k, k): v for k, v in payload.items()}
    result: dict[str, Any] = {}
    for field in _TOKEN_VALUE_FIELDS:
        coerced = _coerce_token(flat.get(field), note)
        if coerced:
            result[field] = coerced
    for field in _TOKEN_SCALE_FIELDS:
        raw = flat.get(field)
        if not isinstance(raw, dict):
            continue
        scale = {str(k): v for k, v in ((k, _coerce_token(v, note)) for k, v in raw.items()) if v}
        if scale:
            result[field] = scale
    if not result:
        return None
    result["reference"] = str(flat.get("reference") or note or "模型输出（字段名已归一化）")
    return result


def _inline_file(path: str, limit: int = 4000) -> str:
    """把产物文件内容内联进提示词（模型读不到本地路径，必须喂内容）。"""
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / path
    if not p.is_file():
        return f"（文件不存在：{path}）"
    text = p.read_text(encoding="utf-8", errors="replace")
    return text[:limit] + ("…（已截断）" if len(text) > limit else "")


# ============================================================ 模型网关
@runtime_checkable
class ModelGateway(Protocol):
    """一次模型调用的最小接口（便于测试时替换为假实现）。"""

    async def complete(
        self, profile: ModelProfile, prompt: str, system: str | None = None
    ) -> str:
        ...


def _content_to_text(content: Any) -> str:
    """把各家 SDK 的返回内容统一成纯文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return str(content)


class OpenAIChatGateway:
    """走 OpenAI 兼容协议调用模型（复用本项目已声明的 langchain-openai）。"""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], Any] = {}

    def _client(self, profile: ModelProfile) -> Any:
        if not profile.has_key:
            raise ModelNotConfiguredError(
                f"档位 {profile.provider}/{profile.model} 缺少 API Key："
                f"请在 .env 里设置 {profile.api_key_env or 'FRONTEND_OPTIMIZER_API_KEY'}"
                "（或全局 FRONTEND_OPTIMIZER_API_KEY）。"
            )
        cache_key = (profile.resolved_base_url or "", profile.model or "")
        if cache_key not in self._cache:
            from langchain_openai import ChatOpenAI

            kwargs: dict[str, Any] = {
                "model": profile.model,
                "base_url": profile.resolved_base_url,
                "api_key": profile.api_key,
                "timeout": profile.timeout,
                "max_retries": 2,
                **profile.extra,
            }
            # 推理类模型可能不接受 temperature，配置为 none 时不传
            if profile.temperature is not None:
                kwargs["temperature"] = profile.temperature
            self._cache[cache_key] = ChatOpenAI(**kwargs)
        return self._cache[cache_key]

    async def complete(
        self, profile: ModelProfile, prompt: str, system: str | None = None
    ) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages: list[Any] = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        response = await self._client(profile).ainvoke(messages)
        return _content_to_text(getattr(response, "content", response))


# ============================================================ 阶段执行器协议
@runtime_checkable
class StageHandler(Protocol):
    """一个阶段的执行器。"""

    async def plan(self, state: RunState, stage: Stage) -> list[TaskUnit]:
        """为该阶段拆出任务单元。"""
        ...

    async def run_task(self, state: RunState, task: TaskUnit) -> None:
        """执行单个任务单元，产物写进 state.artifacts。"""
        ...

    async def review(self, state: RunState, stage: Stage) -> ReviewOutcome:
        """阶段评审；S4 返回 ReviewOutcome。"""
        ...


class NoopHandlers:
    """骨架默认实现：只推进状态机，不做任何真实改动。

    用于验证编排、DAG、红线机制本身是否跑通。
    """

    def __init__(self, log: list[str] | None = None) -> None:
        self.log: list[str] = log if log is not None else []

    async def plan(self, state: RunState, stage: Stage) -> list[TaskUnit]:
        self.log.append(f"[plan] {stage.value}")
        return []

    async def run_task(self, state: RunState, task: TaskUnit) -> None:
        self.log.append(f"[run] {task.task_id} by {task.owner.value}")
        task.status = TaskStatus.DONE

    async def review(self, state: RunState, stage: Stage) -> ReviewOutcome:
        self.log.append(f"[review] {stage.value}")
        return ReviewOutcome.PASS


# ============================================================ LLM 执行器
# 各阶段「一个自足任务」的默认归属：阶段 -> (负责人, 档位, 任务名)
_STAGE_TASKS: dict[Stage, tuple[RoleId, ModelSlot, str]] = {
    Stage.S0_ALIGN: (RoleId.OR, ModelSlot.REASONING, "需求拆解与任务 DAG 编排"),
    Stage.S1_FREEZE: (RoleId.E1_DS, ModelSlot.REASONING, "冻结设计令牌与组件规范"),
    Stage.S3_INTEGRATE: (RoleId.OR, ModelSlot.REASONING, "四泳道集成对齐与冲突消解"),
    Stage.S4_ACCEPT: (RoleId.E6_QA, ModelSlot.VISION, "多断点验收与红线终审"),
    Stage.S5_DELIVER: (RoleId.OR, ModelSlot.REASONING, "汇总最终交付清单"),
}

# 泳道默认档位（LLM 未给出复杂度画像时的兜底）
_LANE_SLOT: dict[Lane, ModelSlot] = {
    Lane.A_LAYOUT: ModelSlot.REASONING,
    Lane.B_STYLE: ModelSlot.REASONING,
    Lane.C_INTERACTION: ModelSlot.REASONING,
    Lane.D_PERFORMANCE: ModelSlot.FAST,
}

_OUTCOME_MAP: dict[str, ReviewOutcome] = {
    "pass": ReviewOutcome.PASS,
    "fix_lane": ReviewOutcome.FIX_LANE,
    "refreeze": ReviewOutcome.REFREEZE_SPEC,
    "refreeze_spec": ReviewOutcome.REFREEZE_SPEC,
    "reject_redline": ReviewOutcome.REJECT_REDLINE,
}


class LLMHandlers:
    """基于真实模型的 StageHandler 实现。

    参数：
        apply_changes  是否真的把泳道产出的文件写进磁盘（False 则只出报告）
    """

    def __init__(
        self,
        router: ModelRouter | None = None,
        gateway: ModelGateway | None = None,
        *,
        log: list[str] | None = None,
        apply_changes: bool = True,
        max_json_retries: int = 1,
    ) -> None:
        self.router = router or ModelRouter()
        self.gateway = gateway or OpenAIChatGateway()
        self.log: list[str] = log if log is not None else []
        self.apply_changes = apply_changes
        self.max_json_retries = max_json_retries
        self._planned: dict[str, list[dict]] = {}
        self._verdicts: dict[str, dict] = {}
        self._violations: dict[str, list[str]] = {}
        self._failures: dict[str, list[str]] = {}

    # ------------------------------------------------------------ plan
    async def plan(self, state: RunState, stage: Stage) -> list[TaskUnit]:
        """按阶段拆任务。"""
        if stage is Stage.S2_PARALLEL:
            plans = self._planned.get(state.run_id)
            if plans:
                tasks = self._valid_tasks(state, plans)
            else:
                self.log.append("[warn] S0 未产出任务表，回退到默认四泳道骨架")
                tasks = self._valid_tasks(
                    state, [self._default_lane_plan(r) for r in parallel_lanes()]
                )
            return self._enforce_exclusive_boundaries(tasks)

        owner, slot, title = _STAGE_TASKS[stage]
        slot = self._fit_slot(slot)
        return [
            TaskUnit(
                task_id=f"{stage.value}-{owner.value}",
                title=title,
                stage=stage.value,
                owner=owner,
                slot=slot,
                boundary=FileBoundary(writable=[], read_only=[]),
                deliverables=[Deliverable(name=title)],
            )
        ]

    def _fit_slot(self, slot: ModelSlot) -> ModelSlot:
        """可选档位（视觉）未配置时降级到高性能档。"""
        if slot is ModelSlot.VISION and not self.router.available(ModelSlot.VISION):
            self.log.append("[warn] 视觉档未配置，E6-QA 降级使用高性能档")
            return ModelSlot.REASONING
        return slot

    def _default_lane_plan(self, role) -> dict:
        """LLM 没给任务表时的兜底泳道定义（可写范围取自角色档案）。"""
        return {
            "task_id": f"S2-{role.id.value}",
            "title": f"{role.name}：{role.responsibility}",
            "owner": role.id.value,
            "lane": role.lane.value,
            "writable": self._default_writable(role.id),
            "deliverables": role.deliverables[:1],
        }

    @staticmethod
    def _default_writable(role_id: RoleId) -> list[str]:
        """兜底可写范围：按本工程「单文件 Vue SFC」的真实布局分配，严格落在红线白名单内。

        本工程样式写在 src/App.vue 的 <style scoped> 里，并不存在独立 .css 文件，
        所以样式专家的默认范围必须直接指向 App.vue，否则会去改一个不存在的文件。
        """
        root = f"{FRONTEND_ROOT}/"
        sfc = [f"{root}src/App.vue"]
        return {
            RoleId.E2_LY: [f"{root}index.html"],
            RoleId.E3_ST: sfc,
            RoleId.E4_IX: sfc,
            RoleId.E5_PF: [f"{root}vite.config.js", f"{root}package.json"],
        }.get(role_id, [])

    @staticmethod
    def _normalize_writable(paths: list) -> list[str]:
        """把编排产出的可写范围统一成「相对项目根」的坐标系。

        坑点：S0 编排专家经常给相对前端目录的写法（src/App.vue），而落盘校验用的是
        相对项目根的写法（external/customer-service-frontend/src/App.vue）。差一个
        前缀，全体专家的产出都会被误判为「越界」，导致整轮零落盘。
        """
        out: list[str] = []
        prefix = FRONTEND_ROOT + "/"
        for raw in paths:
            p = str(raw).strip().replace("\\", "/").lstrip("./")
            if not p:
                continue
            if p == FRONTEND_ROOT or p.startswith(prefix):
                norm = p
            elif p in {"index.html", "vite.config.js", "package.json", "package-lock.json"} or p.startswith(
                ("src/", "public/", "dist/", "assets/")
            ):
                norm = prefix + p
            else:
                continue  # 既不是前端相对路径、也不是前端绝对路径 -> 丢弃（防越界）
            # 把 glob / 具体路径统一展开成「真实存在的文件」：本次禁止新建文件，
            # 指向不存在目标的泳道注定空转，这里直接剔除。
            for hit in PROJECT_ROOT.glob(norm):
                if not hit.is_file():
                    continue
                rel = str(hit.relative_to(PROJECT_ROOT)).replace("\\", "/")
                if any(
                    part in {"node_modules", "dist", ".vite", "__pycache__"}
                    for part in Path(rel).parts
                ):
                    continue
                if rel not in out:
                    out.append(rel)
        return out

    def _enforce_exclusive_boundaries(self, tasks: list[TaskUnit]) -> list[TaskUnit]:
        """一人一域硬约束：同一个文件只能有一个写入者。

        单文件 SFC 工程里 App.vue 是唯一载体，多条泳道并行写它必然互相覆盖。
        这里按角色优先级逐个认领文件，退让后拿不到任何文件的任务先回落角色默认范围，
        仍拿不到就显式置为「禁止写入」。
        """
        order = {rid: i for i, rid in enumerate(_CLAIM_PRIORITY)}
        ranked = sorted(tasks, key=lambda t: order.get(t.owner, len(order)))
        claimed: set[str] = set()
        for task in ranked:
            kept = [p for p in task.boundary.writable if p not in claimed]
            if not kept:
                default = self._normalize_writable(self._default_writable(task.owner))
                kept = [p for p in default if p not in claimed]
            if not kept:
                kept = [DENY_WRITE]
                self.log.append(
                    f"[warn] {task.task_id}({task.owner.value}) 已无可写文件，置为禁止写入"
                )
            claimed.update(kept)
            task.boundary.writable = kept
        return tasks

    def _valid_tasks(self, state: RunState, plans: list[dict]) -> list[TaskUnit]:
        """把任务条目转成 TaskUnit，顺手丢掉 owner 不合法的条目（模型偶尔会发明角色）。"""
        tasks = [self._lane_task(state, item) for item in plans]
        return [t for t in tasks if t is not None]

    def _lane_task(self, state: RunState, item: dict) -> TaskUnit | None:
        """把 S0 产出的任务条目（或兜底条目）转成 TaskUnit。"""
        complexity = item.get("complexity") or {}
        slot = judge_model_slot(
            ComplexityInput(
                needs_decision=bool(complexity.get("needs_decision")),
                cross_scope=bool(complexity.get("cross_scope")),
                deep_reasoning=bool(complexity.get("deep_reasoning")),
                hard_to_revert=bool(complexity.get("hard_to_revert")),
            )
        )
        raw_owner = str(item.get("owner") or RoleId.E2_LY.value).strip()
        try:
            owner = RoleId(raw_owner)
        except ValueError:
            self.log.append(
                f"[warn] 任务 {item.get('task_id')!r} 的 owner={raw_owner!r} 不在 7 名专家编制内，已丢弃该任务"
            )
            return None
        lane = Lane(item.get("lane") or get_role(owner).lane.value)
        writable = self._normalize_writable(
            item.get("writable") or self._default_writable(owner)
        )
        return TaskUnit(
            task_id=str(item.get("task_id") or f"S2-{owner.value}"),
            title=str(item.get("title") or get_role(owner).responsibility),
            stage=Stage.S2_PARALLEL.value,
            owner=owner,
            lane=lane,
            slot=slot,
            depends_on=[str(d) for d in (item.get("depends_on") or [])],
            boundary=FileBoundary(writable=writable, read_only=["**/service/**", "**/api/**"]),
            deliverables=[Deliverable(name=str(d)) for d in (item.get("deliverables") or [])],
        )

    # ------------------------------------------------------------ run_task
    async def run_task(self, state: RunState, task: TaskUnit) -> None:
        """执行单个任务；档位由复杂度判定决定。"""
        task.status = TaskStatus.RUNNING
        handlers = {
            Stage.S0_ALIGN.value: self._work_plan,
            Stage.S1_FREEZE.value: self._work_freeze,
            Stage.S2_PARALLEL.value: self._work_lane,
            Stage.S3_INTEGRATE.value: self._work_integrate,
            Stage.S4_ACCEPT.value: self._work_accept,
            Stage.S5_DELIVER.value: self._work_deliver,
        }
        worker = handlers.get(task.stage)
        if worker is None:
            task.status = TaskStatus.REJECTED
            self._note_failure(state, task, f"未知阶段 {task.stage!r}")
            return
        try:
            await worker(state, task)
            task.status = TaskStatus.DONE
            task.deliverables = [d.model_copy(update={"produced": True}) for d in task.deliverables]
        except Exception as exc:  # noqa: BLE001 - 单任务失败不应炸掉整条流水线
            task.status = TaskStatus.REJECTED
            self._note_failure(state, task, f"{type(exc).__name__}: {exc}")

    def _note_failure(self, state: RunState, task: TaskUnit, message: str) -> None:
        self._failures.setdefault(state.run_id, []).append(f"{task.task_id} -> {message}")
        self.log.append(f"[reject] {task.task_id}: {message}")

    # ------------------------------------------------------------ 各阶段实现
    async def _work_plan(self, state: RunState, task: TaskUnit) -> None:
        """S0：OR 拆解任务 DAG。"""
        payload = await self._ask(
            state,
            task,
            "orchestrator_plan",
            {
                "goal": state.goal or "（未提供）",
                "pages": self._page_inventory(),
                "contracts": "后端接口契约只读，任何情况下不得修改（红线 R1）",
            },
        )
        items = [i for i in (payload.get("tasks") or []) if isinstance(i, dict)]
        if not items:
            raise ValueError("模型未返回任何任务条目（tasks 为空）")
        self._planned[state.run_id] = items
        out = self._report_path(state, "S0", "task-plan.json")
        self._write_json(out, payload)
        state.artifacts[f"{task.task_id}/任务分解与泳道分配表"] = str(out)

    async def _work_freeze(self, state: RunState, task: TaskUnit) -> None:
        """S1：E1-DS 冻结设计令牌。"""
        payload = await self._ask(
            state,
            task,
            "design_freeze",
            {
                "reference": state.goal or "（未提供参考物）",
                "existing_tokens": self._existing_tokens(state),
            },
        )
        normalized = normalize_tokens(payload)
        if normalized is None:
            self.log.append("[warn] 令牌输出无法归一化，按原始结构记录")
        else:
            state.tokens = normalized
            if normalized != payload:
                self.log.append("[ok] 令牌字段名/取值已归一化到 DesignTokens 结构")
        if not state.tokens:
            state.tokens = payload

        out = self._report_path(state, "S1", "design-tokens.json")
        self._write_json(out, state.tokens)
        self._write_json(self._report_path(state, "S1", "design-tokens.raw.json"), payload)
        state.artifacts[f"{task.task_id}/design-tokens.json"] = str(out)

        try:
            from frontend_optimizer.tokens.exporter import export
            from frontend_optimizer.tokens.schema import DesignTokens

            tokens = DesignTokens.model_validate(state.tokens)
            css = export(tokens, self._report_path(state, "S1", "design-tokens.css"))
            state.artifacts[f"{task.task_id}/design-tokens.css"] = css
            missing = tokens.missing_minimum_set()
            if missing:
                self.log.append(f"[warn] 令牌缺少最小集合：{missing}")
            else:
                self.log.append(f"[ok] 令牌 8 项最小集合齐备（推断项 {len(tokens.inferred_fields())} 个）")
        except Exception as exc:  # noqa: BLE001 - 令牌结构不完整不致命，劝阻但不中断
            self.log.append(f"[warn] 令牌结构不完整，跳过 CSS 导出：{exc}")

    async def _work_lane(self, state: RunState, task: TaskUnit) -> None:
        """S2：某一泳道按冻结规范改造前端代码。"""
        role = get_role(task.owner)
        payload = await self._ask(
            state,
            task,
            "lane_work",
            {
                "role_name": role.name,
                "lane": task.lane.value,
                "frozen_tokens": json.dumps(state.tokens, ensure_ascii=False)[:8000] or "（未冻结）",
                "writable": task.boundary.writable,
                "read_only": task.boundary.read_only,
                "task_title": task.title,
                "existing_files": self._existing_sources(task),
            },
        )
        files = [f for f in (payload.get("files") or []) if isinstance(f, dict)]
        edits = [e for e in (payload.get("edits") or []) if isinstance(e, dict)]
        changed, proposed, violations = self._apply_files(task, files)
        if edits:
            # 补丁模式：代码负责精确替换，模型只出 find/replace 片段。
            # 大文件（App.vue 7.4 万字符）整文件重写在物理上不可行，必须走这条路。
            p_changed, p_proposed, p_violations = self._apply_edits(task, edits)
            changed.extend(p_changed)
            proposed.extend(p_proposed)
            violations.extend(p_violations)
        if violations:
            self._violations.setdefault(state.run_id, []).extend(violations)
            self.log.append(f"[redline] {task.task_id} 越界改动被驳回：{violations}")
        for rel in changed:
            state.artifacts[f"code:{rel}"] = rel
        report = dict(payload)
        report["applied"] = changed
        report["proposed_only"] = proposed
        report["violations"] = violations
        out = self._report_path(state, "S2", f"{task.task_id}.json")
        self._write_json(out, report)
        state.artifacts[f"{task.task_id}({task.owner.value})/泳道自检报告"] = str(out)

    async def _work_integrate(self, state: RunState, task: TaskUnit) -> None:
        """S3：OR + E1-DS 集成对齐。"""
        payload = await self._ask(
            state,
            task,
            "integrate",
            {
                "lane_outputs": self._lane_outputs(state),
                "frozen_tokens": json.dumps(state.tokens, ensure_ascii=False)[:6000] or "（未冻结）",
            },
        )
        out = self._report_path(state, "S3", "integration.json")
        self._write_json(out, payload)
        state.artifacts[f"{task.task_id}/集成验收报告"] = str(out)

    async def _work_accept(self, state: RunState, task: TaskUnit) -> None:
        """S4：E6-QA 出验收结论（红线部分由代码强制覆盖）。"""
        changed = self._changed_paths(state)
        red_report = red_line.check_changes(changed) if changed else None
        path_violations = [f"{r.path} -> {r.reason}" for r in (red_report.violations if red_report else [])]
        try:
            hash_changed = red_line.audit_against_saved_baseline()
        except FileNotFoundError:
            hash_changed = []

        payload = await self._ask(
            state,
            task,
            "accept",
            {
                "changed_paths": "\n".join(changed) or "（本次未改动任何文件）",
                "render_entry": self._render_entry(),
                "performance_baseline": self._perf_note(state),
            },
        )
        violations = list(path_violations) + [f"后端文件哈希变化：{p}" for p in hash_changed]
        if violations:
            payload["outcome"] = ReviewOutcome.REJECT_REDLINE.value
        payload["red_line"] = {
            "passed": not violations,
            "violations": violations,
            "checked": len(changed),
            "backend_hash_changed": hash_changed,
        }
        self._verdicts[state.run_id] = payload

        out = self._report_path(state, "S4", "acceptance.json")
        self._write_json(out, payload)
        state.artifacts[f"{task.task_id}/验收报告"] = str(out)
        state.artifacts[f"{task.task_id}/红线校验报告"] = json.dumps(
            payload["red_line"], ensure_ascii=False
        )

    async def _work_deliver(self, state: RunState, task: TaskUnit) -> None:
        """S5：OR 汇总交付清单。"""
        text = await self._ask(
            state,
            task,
            "deliver",
            {
                "artifacts": self._artifact_index(state),
                "red_line_audit": state.red_line_audit or "（由引擎在 S5 出口终审）",
            },
            json_mode=False,
        )
        out = self._report_path(state, "S5", "delivery.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        state.artifacts[f"{task.task_id}/最终交付清单"] = str(out)

    # ------------------------------------------------------------ review
    async def review(self, state: RunState, stage: Stage) -> ReviewOutcome:
        """阶段评审；S4 需返回真实验收结论。"""
        if stage is not Stage.S4_ACCEPT:
            rejected = [
                t.task_id
                for t in state.graph.tasks
                if t.stage == stage.value and t.status is TaskStatus.REJECTED
            ]
            if rejected:
                self.log.append(f"[review] {stage.value} 存在失败任务：{rejected}")
            return ReviewOutcome.PASS

        # 红线一票否决：代码判定优先于模型判定
        if self._violations.get(state.run_id):
            self.log.append("[review] S4 红线否决：存在越界改动")
            return ReviewOutcome.REJECT_REDLINE

        verdict = self._verdicts.get(state.run_id) or {}
        raw = str(verdict.get("outcome", "pass")).strip().lower()
        outcome = _OUTCOME_MAP.get(raw, ReviewOutcome.PASS)
        self.log.append(f"[review] S4 验收结论：{raw} -> {outcome.value}")
        return outcome

    # ------------------------------------------------------------ 模型调用
    def _system_prompt(self, task: TaskUnit) -> str:
        role = get_role(task.owner)
        return (
            f"你是「{role.name}」（编号 {task.owner.value}），前端优化多智能体协作架构中的一员。\n"
            f"职责：{role.responsibility}\n"
            f"可写范围：{role.write_scope or '（见任务单）'}；只读范围：{role.read_only_scope or '（见任务单）'}\n"
            "最高红线 R1：不得修改任何后端文件（api/ service/ domain/ engine/ conf/ main.py 等），"
            "越界改动一律驳回并回退。\n"
            "严禁编造参考物中不存在的信息；无法确认时明确写「未知」，不要用「通常/一般」掩盖推断。\n"
            "严格按提示词要求的结构输出，不要添加多余寒暄。"
        )

    async def _ask(
        self,
        state: RunState,
        task: TaskUnit,
        prompt_name: str,
        context: dict[str, Any],
        *,
        json_mode: bool = True,
    ) -> Any:
        """渲染提示词 -> 取档位 -> 调模型 -> （可选）解析 JSON，失败自动纠正重试。"""
        profile = self.router.resolve(task.slot)
        prompt = render_prompt(prompt_name, **context)
        system = self._system_prompt(task)
        last_error: Exception | None = None
        for attempt in range(self.max_json_retries + 1):
            text = await self.gateway.complete(profile, prompt, system=system)
            if not json_mode:
                return text
            try:
                return extract_json(text)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                self.log.append(f"[retry] {task.task_id} JSON 解析失败（第 {attempt + 1} 次）：{exc}")
                prompt = (
                    f"{prompt}\n\n【纠正】上一次输出不是合法 JSON（{exc}）。"
                    "请只输出一个 JSON 对象，不要解释、不要代码围栏。"
                )
        raise ValueError(f"模型连续 {self.max_json_retries + 1} 次未返回合法 JSON：{last_error}")

    # ------------------------------------------------------------ 文件写入（红线网关）
    def _apply_files(
        self, task: TaskUnit, files: list[dict]
    ) -> tuple[list[str], list[str], list[str]]:
        """把模型产出的文件落到磁盘，逐条过红线 + 任务单边界。"""
        changed: list[str] = []
        proposed: list[str] = []
        violations: list[str] = []
        for item in files:
            rel = str(item.get("path", "")).strip().replace("\\", "/").lstrip("./")
            content = item.get("content")
            if not rel or not isinstance(content, str):
                violations.append(f"文件项缺少 path/content：{str(item)[:120]}")
                continue
            record = red_line.check_changes([rel]).records[0]
            if not record.allowed:
                violations.append(f"{rel} -> {record.reason}")
                continue
            if task.boundary.writable and not any(
                fnmatch.fnmatch(rel.lower(), pat.lower().lstrip("./"))
                for pat in task.boundary.writable
            ):
                violations.append(f"{rel} -> 越出任务单可写范围 {task.boundary.writable}")
                continue
            # 反「整文件重写」保护：既有文件若被大幅缩小，几乎必然是把真实页面
            # 替换成了脚手架示例（历史事故：App.vue 2758 行 -> 3 张卡片）。直接拒绝落盘。
            target = PROJECT_ROOT / rel
            if target.is_file():
                old_len = len(target.read_text(encoding="utf-8", errors="replace"))
                new_len = len(content)
                if old_len >= 4000 and new_len < old_len * 0.6:
                    reason = (
                        f"{rel} -> 疑似整文件重写被拒：新内容 {new_len} 字符，仅为原文 "
                        f"{old_len} 字符的 {new_len / old_len:.0%}（保护既有功能，红线 R4）"
                    )
                    violations.append(reason)
                    self.log.append(f"[redline] {task.task_id} {reason}")
                    continue
            elif DENY_NEW_FILES:
                reason = f"{rel} -> 新建文件被拒：本次只允许改造既有文件，以保持整体框架不变"
                violations.append(reason)
                self.log.append(f"[redline] {task.task_id} {reason}")
                continue
            if not self.apply_changes:
                proposed.append(rel)
                continue
            if target.is_file():
                # 既有文件：保持原有行尾与 BOM，避免流水线把仓库行尾搅乱
                self._write_existing(
                    target, target.read_text(encoding="utf-8", errors="replace"), content
                )
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="")
            changed.append(rel)
        return changed, proposed, violations

    # ------------------------------------------------------------ 补丁式落盘
    @staticmethod
    def _split_newline(text: str) -> str:
        """返回文本的主导行尾。"""
        return "\r\n" if "\r\n" in text else "\n"

    @classmethod
    def _restore_newline(cls, text: str, newline: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.replace("\n", "\r\n") if newline == "\r\n" else normalized

    def _write_existing(self, target: Path, raw: str, new_text: str) -> None:
        """写回既有文件：保持原有行尾与 UTF-8 BOM。"""
        body = self._restore_newline(new_text, self._split_newline(raw))
        had_bom = raw.startswith("\ufeff")
        if had_bom and not body.startswith("\ufeff"):
            body = "\ufeff" + body
        elif not had_bom and body.startswith("\ufeff"):
            body = body[1:]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8", newline="")

    def _apply_edits(
        self, task: TaskUnit, edits: list[dict]
    ) -> tuple[list[str], list[str], list[str]]:
        """补丁模式：模型给 find/replace 片段，代码在原文上做精确替换。

        大文件（src/App.vue 7.4 万字符）要求模型整文件重写必然失败——实测它只会吐出
        几十字符的占位内容而被防重写保护拦下。补丁模式把「改哪里」交给模型，把
        「怎么落盘」交给代码，既省 token 又杜绝整文件被清空。
        """
        changed: list[str] = []
        proposed: list[str] = []
        violations: list[str] = []

        grouped: dict[str, list[dict]] = {}
        order: list[str] = []
        for item in edits:
            rel = str(item.get("path", "")).strip().replace("\\", "/").lstrip("./")
            find = item.get("find")
            repl = item.get("replace")
            if (
                not rel
                or not isinstance(find, str)
                or not isinstance(repl, str)
                or not find.strip()
            ):
                violations.append(f"补丁项缺少 path/find/replace：{str(item)[:120]}")
                continue
            if rel not in grouped:
                grouped[rel] = []
                order.append(rel)
            grouped[rel].append({"find": find, "replace": repl})

        if len(edits) > MAX_EDITS_PER_TASK:
            violations.append(
                f"补丁条目过多（{len(edits)} > {MAX_EDITS_PER_TASK}），整批驳回，请拆小后重报"
            )
            return changed, proposed, violations

        for rel in order:
            record = red_line.check_changes([rel]).records[0]
            if not record.allowed:
                violations.append(f"{rel} -> {record.reason}")
                continue
            if task.boundary.writable and not any(
                fnmatch.fnmatch(rel.lower(), pat.lower().lstrip("./"))
                for pat in task.boundary.writable
            ):
                violations.append(f"{rel} -> 越出任务单可写范围 {task.boundary.writable}")
                continue

            target = PROJECT_ROOT / rel
            if not target.is_file():
                violations.append(f"{rel} -> 补丁目标不是既有文件（本次禁止新建文件）")
                continue

            raw = target.read_text(encoding="utf-8", errors="replace")
            text = raw
            ok = True
            for idx, item in enumerate(grouped[rel], 1):
                find = item["find"]
                hits = text.count(find)
                if hits == 0:
                    violations.append(
                        f"{rel} 第 {idx} 处补丁 -> 锚点未在原文中找到（逐字符比对失败），该文件未改动"
                    )
                    ok = False
                    break
                if hits > 1:
                    violations.append(
                        f"{rel} 第 {idx} 处补丁 -> 锚点在原文中出现 {hits} 次，不唯一，拒绝盲改"
                    )
                    ok = False
                    break
                text = text.replace(find, item["replace"], 1)
            if not ok:
                continue
            if text == raw:
                violations.append(f"{rel} -> 补丁应用后内容无变化")
                continue
            if len(raw) >= 4000 and len(text) < len(raw) * 0.6:
                violations.append(
                    f"{rel} -> 补丁后文件大幅缩小（{len(text)}/{len(raw)} 字符），"
                    "保护既有功能，拒绝落盘（红线 R4）"
                )
                continue
            if not self.apply_changes:
                proposed.append(rel)
                continue
            self._write_existing(target, raw, text)
            changed.append(rel)
            self.log.append(
                f"[patch] {task.task_id} {rel} 精确应用 {len(grouped[rel])} 处补丁"
            )
        return changed, proposed, violations

    # ------------------------------------------------------------ 产物落盘
    def _workspace(self, state: RunState) -> Path:
        raw = state.workspace or "docs/frontend-optimizer/workspace"
        path = Path(raw)
        return path if path.is_absolute() else PROJECT_ROOT / path

    def _report_path(self, state: RunState, stage: str, filename: str) -> Path:
        return self._workspace(state) / state.run_id[:8] / stage / filename

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------ 上下文收集
    @staticmethod
    def _page_inventory(limit: int = 40) -> str:
        """前端页面清单（只读扫描，不越界）。"""
        root = PROJECT_ROOT / "external" / "customer-service-frontend"
        if not root.is_dir():
            return "（未找到 external/customer-service-frontend）"
        rows: list[str] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in {"node_modules", "dist", ".vite", "__pycache__"} for part in path.parts):
                continue
            rows.append(str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
            if len(rows) >= limit:
                rows.append("…（已截断）")
                break
        return "\n".join(rows) or "（空目录）"

    @staticmethod
    def _expand(pattern: str, limit: int = 6) -> list[str]:
        """把可写范围里的 glob 展开成具体相对路径。"""
        cleaned = pattern.replace("\\", "/").lstrip("./")
        if any(ch in cleaned for ch in "*?["):
            root = PROJECT_ROOT
            hits = sorted(
                str(p.relative_to(root)).replace("\\", "/")
                for p in root.glob(cleaned)
                if p.is_file()
            )
            return hits[:limit]
        return [cleaned]

    def _existing_sources(
        self, task: TaskUnit, *, per_file: int = 160000, total: int = 320000
    ) -> str:
        """把可写范围内「现有文件」的内容喂给模型。

        没有这一步，模型会凭标题重写整个文件（把真实页面精简成脚手架），必须给原文。
        """
        rows: list[str] = []
        used = 0
        for pattern in task.boundary.writable:
            for rel in self._expand(pattern):
                path = PROJECT_ROOT / rel if not Path(rel).is_absolute() else Path(rel)
                if not path.is_file() or used >= total:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                snippet = text[:per_file]
                if len(text) > per_file:
                    snippet += f"\n…（原文共 {len(text)} 字符，已截断）"
                block = f"### 现有文件：{rel}\n```\n{snippet}\n```"
                rows.append(block)
                used += len(snippet)
        if not rows:
            return "（可写范围内暂无现有文件，属于新增文件）"
        return "\n\n".join(rows)

    @staticmethod
    def _existing_tokens(state: RunState) -> str:
        if not state.tokens:
            return "（无）"
        return json.dumps(state.tokens, ensure_ascii=False)[:4000]

    @staticmethod
    def _render_entry() -> str:
        for rel in RENDER_ENTRY_CANDIDATES:
            if (PROJECT_ROOT / rel).is_file():
                return rel
        return "（未找到可渲染入口）"

    def _lane_outputs(self, state: RunState) -> str:
        """把各泳道自检报告的内容内联（只给路径模型读不到）。"""
        rows = [
            f"### {key}\n{_inline_file(value, 2500)}"
            for key, value in state.artifacts.items()
            if "泳道自检报告" in key
        ]
        return "\n\n".join(rows) or "（无）"

    def _perf_note(self, state: RunState) -> str:
        rows = [
            f"### {k}\n{_inline_file(v, 1500)}"
            for k, v in state.artifacts.items()
            if "泳道自检报告" in k and "E5-PF" in k
        ]
        return "\n\n".join(rows) or "（未采集性能基线）"

    @staticmethod
    def _changed_paths(state: RunState) -> list[str]:
        return [v for k, v in state.artifacts.items() if k.startswith("code:")]

    def _artifact_index(self, state: RunState) -> str:
        rows = [f"- {name} -> {path}" for name, path in state.artifacts.items()]
        return "\n".join(rows) or "（无产物）"

    def failures(self, state: RunState) -> list[str]:
        """本次运行中被驳回的任务与原因（供 CLI 汇总）。"""
        return list(self._failures.get(state.run_id, []))


def slot_for(task_complexity: ComplexityInput) -> ModelSlot:
    """按复杂度画像取档位，可直接用于构造 TaskUnit.slot。"""
    return judge_model_slot(task_complexity)
