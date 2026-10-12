# customer-service-backend 项目长期笔记

> 只记录跨会话有长期价值的事实与约定。日常进展写入同目录 `YYYY-MM-DD.md`。

## 一、项目定位与运行方式

电商小二智能客服系统。三端同仓：

| 路径 | 内容 | 端口 |
|---|---|---|
| 仓库根 `F:\customer-service-backend\` | 客服后端（FastAPI + 对话引擎） | **18082** |
| `external/customer-service-frontend/` | 客服前端（**Vue 3 + Vite**） | **5173** |
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

## 三、前端架构（2026-10-11 重构后）

- **前端不是单文件了**。`src/` 现在是分层结构：
  - `App.vue` 仅 ~25 行：`AppShell` + 按 hash 路由渲染视图 + 全局 `ToastHost` / `ConfirmDialog`。
  - `router/`：**零依赖自建 hash 路由**（`useRoute.js` 监听 `hashchange`/`popstate`；`routes.js` 定义
    `#/`(工作台) `#/sessions` `#/dashboard` `#/settings`，未知路径回落 `#/`）。**没有 vue-router**。
  - `styles/design-tokens.css` + `styles/base.css`：**全局唯一令牌来源**（`main.js` 引入）。
    单一主色 **teal `#0F766E`**（旧京东红 `#E1251B` 已作为主色退场，仅危险色用 `#B42318`）。
    ink 中性阶 50–900、radius 真阶梯（含 `--radius-full:9999px`）、shadow 4 档、`--shell-h:56px`。
    **旧名别名层已于 2026-10-11 第 2 轮删除**（前提：全仓旧令牌引用清零）。
    新增 `docs/../scripts/check-frontend-tokens.py` 可静态核对「引用了但未定义」的变量
    （这类变量在浏览器里静默失效，最难发现）。
  - `components/ui/`：自研原语（AppButton/AppCard/AppBadge/AppInput/AppField/AppTextarea/Avatar/
    Icon/Skeleton/EmptyState/SegmentedControl/InlineAlert/DetailDrawer/ToastHost/ConfirmDialog/
    KpiCard/ChartPlaceholder/StatTable/Spinner）。图标走 `assets/icons.js` 的 SVG 注册表 + `Icon.vue`。
  - `components/layout/`：`AppShell.vue`（56px 顶栏 + 主导航 + 联网 pill + skip-link）、`PageHeader.vue`。
  - `components/workbench/`（2026-10-11 第 2 轮新增）：`AvatarPanel` / `MessageStream` /
    `MessageBubble` / `ObjectCard` / `ObjectSidebar` / `Composer`。
  - `views/`：`WorkbenchView.vue`（**第 2 轮已重写为 266 行编排层**，原 2509 行单体已拆散）、
    `SessionsView.vue`、`DashboardView.vue`、`SettingsView.vue`。
  - `config/service.js`：客服 `小宝/金牌客服` 与用户身份的头像配置（工作台与会话记录共用）。
  - `composables/`：useChat / useAvatar / useAvatarWs / useSidebar / useClipboard / useConfirm /
    useToast / useNetwork（**全部已接线**，第 2 轮前有 931 行是零引用的孤儿代码）。
    `utils/`：format / status / id / error（`toFriendlyMessage`）/ **timeline**（本地消息时间轴）。
- **保持零第三方依赖**：`package.json` 的 `dependencies` 仍只有 `vue`。不要引入 vue-router / UI 库 / Tailwind。
- Canvas 粒子背景已**整体移除**（改纯中性底 `--surface-raised`）。
- 新增页面数据源：`#/sessions` 用真实 `GET /api/chat/history`（按 `session_id` 归并为会话）；
  `#/settings` 读 `/api/avatar/status` 与 `/api/avatar/consume-record`；`#/dashboard` **只能用静态示例数据**
  （后端无聚合接口，UI 已标注「示例数据」）。
