# 前端优化多智能体协作架构（已接入模型 v1.2 · 分档位独立配置）

> 排版依据：`前端页面优化-多智能体协作架构方案.md` v1.0
> 代码位置：`frontend_optimizer/`
> 定位：**构建期编排工具**，与客服后端运行时解耦，不参与 `/api/chat` 链路。

---

## 一、这是什么

一套「1 名统筹规划 + 6 名执行专家」的多智能体协作骨架，用于在**完全不改动后端**的前提下，
对存量前端页面完成「商务风格」视觉与体验升级。

当前状态：**架构 + 执行器均已可用，模型档位已配置并可真实调用**。

| 能力 | 状态 |
|---|---|
| 角色编制 / 阶段机 / 任务 DAG | ✅ 可用 |
| 红线校验（路径 + 后端哈希终审） | ✅ 可用（写入网关强制拦截） |
| 设计令牌模型 / CSS 导出 | ✅ 可用 |
| 模型档位解析（provider / model / base_url） | ✅ 三个档位已配置 |
| 真实模型接入（`LLMHandlers`） | ✅ 已实现，S0→S5 全流程真机跑通 |
| 真机视觉回归（CDP 截图比对） | ⏳ 由 `headless-cdp-verify` 技能承担，尚未接入执行器 |

---

## 二、专家编制（7 名）

| 编号 | 角色 | 类型 | 泳道 | 模型档位 | 技能 |
|---|---|---|---|---|---|
| OR | 总控编排专家 | 统筹 | — | 高性能 | frontend-design |
| E1-DS | 设计规范专家 | 执行 | — | 高性能 + 轻量 | frontend-design、joy2know-design-tokens |
| E2-LY | 布局重构专家 | 执行 | A | 高性能 + 轻量 | frontend-design |
| E3-ST | 样式与主题专家 | 执行 | B | 高性能 + 轻量 | frontend-design、joy2know-design-tokens |
| E4-IX | 交互与动效专家 | 执行 | C | 高性能 + 轻量 | frontend-design |
| E5-PF | 性能优化专家 | 执行 | D | 高性能 + 轻量 | headless-cdp-verify |
| E6-QA | 质量验收专家 | 执行 | — | 视觉 + 高性能 + 轻量 | headless-cdp-verify、agent-browser |

### 关于「是否增删专家」的结论

**未增未删，6 名执行专家全部保留。** 判断依据：

| 角色 | 能否省略 | 理由 |
|---|---|---|
| OR | 不可省 | 唯一拥有「规范冻结」「变更准入」「冲突裁决」权的角色 |
| E1-DS | 不可省 | 商务风格需要唯一视觉来源，否则多页必然风格漂移 |
| E2 / E3 / E4 | 不可合并 | 结构 / 样式 / 交互分属不同文件类型，合并会立刻产生同一文件并行写入冲突 |
| E5-PF | 不可省 | 验收标准含「性能不劣化」，需独立采集与基线比对 |
| E6-QA | 不可省且必须独立 | 验收方若与执行方同体，红线校验即失效 |

---

## 三、模型档位：按任务复杂度选，不是按角色选

档位只有 **3 个**，6 名执行专家共用；谁走哪档由 `judge_model_slot()` 逐任务裁定
（`needs_decision / cross_scope / deep_reasoning / hard_to_revert` 任一为真 → 高性能）。

| 档位 | 用途 | 当前型号 |
|---|---|---|
| `reasoning` | 设计 / 取舍 / 架构 / 根因分析 | `deepseek-v4-pro`（阿里云百炼 MaaS） |
| `fast` | 执行既定规范、批量替换、采集整理 | `deepseek-flash`（DeepSeek 官方 · V4.1-Flash） |
| `vision` | E6-QA 多断点截图比对（可选，未配置自动降级为 reasoning） | `deepseek-flash`（官方型号支持图片输入） |

角色与档位的对应关系：

| 角色 | 主要档位 | 说明 |
|---|---|---|
| OR | 高性能 | 拆 DAG、冻结规范、冲突裁决、交付把关 |
| E1-DS | 高性能（主）+ 轻量 | 色彩体系推导走高性能；令牌导出走轻量 |
| E2-LY | 高性能（主）+ 轻量 | 跨页结构方案走高性能；批量类名替换走轻量 |
| E3-ST | 高性能（主）+ 轻量 | 主题架构走高性能；颜色值替换走轻量 |
| E4-IX | 高性能（主）+ 轻量 | 交互状态机走高性能；事件绑定样板走轻量 |
| E5-PF | 轻量（主）+ 高性能 | 资源压缩 / 指标采集走轻量；渲染路径优化走高性能 |
| E6-QA | 高性能 + 轻量 + 视觉 | 多断点截图比对走视觉档；清单核对走轻量 |

### 配置方式（密钥绝不写进代码）

