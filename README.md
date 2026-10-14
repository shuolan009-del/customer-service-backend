# 电商小二智能客服系统（customer-service-backend）

电商场景的智能客服系统：基于 FastAPI 的对话引擎按意图三轨分流（任务流程 / 知识库 / 闲聊），
集成魔珐星云数字人，配套 Vue 3 客服工作台前端。

## 系统组成

| 组件 | 目录 | 端口 |
|---|---|---|
| 客服后端（本仓库根目录） | `api/` `engine/` `domain/` … | 18082 |
| 客服前端 | `external/customer-service-frontend/` | 5173 |
| 电商业务后端 | `external/ecommerce-service-backend/` | 18081 |

## 核心特性

- **三轨对话引擎**：`DialogueEngine` 把每轮对话分流到 Task（订单/商品流程）、
  Knowledge（知识库）、ChitChat（闲聊）三条轨道；`TurnPlanner` 规划本轮动作，
  `TurnPlanValidator` 做防幻觉校验。
- **数字人（魔珐星云）**：`infrastructure/xmov/` + WebSocket 通道 `/ws/avatar/chat`；
  未启用（`XMOV_ENABLED=false`）时整条链路静默降级，不影响主对话。
- **业务对象聚焦**：`POST /api/chat` 支持传入订单/商品对象，回复可携带结构化业务信息；
  `GET /api/chat/history?sender_id=` 取历史。
- **MySQL 双库**：`customer_service`（对话状态表 `dialogue_states`）+
  `commerce`（电商演示数据：订单/商品）。

## 技术栈

- 后端：Python ≥ 3.12 · FastAPI · SQLAlchemy · LangChain · Pydantic Settings · uvicorn
- 前端：Vue 3 + Vite（**零第三方依赖**，`dependencies` 仅 `vue`；自建 hash 路由 +
  teal `#0F766E` 设计令牌）
- 数据库：MySQL 8（本机服务或 Docker 均可）

## 快速开始

**方式一（推荐）**：双击根目录 `启动项目.bat`
（自动检查 MySQL → `uv sync` → 启动三个服务 → 打开浏览器）。

**方式二（手动）**：先安装 [uv](https://docs.astral.sh/uv/)，然后：

```bash
# 客服后端（:18082）
uv run uvicorn api.app:app --host 127.0.0.1 --port 18082

# 客服前端（:5173）
cd external/customer-service-frontend
npm install && npm run dev

# 电商业务后端（:18081）
cd external/ecommerce-service-backend
uv run python main.py
```

前端通过 Vite 代理访问后端：`/api`、`/health` → 18082；`/commerce` → 18081；
`/ws` → `ws://127.0.0.1:18082`（数字人聊天通道）。

## 目录结构

后端为扁平包结构（无 `src/` 层级）：

```
api/              FastAPI 路由（chat / avatar / 数字人 WS）
conf/             配置（pydantic-settings；密钥一律走 .env）
domain/ engine/   对话引擎核心（状态机、三轨分流、TurnPlanner、校验器）
knowledge/        知识库轨道
task/ clarify/ chitchat/   任务流程 / 澄清 / 闲聊轨道
infrastructure/   外部集成（数字人 xmov 等）
prompts/          Jinja2 提示词模板
repository/ models/        数据访问与 ORM 模型
external/         客服前端 + 电商业务后端（各自独立可运行）
scripts/          启动与校验脚本
docs/             设计与交付文档
```

## 配置

复制 `.env.example` 为 `.env` 并填写（`.env` 已被 `.gitignore` 排除，不会入库）：

- MySQL 连接信息（两个库）
- `XMOV_*`：魔珐星云数字人（可选；关闭则自动降级）

## 相关文档

`docs/` 目录下有前端重构交付说明、对话流设计、GitHub 上传方法论等文档。