- **尚未完成**：`static/avatar_demo.html` 尚未统一到同一套令牌；768–1023 区间的抽屉化布局未做；
  会话记录页仍是「会话维度」而非「日期维度」；数据看板仍为静态数据。

### 3.1 工作台对话流（2026-10-11 第 2 轮，用户明确要求）

- **对话不再按 Turn 分块**。用户原话：「用户和客服之间的对话不要分成一块一块的，要做成整个整体」。
  旧实现每个 Turn 一张带边框卡片 + `Turn N` 徽章 + 每组重复头像姓名，已全部去掉；
  改为**连续 IM 流**：头像与姓名只在「同一发送者的首条」出现，同组气泡折角收紧、间距 4px，
  跨组 16px。`Turn N` 徽章改为 `?debug=1` 才显示的内部状态浮层。
- **消息区按自然日分组**：吸顶胶囊 `今天` / `昨天` / `10月9日 周四` / `更早的记录`。
  分组逻辑在 `useChat.js` 的 `messageGroups`（原 `turns` 已删除）。
- ⚠️ **时间来源是前端自建，不是后端**（详见 `docs/前端优化交付说明-对话流重构.md` 第四节）：
  `HistoryMessage` 只有 `session_id/role/text/object`，**零时间字段**；后端时间戳只到 Session 级
  （`domain/state.py` 的 `started_at/last_activity_at/closed_at`）且不外传；`session_id` 是
  `str(uuid4())` 反推不出日期。故 `utils/timeline.js` 用
  `角色+类型+对象id+文本+同内容第几次出现` 的**指纹**把本地时间戳写进
  `localStorage['cs-ts:v1:<sender_id>']`。已实测**刷新后仍能命中**。
  代价：跨浏览器/清缓存后退化为「更早的记录」；跨天说完全相同的话会命中较新的时间。
- 数字人栏、对话栏、业务对象栏**共用同一高度来源** `calc(100vh - var(--shell-h))`
  （旧实现 `.avatar-panel` 少减了 `--shell-h`，导致左栏高 56px、三栏错位）。

## 四、对话引擎现状

- `POST /api/chat` 入参仅 `text` 或 `object`（订单/商品聚焦对象），出参 `messages[]` 纯文本；
  `GET /api/chat/history?sender_id=`。**没有任何音频/视频/形象字段**。
- 链路：`DialogueService` → `DialogueEngine`，三轨分流：**Task 流程 / Knowledge 知识库 / ChitChat 闲聊**，
  经 `TurnPlanner` 规划 + `TurnPlanValidator` 防幻觉校验。
- **TTS 不走后端音频**：前端 `playTts` 直接驱动数字人 SDK 播报；**后端从未有 `/api/chat/tts`**
  （早期笔记误记为「前端写了、后端没实现」，实际前端调用的是数字人 SDK）。

## 五、数字人（魔珐星云）

- 后端：`infrastructure/xmov/`、`api/routers/avatar_router.py`（`/api/avatar/status|ping|session|drive-guide|consume-record`）、
  `api/routers/avatar_ws_router.py`（**`WS /ws/avatar/chat`**，非 `/ws`）、`api/schemas_xmov.py`、
  `conf/config.py` 的 `xmov_*`、`.env` 的 `XMOV_*`。
- 未启用（`XMOV_ENABLED=false`）时整条链路静默降级，接口返 503，不影响 `/api/chat`。
- 前端集成在工作台视图内（连接/销毁、进度、WS 通道、插话打断）。
- 演示页：`static/avatar_demo.html`，经后端挂载在 `http://127.0.0.1:18082/static/avatar_demo.html`。

## 六、踩坑记录（可复用）

- **FastAPI 0.136 的 `include_router` 会展开为 `_IncludedRouter` 惰性对象**，
  遍历 `app.routes` 拿不到 `path`（`getattr` 为空）。正确枚举方式：**`app.openapi()["paths"]`**。