**每个档位一套 provider / base_url / api_key**，互不干扰 —— 因此可以「高性能档走 A 厂商、
轻量档走 B 厂商」。解析优先级：`FRONTEND_OPTIMIZER_{档位}_XXX` > `FRONTEND_OPTIMIZER_XXX` > 内置推荐表。

本机 `.env` 现状（明文密钥只留本机，已打码）：

```dotenv
# 高性能档 -> 阿里云百炼 MaaS（OpenAI 兼容端点）
FRONTEND_OPTIMIZER_REASONING_PROVIDER=aliyun-maas
FRONTEND_OPTIMIZER_REASONING_MODEL=deepseek-v4-pro
FRONTEND_OPTIMIZER_REASONING_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
FRONTEND_OPTIMIZER_REASONING_API_KEY=sk-sp-****

# 轻量档 -> DeepSeek 官方
FRONTEND_OPTIMIZER_FAST_PROVIDER=deepseek
FRONTEND_OPTIMIZER_FAST_MODEL=deepseek-flash
FRONTEND_OPTIMIZER_FAST_BASE_URL=https://api.deepseek.com
FRONTEND_OPTIMIZER_FAST_API_KEY=sk-****
```

> ⚠️ 本项目**不再回退** `LLM_API_KEY / OPENAI_API_KEY` —— 那两个变量是客服后端运行时
> （`conf/config.py`）在用的，构建期工具与之刻意隔离，避免串用后端密钥；原「硅基流动」配置已废弃。

支持的供应商与内置网关：

| provider | base_url | 推荐型号（reasoning / fast / vision） |
|---|---|---|
| `deepseek`（默认） | `https://api.deepseek.com` | deepseek-v4-pro / deepseek-flash / deepseek-flash |
| `aliyun-maas` | `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` | deepseek-v4-pro / deepseek-v4.1-flash / — |
| `siliconflow` | `https://api.siliconflow.cn/v1` | DeepSeek-V4-Pro / DeepSeek-V4-Flash / Qwen3-VL-32B-Instruct |
| `dashscope` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen3-max / qwen-plus / qwen-vl-max |
| `moonshot` | `https://api.moonshot.cn/v1` | kimi-k2-0905-preview / moonshot-v1-32k / — |
| `zhipu` | `https://open.bigmodel.cn/api/paas/v4` | glm-4.6 / glm-4-flash / glm-4v |
| `openai` | `https://api.openai.com/v1` | gpt-5 / gpt-5-mini / gpt-5 |

> 型号名以厂商 `/models` 列表为准（`deepseek` 与 `aliyun-maas` 均已核对）；改完用
> `uv run python -m frontend_optimizer.run --check` 验证连通性即可。

---

## 四、阶段机

```text
S0 需求对齐(OR) -> S1 规范冻结(E1-DS) -> S2 四泳道并行 -> S3 集成对齐(OR+E1) -> S4 验收(E6-QA) -> S5 交付(OR)
```

- S2 四条泳道 **完全并行**：A 布局 / B 样式 / C 交互 / D 性能（按依赖拓扑分层，`asyncio.gather`）。
- 回退规则：S4 缺陷 → 退回对应泳道；涉及规范 → 退回 S1；触碰红线 → 无条件回退。
- 回退次数上限 `max_rollbacks`（默认 2），防止模型反复挑刺导致死循环。
- 每个阶段由 `LLMHandlers.plan()` 产任务、`run_task()` 干活、`review()` 评审；
  引擎只执行「本次新产出且待办」的任务，回退后不会重跑历史任务。

| 阶段 | 负责 | 出口条件 | 提示词模板 |
|---|---|---|---|
| S0 | OR | 任务分解表确认 | `orchestrator_plan` |
| S1 | E1-DS | 规范冻结令（OR 签发） | `design_freeze` |
| S2 | E2/E3/E4/E5 | 各泳道自检通过 | `lane_work` |
| S3 | OR + E1-DS | 无冲突、风格统一 | `integrate` |
| S4 | E6-QA | 缺陷清零、红线通过 | `accept` |
| S5 | OR | 交付清单签署 | `deliver` |

---

## 五、代码落位

