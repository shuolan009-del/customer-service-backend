"""设计令牌模型。字段对齐 joy2know-design-tokens 的「8 项最小集合」。

来源标注规则（该技能的防幻觉硬约束）：
    USER       用户提供的
    EXTRACTED  我从参考物提取的（附具体位置）
    INFERRED   我推断的（必须显式标注，禁止用「通常/一般/建议」掩盖）
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TokenSource(str, Enum):
    """令牌来源。"""

    USER = "user"
    EXTRACTED = "extracted"
    INFERRED = "inferred"


class TokenValue(BaseModel):
    """单个令牌值。"""

    value: str
    source: TokenSource = TokenSource.INFERRED
    note: str = ""


class DesignTokens(BaseModel):
    """一份可落盘、可引用、可校验的设计令牌。"""

    # 1. 主色与语义色
    color_primary: TokenValue
    color_success: TokenValue
    color_warning: TokenValue
    color_danger: TokenValue
    # 2. 中性色阶
    gray_scale: dict[str, TokenValue] = Field(default_factory=dict)
    # 3. 背景与前景
    bg_base: TokenValue
    bg_subtle: TokenValue
    fg_base: TokenValue
    fg_muted: TokenValue
    # 4. 字体与字号阶梯
    font_sans: TokenValue
    text_scale: dict[str, TokenValue] = Field(default_factory=dict)
    # 5. 间距节奏
    space_scale: dict[str, TokenValue] = Field(default_factory=dict)
    # 6. 圆角与阴影（建议项，缺省按 0 处理）
    radius_scale: dict[str, TokenValue] = Field(default_factory=dict)
    shadow_scale: dict[str, TokenValue] = Field(default_factory=dict)
    # 7. 栅格与断点
    breakpoints: dict[str, TokenValue] = Field(default_factory=dict)
    # 8. 元信息
    reference: str = ""   # 参考物来源，便于溯源

    def all_values(self) -> list[tuple[str, TokenValue]]:
        """展平所有令牌，返回 (名称, 值) 列表。"""
        flat: list[tuple[str, TokenValue]] = []
        for name, val in self.__dict__.items():
            if isinstance(val, TokenValue):
                flat.append((name, val))
            elif isinstance(val, dict):
                flat.extend((f"{name}.{k}", v) for k, v in val.items())
        return flat

    def inferred_fields(self) -> list[str]:
        """列出所有被标注为「推断」的令牌名，用于回报可信度。"""
        return [
            name
            for name, val in self.all_values()
            if isinstance(val, TokenValue) and val.source is TokenSource.INFERRED
        ]

    def missing_minimum_set(self) -> list[str]:
        """自检：返回缺失的 8 项最小集合字段。"""
        required = [
            "color_primary",
            "color_success",
            "color_warning",
            "color_danger",
            "bg_base",
            "bg_subtle",
            "fg_base",
            "fg_muted",
            "font_sans",
        ]
        return [name for name in required if getattr(self, name, None) is None]