- Bash 工具在 Windows 下 `/tmp/xxx.py` 会被解析成 `F:\tmp\`，heredoc 写的脚本会找不到；
  改用 Write 工具落盘到项目目录再执行。
- 本机 PowerShell 工具 stdout 常回传为空 → 需取输出时用 `Out-File` 落盘再读文件。
- **`vite build` 在本会话会被沙箱拦在清空 `dist` 这一步**（报 `[safe-delete] … Some operations were aborted`）。
  规避：先 `rm -rf dist` 再 `npm run build`（Bash 的 rm 可通过）；或构建到全新目录
  `npx vite build --outDir .verify-dist --emptyOutDir false`。
- **Chrome headless 有最小窗口宽度（实测约 504px）**：`--window-size=414` 得到的
  `window.innerWidth` 是 504，截图却按 414 裁 → 会**误判为横向溢出**。
  验证窄屏必须用 CDP `Emulation.setDeviceMetricsOverride`（见下），不要用 `--window-size`。
- **CDP 真机校验配方（已验证可用）**：`chrome.exe --headless=new --disable-gpu
  --remote-debugging-port=9333 --user-data-dir=<临时目录> <URL>`（profile 用 `mktemp -d`，别放项目里）；
  Node 22 内置 `WebSocket` 直连 `/json/list` 的 `webSocketDebuggerUrl`，
  发 `Page.enable`/`Runtime.enable`/`Emulation.setDeviceMetricsOverride`，再
  `Runtime.evaluate` 测 `docScrollWidth` 与溢出元素、`Page.captureScreenshot` 取图。
- **三端在本机都没常驻运行**：本次排查时 18082 与 18081 **均未启动**，前端会因此显示
  「无法连接后台服务 / 返回内容异常」。验证完整链路前需先按 `启动项目.bat` 起后端。
- ✅ **本项目就是 git 仓库**（根目录有 `.git`；早期笔记误记为「非 git 仓库」，2026-10-11 已证伪）。
  工作树可用 `git status --porcelain` / `git diff --stat` 直接判定改动范围，回退用 `git revert`。
  关键提交：`a0da9ed`「前端优化前基线」→ `aa8135c` / `cfea63c` / `2fa223c` / `a4167e1`（前端优化流水线各轮）。
- 若需要字节级台账，仍可用 SHA-256（`git hash-object` 或 PowerShell `Get-FileHash`）双保险。
- **前端 `src/` 下多数目录在根仓库里「未被追踪」**（`components/` `views/` `composables/`
  `router/` `styles/` `utils/` `config/` 全是 `??`）。只有 `src/App.vue`、`index.html`、
  `package.json` 等少数文件被追踪。**所以改前端前要知道：没有 git 安全网**，
  旧单体工作台唯一备份是 `git show HEAD:external/customer-service-frontend/src/App.vue`
  （2682 行，含 Turn 卡片实现）。
- **本轮新增两个可复用脚本**（都在仓库根 `scripts/`）：
  - `check-frontend-tokens.py`：核对 CSS 变量「被引用但未定义」（本轮借此发现
    `SessionsView.vue` 里 `var(--text-primary)` 是错的，浏览器静默失效）。
  - `verify-workbench.mjs`：CDP 真机验证工作台，21 项 PASS/FAIL 自动断言 + 截图到
    `docs/verify/`。用法 `node scripts/verify-workbench.mjs http://127.0.0.1:5173`。
    含 Vue `v-model` 赋值技巧（必须用 `HTMLInputElement.prototype.value` 的 setter
    + `dispatchEvent(new Event('input',{bubbles:true}))`，直接赋值不触发响应式）。
- **MySQL 表结构**：`customer_service.dialogue_states` 的列是 `sender_id`(PK) + **`state_json`**
  （不是 `state`）。连接：`"/f/Program Files/MySQL/MySQL Server 8.0/bin/mysql.exe" -uroot -p123456`。
  做验证时用独立 sender（如 `uverify<时间>`）再删掉，别污染 `u1001` 的演示历史。
