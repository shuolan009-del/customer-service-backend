"""模型档位 -> 具体模型（provider / model / base_url / api_key）的解析表。

设计原则（与方案文档 §1 / §6 一致）：
    档位由「任务复杂度」驱动，而不是由角色驱动 —— 所以只有 3 个档位，
    6 名执行专家共用它们，谁用哪档由 judge_model_slot() 逐任务裁定。

    reasoning  高性能：设计 / 取舍 / 架构 / 根因分析
    fast       轻量  ：执行既定规范、批量替换、采集整理
    vision     多模态：E6-QA 的多断点截图比对（未配置时自动降级为 reasoning）

配置粒度（v2 起）：**每个档位一套 provider / base_url / api_key**，互不干扰。
    因此可以「高性能档走阿里云 MaaS、轻量档走 DeepSeek 官方」，两档用不同密钥。

    解析优先级：档位级 env  >  全局级 env  >  内置推荐表
        FRONTEND_OPTIMIZER_{SLOT}_PROVIDER  >  FRONTEND_OPTIMIZER_PROVIDER  >  DEFAULT_PROVIDER
        FRONTEND_OPTIMIZER_{SLOT}_MODEL     >  RECOMMENDED_MODELS[provider][slot]
        FRONTEND_OPTIMIZER_{SLOT}_BASE_URL  >  FRONTEND_OPTIMIZER_BASE_URL  >  PROVIDER_BASE_URLS[provider]
        FRONTEND_OPTIMIZER_{SLOT}_API_KEY   >  FRONTEND_OPTIMIZER_API_KEY

    {SLOT} 取 REASONING / FAST / VISION。

密钥规则：
    - 本文件不写死任何明文密钥，密钥只从环境变量 / 项目根 .env 读取；
    - **刻意不回退 LLM_API_KEY / OPENAI_API_KEY** —— 那两个变量是客服后端运行时
      （conf/config.py）在用的，本项目与之严格隔离，避免串用后端密钥。

    FRONTEND_OPTIMIZER_TEMPERATURE        采样温度，默认 0.0；填 none 表示不传该参数
    FRONTEND_OPTIMIZER_TIMEOUT            单次调用超时秒数，默认 300（思考型模型较慢）

查看当前生效配置：uv run python -m frontend_optimizer.run --print-config
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

from frontend_optimizer.config import PROJECT_ROOT
from frontend_optimizer.model.slots import ModelSlot

ENV_PREFIX = "FRONTEND_OPTIMIZER_"

# ---------------------------------------------------------------- 供应商默认值
# 全部走 OpenAI 兼容协议，因此只需要 provider + base_url + api_key 三元组。
PROVIDER_BASE_URLS: dict[str, str] = {
    # DeepSeek 官方（用户指定的地址，不带 /v1 亦可）
    "deepseek": "https://api.deepseek.com",
    # 阿里云百炼 · 模型广场（MaaS），只用其 OpenAI 兼容端点
    "aliyun-maas": "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "openai": "https://api.openai.com/v1",
}

# 默认供应商：只在本档既没给档位级、也没给全局级 PROVIDER 时兜底。
DEFAULT_PROVIDER = "deepseek"

# 各供应商的推荐型号（型号名以厂商 /models 列表为准）。
# 换厂商时改这里，或用 FRONTEND_OPTIMIZER_{SLOT}_MODEL 单点覆盖。
RECOMMENDED_MODELS: dict[str, dict[str, str]] = {
    "deepseek": {
        # 官方 /models 实际返回：deepseek-flash(DeepSeek-V4.1-Flash)、deepseek-v4-pro
        "reasoning": "deepseek-v4-pro",
        "fast": "deepseek-flash",
        "vision": "deepseek-flash",  # V4.1-Flash 支持图片输入
    },
    "aliyun-maas": {
        "reasoning": "deepseek-v4-pro",
        "fast": "deepseek-v4.1-flash",
        "vision": "",  # 该端点无多模态型号时留空，路由会自动降级
    },
    "siliconflow": {
        "reasoning": "deepseek-ai/DeepSeek-V4-Pro",
        "fast": "deepseek-ai/DeepSeek-V4-Flash",
        "vision": "Qwen/Qwen3-VL-32B-Instruct",
    },
    "dashscope": {
        "reasoning": "qwen3-max",
        "fast": "qwen-plus",
        "vision": "qwen-vl-max",
    },
    "moonshot": {
        "reasoning": "kimi-k2-0905-preview",
        "fast": "moonshot-v1-32k",
        "vision": "",
    },
    "zhipu": {
        "reasoning": "glm-4.6",
        "fast": "glm-4-flash",
        "vision": "glm-4v",
    },
    "openai": {
        "reasoning": "gpt-5",
        "fast": "gpt-5-mini",
        "vision": "gpt-5",
    },
}

DEFAULT_TEMPERATURE = 0.0
DEFAULT_TIMEOUT = 300.0

# 「不传 temperature」的写法（部分推理模型不接受该参数）
_FALSY_VALUES = {"none", "null", "off", "false", "no"}


# ---------------------------------------------------------------- 模型档位档案
class ModelProfile(BaseModel):
    """一个模型档位的配置。api_key 仅驻留内存，不参与序列化落盘。"""

    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = Field(default=None, repr=False)
    api_key_source: str | None = None   # 密钥来自哪个环境变量（只记名字，不记明文）
    api_key_env: str | None = None      # 该档位首选的环境变量名（用于报错提示）
    slot: str | None = None             # 该档案属于哪个档位（reasoning/fast/vision）
    temperature: float | None = DEFAULT_TEMPERATURE
    timeout: float = DEFAULT_TIMEOUT
    extra: dict = Field(default_factory=dict)

    @property
    def configured(self) -> bool:
        """是否已配置可用的 provider + model。"""
        return bool(self.provider and self.model)

    @property
    def resolved_base_url(self) -> str | None:
        """显式 base_url 优先，否则按 provider 取内置默认值。"""
        if self.base_url:
            return self.base_url
        if not self.provider:
            return None
        return PROVIDER_BASE_URLS.get(self.provider.lower())

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    def label(self) -> str:
        """供日志 / 自检打印的可读标签（不含密钥）。"""
        if not self.configured:
            return "未配置"
        return f"{self.provider}/{self.model}"


# ---------------------------------------------------------------- .env 读取
def load_dotenv_if_present(path: Path | None = None) -> bool:
    """把项目根 .env 读进 os.environ（只读，不修改文件）。

    已存在的环境变量优先，不会被 .env 覆盖；返回是否成功读取到文件。
    """
    target = path or (PROJECT_ROOT / ".env")
    if not target.is_file():
        return False
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value
    return True


# ---------------------------------------------------------------- env 读取工具
def slot_env_name(slot: ModelSlot, field: str) -> str:
    """档位级环境变量名，例如 FRONTEND_OPTIMIZER_REASONING_MODEL。"""
    return f"{ENV_PREFIX}{slot.value.upper()}_{field}"


def _read(name: str) -> str | None:
    """读环境变量；空字符串视为未设置。"""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return raw.strip()


def _env(name: str, default: str | None = None) -> str | None:
    """全局级环境变量（FRONTEND_OPTIMIZER_xxx）。"""
    return _read(f"{ENV_PREFIX}{name}") or default


def _slot_env(slot: ModelSlot, field: str, default: str | None = None) -> str | None:
    """档位级环境变量（FRONTEND_OPTIMIZER_{SLOT}_xxx）。"""
    return _read(slot_env_name(slot, field)) or default


def _resolve_number(slot: ModelSlot, field: str, default: float | None) -> float | None:
    """档位级 > 全局级；值为 none/null/off 时返回 None（表示不传该参数）。"""
    for raw in (_slot_env(slot, field), _env(field)):
        if raw is None:
            continue
        if raw.lower() in _FALSY_VALUES:
            return None
        return float(raw)
    return default


def current_provider() -> str:
    """全局默认供应商（仅作兜底；各档位可有自己的 provider）。"""
    return (_env("PROVIDER") or DEFAULT_PROVIDER).lower()


def resolve_api_key(slot: ModelSlot | None = None) -> tuple[str | None, str | None]:
    """按「档位级 > 全局级」取密钥，返回 (密钥, 来源变量名)。

    刻意不回退 LLM_API_KEY / OPENAI_API_KEY：那两个变量属于客服后端运行时。
    """
    names: list[str] = []
    if slot is not None:
        names.append(slot_env_name(slot, "API_KEY"))
    names.append(f"{ENV_PREFIX}API_KEY")
    for name in names:
        raw = _read(name)
        if raw:
            return raw, name
    return None, None


def env_overrides(slot: ModelSlot) -> list[str]:
    """列出该档位被显式覆盖的环境变量名（用于 --print-config 溯源）。"""
    candidates = [
        slot_env_name(slot, "PROVIDER"),
        slot_env_name(slot, "MODEL"),
        slot_env_name(slot, "BASE_URL"),
        slot_env_name(slot, "API_KEY"),
        f"{ENV_PREFIX}PROVIDER",
        f"{ENV_PREFIX}MODEL",
        f"{ENV_PREFIX}BASE_URL",
        f"{ENV_PREFIX}API_KEY",
    ]
    return [n for n in candidates if _read(n)]


def build_profile(slot: ModelSlot) -> ModelProfile:
    """按「档位级 env > 全局 env > 推荐型号表」的优先级构造一个档位配置。"""
    provider = (_slot_env(slot, "PROVIDER") or _env("PROVIDER") or DEFAULT_PROVIDER).lower()
    recommended = RECOMMENDED_MODELS.get(provider, {})
    model = _slot_env(slot, "MODEL") or recommended.get(slot.value, "")
    base_url = (
        _slot_env(slot, "BASE_URL")
        or _env("BASE_URL")
        or PROVIDER_BASE_URLS.get(provider)
    )
    key, key_source = resolve_api_key(slot)
    timeout = _resolve_number(slot, "TIMEOUT", DEFAULT_TIMEOUT)
    return ModelProfile(
        provider=provider,
        model=model or None,
        base_url=base_url,
        api_key=key,
        api_key_source=key_source,
        api_key_env=slot_env_name(slot, "API_KEY"),
        slot=slot.value,
        temperature=_resolve_number(slot, "TEMPERATURE", DEFAULT_TEMPERATURE),
        timeout=timeout if timeout and timeout > 0 else DEFAULT_TIMEOUT,
    )


# 先读 .env，再构造档位表（导入即生效）
load_dotenv_if_present()

MODEL_PROFILES: dict[ModelSlot, ModelProfile] = {
    slot: build_profile(slot) for slot in ModelSlot
}


def reload_profiles() -> dict[ModelSlot, ModelProfile]:
    """进程内改过环境变量后重新解析（返回新表，不替换模块级常量）。"""
    return {slot: build_profile(slot) for slot in ModelSlot}


def describe_config() -> list[str]:
    """返回人类可读的配置摘要，供 --print-config / 自检打印。"""
    lines = [
        "档位配置（每档可独立指定 provider / base_url / api_key）：",
    ]
    for slot, profile in MODEL_PROFILES.items():
        if not profile.configured:
            lines.append(f"  [{slot.value:<9}] 未配置（provider={profile.provider}）")
            continue
        key_note = profile.api_key_source or f"未找到（应为 {profile.api_key_env}）"
        lines.append(f"  [{slot.value:<9}] {profile.label()}")
        lines.append(f"              base_url    = {profile.resolved_base_url}")
        lines.append(f"              api_key     = {key_note}")
        lines.append(
            f"              temperature = {profile.temperature}"
            f"   timeout = {profile.timeout:g}s"
        )
    lines.append("")
    lines.append("模板（把需要的行写进项目根 .env，不要把明文密钥提交到 git）：")
    lines.append("# ---- 高性能档 ----")
    lines.append(f"{ENV_PREFIX}REASONING_PROVIDER={MODEL_PROFILES[ModelSlot.REASONING].provider or ''}")
    lines.append(f"{ENV_PREFIX}REASONING_MODEL={MODEL_PROFILES[ModelSlot.REASONING].model or ''}")
    lines.append(f"{ENV_PREFIX}REASONING_BASE_URL={MODEL_PROFILES[ModelSlot.REASONING].resolved_base_url or ''}")
    lines.append(f"# {ENV_PREFIX}REASONING_API_KEY=sk-****")
    lines.append("# ---- 轻量档 ----")
    lines.append(f"{ENV_PREFIX}FAST_PROVIDER={MODEL_PROFILES[ModelSlot.FAST].provider or ''}")
    lines.append(f"{ENV_PREFIX}FAST_MODEL={MODEL_PROFILES[ModelSlot.FAST].model or ''}")
    lines.append(f"{ENV_PREFIX}FAST_BASE_URL={MODEL_PROFILES[ModelSlot.FAST].resolved_base_url or ''}")
    lines.append(f"# {ENV_PREFIX}FAST_API_KEY=sk-****")
    lines.append("# ---- 多模态档（留空则 E6-QA 自动降级为高性能档）----")
    lines.append(f"{ENV_PREFIX}VISION_PROVIDER={MODEL_PROFILES[ModelSlot.VISION].provider or ''}")
    lines.append(f"{ENV_PREFIX}VISION_MODEL={MODEL_PROFILES[ModelSlot.VISION].model or ''}")
    lines.append(f"{ENV_PREFIX}VISION_BASE_URL={MODEL_PROFILES[ModelSlot.VISION].resolved_base_url or ''}")
    lines.append(f"# {ENV_PREFIX}VISION_API_KEY=sk-****")
    return lines
