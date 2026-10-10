"""红线校验：保证后端零改动（文档 §0.2、§7）。

机制：路径比对 + 后端文件哈希终审。
命中黑名单 -> 立即驳回 + 回退；越界改动同样驳回。

本模块不修改任何文件，只做校验与快照落盘（快照写在架构工作区，非后端目录）。
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from frontend_optimizer.config import DEFAULT_WORKSPACE, PROJECT_ROOT

# ⛔ 黑名单：命中即无条件驳回 + 回退
RED_LINE_PATTERNS: tuple[str, ...] = (
    "api/**",
    "chitchat/**",
    "clarify/**",
    "conf/**",
    "domain/**",
    "engine/**",
    "external/ecommerce-service-backend/**",
    "external/docker/**",
    "flow_config/**",
    "infrastructure/**",
    "knowledge/**",
    "models/**",
    "plan/**",
    "prompts/**",
    "repository/**",
    "scripts/**",
    "service/**",
    "task/**",
    "test/**",
    "main.py",
    "pyproject.toml",
    "uv.lock",
    ".env",
    ".env.*",
    "*.secret",
    "docs/**/*.openapi.*",
    "docs/**/*swagger*",
)

# ✅ 白名单：仅允许改动前端侧
WHITE_LIST_PATTERNS: tuple[str, ...] = (
    "external/customer-service-frontend/**",
    "static/**",
)

# 后端哈希基线的默认落盘位置（放在架构工作区，避免污染后端）
BASELINE_PATH = DEFAULT_WORKSPACE / "_backend_baseline.json"


class RedLineRecord(BaseModel):
    """一条红线判定记录。"""

    path: str
    allowed: bool
    reason: str


class RedLineReport(BaseModel):
    """红线校验报告。"""

    passed: bool
    checked: int = 0
    violations: list[RedLineRecord] = Field(default_factory=list)
    records: list[RedLineRecord] = Field(default_factory=list)
    backend_hash_changed: list[str] = Field(default_factory=list)


def _norm(path: str | Path) -> str:
    """统一成相对项目根的正斜杠路径。"""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            return str(p.resolve()).replace("\\", "/")
    return str(p).replace("\\", "/").lstrip("./")


def _match(rel: str, patterns: tuple[str, ...]) -> bool:
    """glob 匹配（Windows 下大小写不敏感）。"""
    low = rel.lower()
    return any(fnmatch.fnmatch(low, pat.lower()) for pat in patterns)


def is_red_line(rel_path: str) -> bool:
    """判断某相对路径是否命中后端黑名单。"""
    return _match(_norm(rel_path), RED_LINE_PATTERNS)


def is_allowed(rel_path: str) -> bool:
    """判断某相对路径是否在白名单内且未命中黑名单。"""
    rel = _norm(rel_path)
    if is_red_line(rel):
        return False
    return _match(rel, WHITE_LIST_PATTERNS)


def check_changes(changed_paths: list[str | Path]) -> RedLineReport:
    """对一组改动路径做红线路径比对。"""
    records: list[RedLineRecord] = []
    for raw in changed_paths:
        rel = _norm(raw)
        if is_red_line(rel):
            records.append(
                RedLineRecord(path=rel, allowed=False, reason="命中后端黑名单（R1/R2）")
            )
        elif is_allowed(rel):
            records.append(
                RedLineRecord(path=rel, allowed=True, reason="命中前端白名单（R3）")
            )
        else:
            records.append(
                RedLineRecord(path=rel, allowed=False, reason="越界改动：不在前端白名单内")
            )
    violations = [r for r in records if not r.allowed]
    return RedLineReport(
        passed=not violations,
        checked=len(records),
        violations=violations,
        records=records,
    )


def hash_files(paths: list[str | Path]) -> dict[str, str]:
    """计算文件 SHA256，用于后端哈希终审。"""
    result: dict[str, str] = {}
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if not p.is_file():
            continue
        result[_norm(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def snapshot_backend_paths() -> list[Path]:
    """枚举需要哈希终审的后端文件（用于变更前快照 / 变更后比对）。"""
    files: list[Path] = []
    for pattern in (
        "api",
        "chitchat",
        "clarify",
        "conf",
        "domain",
        "engine",
        "flow_config",
        "infrastructure",
        "knowledge",
        "models",
        "plan",
        "prompts",
        "repository",
        "service",
        "task",
    ):
        root = PROJECT_ROOT / pattern
        if root.is_dir():
            files.extend(
                p
                for p in root.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            )
    for name in ("main.py", "pyproject.toml", "uv.lock"):
        p = PROJECT_ROOT / name
        if p.is_file():
            files.append(p)
    return files


def final_backend_audit(before: dict[str, str]) -> list[str]:
    """终审：比对后端哈希，返回发生变化的文件列表（空即通过）。"""
    after = hash_files(list(before.keys()))
    return [rel for rel in before if before.get(rel) != after.get(rel)]


def save_baseline(path: str | Path | None = None) -> str:
    """把当前后端哈希基线落盘（变更前调用一次）。"""
    target = Path(path) if path else BASELINE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    baseline = hash_files(snapshot_backend_paths())
    target.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return str(target)


def load_baseline(path: str | Path | None = None) -> dict[str, str]:
    """读取已落盘的后端哈希基线；不存在返回空字典。"""
    target = Path(path) if path else BASELINE_PATH
    if not target.is_file():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def audit_against_saved_baseline(path: str | Path | None = None) -> list[str]:
    """用落盘基线做终审，返回发生变化的文件列表（空即通过）。"""
    before = load_baseline(path)
    if not before:
        raise FileNotFoundError(
            "未找到后端哈希基线，请先调用 red_line.save_baseline()。"
        )
    return final_backend_audit(before)
