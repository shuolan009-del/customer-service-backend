# 前端优化多智能体协作架构（骨架版 v1.0）

> 排版依据：`前端页面优化-多智能体协作架构方案.md` v1.0
> 代码位置：`frontend_optimizer/`
> 定位：**构建期编排工具**，与客服后端运行时解耦，不参与 `/api/chat` 链路。

---

## 一、这是什么

一套「1 名统筹规划 + 6 名执行专家」的多智能体协作骨架，用于在**完全不改动后端**的前提下，
对存量前端页面完成「商务风格」视觉与体验升级。

当前状态：**只搭架构，模型配置留空**。编排、阶段机、任务 DAG、红线校验、令牌导出
均已可运行并通过自检；具体模型（高性能 / 轻量）待你补齐。

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
| E6-QA | 质量验收专家 | 执行 | — | 高性能 + 轻量 | headless-cdp-verify、agent-browser |

### 关于「是否增删专家」的结论

**未增未删，6 名执行专家全部保留。** 判断依据：

| 角色 | 能否省略 | 理由 |
|---|---|---|
| OR | 不可省 | 唯一拥有「规范冻结」「变更准入」「冲突裁决」权的角色 |
| E1-DS | 不可省 | 商务风格需要唯一视觉来源，否则多页必然风格漂移 |
| E2 / E3 / E4 | 不可合并 | 结构 / 样式 / 交互分属不同文件类型，合并会立刻产生同一文件并行写入冲突 |
| E5-PF | 不可省 | 验收标准含「性能不劣化」，需独立采集与基线比对 |
| E6-QA | 不可省且必须独立 | 验收方若与执行方同体，红线校验即失效 |

> 结论：该编制与「一人一域、写读分离」原则完全自洽，**不增不减**。

---

## 三、阶段机

```text
S0 需求对齐(OR) -> S1 规范冻结(E1-DS) -> S2 四泳道并行 -> S3 集成对齐(OR+E1) -> S4 验收(E6-QA) -> S5 交付(OR)
```

- S2 四条泳道 **完全并行**：A 布局 / B 样式 / C 交互 / D 性能。
- 回退规则：S4 缺陷 -> 退回对应泳道；涉及规范 -> 退回 S1；触碰红线 -> 无条件回退。

| 阶段 | 负责 | 出口条件 |
|---|---|---|
| S0 | OR | 任务分解表确认 |
| S1 | E1-DS | 规范冻结令（OR 签发） |
| S2 | E2/E3/E4/E5 | 各泳道自检通过 |
| S3 | OR + E1-DS | 无冲突、风格统一 |
| S4 | E6-QA | 缺陷清零、红线通过 |
| S5 | OR | 交付清单签署 |

---

## 四、代码落位

| 关注点 | 文件 |
|---|---|
| 全局常量 / 技能路径 | `frontend_optimizer/config.py` |
| 角色档案（7 名） | `frontend_optimizer/agents/roles.py` |
| 专家基类 | `frontend_optimizer/agents/base.py` |
| 阶段机 + 回退规则 | `frontend_optimizer/orchestrator/stages.py` |
| 任务 DAG / 泳道 / 文件边界 | `frontend_optimizer/orchestrator/tasks.py` |
| 运行状态聚合根 | `frontend_optimizer/orchestrator/state.py` |
| 编排主循环 | `frontend_optimizer/orchestrator/engine.py` |
| LLM 接入协议 | `frontend_optimizer/orchestrator/handlers.py` |
| 红线校验 + 哈希基线 | `frontend_optimizer/guardrails/red_line.py` |
| 模型档位（留空） | `frontend_optimizer/model/profiles.py` |
| 档位判定（复杂度） | `frontend_optimizer/model/slots.py` |
| 设计令牌模型 / 导出 | `frontend_optimizer/tokens/schema.py`、`tokens/exporter.py` |
| 技能注册 + 依赖自检 | `frontend_optimizer/skills/registry.py` |
| 阶段提示词（6 个） | `frontend_optimizer/prompts/jinja2/` |
| 离线自检 | `frontend_optimizer/selftest.py` |

---

## 五、模型配置待办（本架构刻意留空）

`model/profiles.py` 中两个槽位均为 `None`，`ModelRouter.resolve()` 会抛
`ModelNotConfiguredError`，避免静默使用错误模型。补齐步骤：

1. 在 `MODEL_PROFILES[ModelSlot.REASONING]` 填高性能模型的 `provider` / `model` / `base_url`；
2. 同理填 `ModelSlot.FAST`（轻量模型）；
3. 如需密钥，走 `conf/` 或环境变量，**不要**写进本包（避免密钥入库）。

档位判定（`model/slots.py`）与方案文档 §6.1 一致：
`needs_decision / cross_scope / deep_reasoning / hard_to_revert` 任一为真 -> 高性能，否则轻量。

---

## 六、技能落位与安装状态

| 技能 | 用途 | 归属 | SKILL.md | 运行时依赖 |
|---|---|---|---|---|
| `frontend-design` | 生产级前端界面设计 | E1/E2/E3/E4 | ✅ | 无 |
| `joy2know-design-tokens` | 设计参考 -> Design Token -> 页面 | E1/E3 | ✅ | python ✅ |
| `headless-cdp-verify` | 真机 headless + CDP 验证 | E5/E6 | ✅ | node ✅、Chrome ✅ |
| `agent-browser` | 批量采集、截图、交互回归 | E6 | ✅ | **已安装 v0.39.0 + Chrome 155 ✅** |

> 本轮已补装缺失的 `agent-browser` CLI（`npm i -g agent-browser`）及其浏览器运行时
> （`agent-browser install`，落在 `C:\Users\86195\.agent-browser\browsers\`）。
> 技能 SKILL.md 根目录可用环境变量 `SKILL_ROOT` 覆盖（默认 `C:\Users\86195\.workbuddy`）。

---

## 七、红线机制

- ⛔ 黑名单：`api/` `service/` `domain/` `engine/` `task/` `knowledge/` `plan/` `prompts/`
  `repository/` `models/` `conf/` `infrastructure/` `flow_config/` `scripts/` `test/`
  `main.py` `pyproject.toml` `uv.lock` `.env` 等。
- ✅ 白名单：`external/customer-service-frontend/**`、`static/**`。
- 三重保障：① 任务单标注允许路径；② 越界改动即驳回；③ S5 用后端文件 SHA256 基线终审。

本项目不是 git 仓库，因此基线用**文件哈希快照**实现（`red_line.save_baseline()`），
快照落在 `docs/frontend-optimizer/workspace/_backend_baseline.json`，不污染后端目录。

---

## 八、运行自检

```powershell
uv run python -m frontend_optimizer.selftest
```

预期输出：编制 7 名 / 技能 4 个就绪 / 模型留空报错 / 红线放行与拦截正确 /
基线自比对无改动 / 令牌导出成功 / 提示词 6 个 / 阶段机 S0->S5 / 红线终审 PASS。
