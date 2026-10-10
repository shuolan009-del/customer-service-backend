# customer-service-backend 项目长期笔记

> 只记录跨会话有长期价值的事实与约定。日常进展写入同目录 `YYYY-MM-DD.md`。

## 一、项目定位与运行方式

电商小二智能客服系统。三端同仓：

| 路径 | 内容 | 端口 |
|---|---|---|
| 仓库根 `F:\customer-service-backend\` | 客服后端（FastAPI + 对话引擎） | **18082** |
| `external/customer-service-frontend/` | 客服前端（**Vue 3 + Vite**，`App.vue` 约 59KB） | **5173** |
| `external/ecommerce-service-backend/` | 电商平台业务后端 | **18081** |
| `external/docker/` | 数据库等部署脚本 | — |

- **一键启动**：双击根目录 `启动项目.bat`（会检查 MySQL → `uv sync` → 开 3 个窗口起服务 →
  等 18 秒自动开浏览器）。子脚本在 `scripts/run-*.bat`。
  ⚠️ `.bat` 一律用 **Python 生成**（`encoding='gbk'` + 手动 `\r\n`），不要用编辑器直接写。
- **后端运行必须用 `uv run`**：裸用系统 Python 会 `ModuleNotFoundError: No module named 'fastapi'`
  （依赖在 uv 管理的 venv 里）。启动：`uv run uvicorn api.app:app --host 127.0.0.1 --port 18082`，
  或 `uv run python main.py`。入口 `main.py` → `api.app:app`。
- **电商后端**启动：`cd external/ecommerce-service-backend && uv run python main.py`（→ 18081），
  它有自己的 `.venv`。连 `commerce` 库。
- **MySQL 是本机 Windows 服务**（`mysqld.exe`，非 Docker；Docker Desktop 未运行），端口 3306，
  root/123456。两个库均已初始化：
  `customer_service`（表 `dialogue_states`）、`commerce`（8 张表，含演示订单与商品数据）。
  初始化 SQL 在 `external/docker/windows/initdb/`（`001_init_customer_service.sql` +
  `002_init_commerce.sql`），`docker/` 下另有 docker-compose 版本。
- 前端 Vite 代理（`vite.config.js`）：`/api` 与 `/health` → `127.0.0.1:18082`；
  `/commerce` → `127.0.0.1:18081`（且 `rewrite` 去掉 `/commerce` 前缀）；
  `/ws` → `ws://127.0.0.1:18082`（**必须 `ws: true`**，数字人聊天通道用）。
- 后端顶层是**扁平包结构**（`api/` `conf/` `domain/` `infrastructure/` `service/` `task/`
  `knowledge/` `plan/` `clarify/` `chitchat/` `engine/` `repository/` `models/`），
  **没有 `atguigu/` 前缀**。网上教程（含 B 站/网盘资料）里的 `atguigu/config/config.py`、
  `atguigu/api/routers.py` 这类路径在**本项目里要相应去掉前缀**。

## 二、对话引擎现状

- `POST /api/chat` 入参仅 `text` 或 `object`（订单/商品聚焦对象），出参 `messages[]` 纯文本；
  `GET /api/chat/history`。**没有任何音频/视频/形象字段**。
- 链路：`DialogueService` → `DialogueEngine`，三轨分流：**Task 流程 / Knowledge 知识库 / ChitChat 闲聊**，
  经 `TurnPlanner` 规划 + `TurnPlanValidator` 防幻觉校验。
- 项目内**无 TTS/ASR/数字人相关实现**。

## 三、已知的现状缺口（2026-10-07 核实）

- 前端 `App.vue` 已有 `playTts(botMsg)`：`POST /api/chat/tts` → 拿 audio blob → `new Audio(url).play()`。
  **但后端没有 `/api/chat/tts` 这个接口** → 该朗读功能实际会失败。属于「前端已写、后端未实现」的空档。
- 数字人（魔珐星云）已在后端落地（见下），但**尚未集成进 `App.vue`**。
  后端数字人配置与代码：`infrastructure/xmov/`、`api/routers/avatar_router.py`、
  `api/schemas_xmov.py`、`conf/config.py` 的 `xmov_*` 字段、`.env` 的 `XMOV_*`。
  配置未启用（`XMOV_ENABLED=false`）时整条链路静默降级，接口返回 503，不影响 `/api/chat`。

## 四、踩坑记录（可复用）

- **FastAPI 0.136 的 `include_router` 会展开为 `_IncludedRouter` 惰性对象**，
  遍历 `app.routes` 拿不到 `path`（`getattr` 为空）。正确枚举方式：**`app.openapi()["paths"]`**。
- Bash 工具在 Windows 下 `/tmp/xxx.py` 会被解析成 `F:\tmp\`，heredoc 写的脚本会找不到；
  改用 Write 工具落盘到项目目录再执行。
- 本机 PowerShell 工具 stdout 常回传为空 → 需取输出时用 `Out-File` 落盘再读文件。
- **本项目不是 git 仓库**（根目录无 `.git`）→ **没有 diff 基线**。核查「文件有没有被改」
  只能用 **mtime**：`find . -type f -printf "%TY-%Tm-%Td %TH:%TM  %p\n"` +
  逐文件内容比对。核心业务目录（`service/` `domain/` `engine/` `task/` `knowledge/`
  `plan/` `chitchat/` `clarify/` `repository/` `models/` `prompts/`）的原始 mtime
  停留在 **2026-09-07 及更早**，可作为「未被改动」的参照基线。