| 关注点 | 文件 |
|---|---|
| 全局常量 / 技能路径 | `frontend_optimizer/config.py` |
| 角色档案（7 名） | `frontend_optimizer/agents/roles.py` |
| 专家基类 | `frontend_optimizer/agents/base.py` |
| 阶段机 + 回退规则 | `frontend_optimizer/orchestrator/stages.py` |
| 任务 DAG / 泳道 / 文件边界 | `frontend_optimizer/orchestrator/tasks.py` |
| 运行状态聚合根 | `frontend_optimizer/orchestrator/state.py` |
| 编排主循环 | `frontend_optimizer/orchestrator/engine.py` |
| **阶段执行器（Noop / LLM）** | `frontend_optimizer/orchestrator/handlers.py` |
| **CLI（看配置 / 验连通 / 跑流水线）** | `frontend_optimizer/run.py` |
| 红线校验 + 哈希基线 | `frontend_optimizer/guardrails/red_line.py` |
| **模型档位解析（provider/model/base_url）** | `frontend_optimizer/model/profiles.py` |
| 档位判定（复杂度） | `frontend_optimizer/model/slots.py` |
| 设计令牌模型 / 导出 | `frontend_optimizer/tokens/schema.py`、`tokens/exporter.py` |
| 技能注册 + 依赖自检 | `frontend_optimizer/skills/registry.py` |
| 阶段提示词（6 个） | `frontend_optimizer/prompts/jinja2/` |
| 离线自检 | `frontend_optimizer/selftest.py` |

---

## 六、怎么跑

```powershell
# 1. 看当前生效的档位、型号、网关、密钥来源（不打印明文）
uv run python -m frontend_optimizer.run --print-config

# 2. 真实调用每个档位一次，验证 provider/model/base_url/key 是否可用
uv run python -m frontend_optimizer.run --check

# 3. 跑完整流水线（dry-run：只出报告，不把泳道产出写进磁盘）
uv run python -m frontend_optimizer.run --goal "把首页改成商务风格" --dry-run

# 4. 真跑：泳道产出会真实落盘（仍受红线白名单限制）
uv run python -m frontend_optimizer.run --goal "把首页改成商务风格"

# 5. 离线架构自检（不需要密钥）
uv run python -m frontend_optimizer.selftest
```

产物落在 `docs/frontend-optimizer/workspace/<run_id>/<阶段>/`：

```text
S0/task-plan.json          任务分解与泳道分配表
S1/design-tokens.json      归一化后的设计令牌（可直接导出 CSS）
S1/design-tokens.raw.json  模型原始输出（便于对比归一化）
S1/design-tokens.css       :root 变量文件
S2/<task_id>.json          各泳道自检报告 + 实际落盘清单 + 越界驳回记录
S3/integration.json        冲突清单与集成结论
S4/acceptance.json         验收结论 + 红线校验报告
S5/delivery.md             最终交付清单
```

---

## 七、执行器的三个关键机制

1. **提示词渲染**：`prompts/jinja2/*.jinja2` 用 jinja2 现场渲染（`render_prompt()`）。
2. **JSON 容错**：模型输出常带 ```json 围栏、前后废话、尾逗号；`extract_json()` 统一抽取，
   解析失败会带「纠正指令」自动重试一次。
3. **红线写入网关**：泳道产出在落盘前逐条过 `red_line.check_changes()` + 任务单 `writable` 边界，
   越界一律驳回并记入 S4 红线报告；S4 结论由**代码强制裁决**（路径违规或后端哈希变化 → 一票否决），
   模型说了不算。

---

## 八、技能落位与安装状态

| 技能 | 用途 | 归属 | SKILL.md | 运行时依赖 |
|---|---|---|---|---|
| `frontend-design` | 生产级前端界面设计 | E1/E2/E3/E4 | ✅ | 无 |
| `joy2know-design-tokens` | 设计参考 -> Design Token -> 页面 | E1/E3 | ✅ | python ✅ |
| `headless-cdp-verify` | 真机 headless + CDP 验证 | E5/E6 | ✅ | node ✅、Chrome ✅ |
| `agent-browser` | 批量采集、截图、交互回归 | E6 | ✅ | agent-browser CLI ✅ |

> 技能 SKILL.md 根目录可用环境变量 `SKILL_ROOT` 覆盖（默认 `C:\Users\86195\.workbuddy`）。

---

## 九、红线机制

- ⛔ 黑名单：`api/` `service/` `domain/` `engine/` `task/` `knowledge/` `plan/` `prompts/`
  `repository/` `models/` `conf/` `infrastructure/` `flow_config/` `scripts/` `test/`
  `main.py` `pyproject.toml` `uv.lock` `.env` 等。
- ✅ 白名单：`external/customer-service-frontend/**`、`static/**`。
- 四重保障：① 任务单标注允许路径；② 落入磁盘前逐条过白名单 + 边界检查；
  ③ S4 由代码强制红线裁决；④ S5 用后端文件 SHA256 基线终审。

基线与产物落在 `docs/frontend-optimizer/workspace/`，不污染后端目录。

---

## 十、运行自检

```powershell
uv run python -m frontend_optimizer.selftest
```

覆盖：编制 7 名 / 技能 4 个就绪 / 档位判定 + 留空报错 / 红线放行与拦截 /
写入门禁（后端与白名单外被拦）/ 令牌导出 / 提示词渲染 / JSON 抽取 /
阶段机 S0→S5 / 假网关跑通 `LLMHandlers` / 档位路由与视觉档降级。
