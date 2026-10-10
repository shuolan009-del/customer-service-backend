"""把设计令牌导出为 design-tokens.css（供前端直接引用）。

规则：页面里颜色 / 字号 / 间距 / 圆角 / 阴影一律走 var(--...)，禁止内联硬编码。
"""
from __future__ import annotations

from pathlib import Path

from frontend_optimizer.tokens.schema import DesignTokens, TokenSource, TokenValue


def _line(name: str, tv: TokenValue) -> str:
    suffix = "  /* [推断] */" if tv.source is TokenSource.INFERRED else ""
    return f"  --{name}: {tv.value};{suffix}"


def to_css(tokens: DesignTokens) -> str:
    """生成 CSS 变量文件正文。"""
    lines: list[str] = [":root {"]

    lines.append("  /* 1. 主色与语义色 */")
    for name in ("color_primary", "color_success", "color_warning", "color_danger"):
        lines.append(_line(name.replace("_", "-"), getattr(tokens, name)))

    lines.append("")
    lines.append("  /* 2. 中性色阶 */")
    lines.extend(_line(f"gray-{k}", v) for k, v in tokens.gray_scale.items())

    lines.append("")
    lines.append("  /* 3. 背景与前景 */")
    for name in ("bg_base", "bg_subtle", "fg_base", "fg_muted"):
        lines.append(_line(name.replace("_", "-"), getattr(tokens, name)))

    lines.append("")
    lines.append("  /* 4. 字体与字号 */")
    lines.append(_line("font-sans", tokens.font_sans))
    lines.extend(_line(f"text-{k}", v) for k, v in tokens.text_scale.items())

    lines.append("")
    lines.append("  /* 5. 间距节奏 */")
    lines.extend(_line(f"space-{k}", v) for k, v in tokens.space_scale.items())

    if tokens.radius_scale or tokens.shadow_scale:
        lines.append("")
        lines.append("  /* 6. 圆角与阴影 */")
        lines.extend(_line(f"radius-{k}", v) for k, v in tokens.radius_scale.items())
        lines.extend(_line(f"shadow-{k}", v) for k, v in tokens.shadow_scale.items())

    if tokens.breakpoints:
        lines.append("")
        lines.append("  /* 7. 断点 */")
        lines.extend(_line(f"bp-{k}", v) for k, v in tokens.breakpoints.items())

    lines.append("}")
    return "\n".join(lines) + "\n"


def export(tokens: DesignTokens, path: str | Path) -> str:
    """写入文件并返回路径字符串。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_css(tokens), encoding="utf-8")
    return str(p)
