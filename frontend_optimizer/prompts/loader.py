"""前端优化架构专属的 Jinja2 提示词加载器。

与运行时 prompts/loader.py 隔离，避免互相影响。
"""
from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).resolve().parent / "jinja2"


def load_prompt(name: str) -> str:
    """加载提示词模板文本。"""
    path = _PROMPT_DIR / f"{name}.jinja2"
    if not path.is_file():
        raise FileNotFoundError(f"提示词模板不存在：{path}")
    return path.read_text(encoding="utf-8")


def available_prompts() -> list[str]:
    """列出可用模板名（不含扩展名）。"""
    return sorted(p.stem for p in _PROMPT_DIR.glob("*.jinja2"))
