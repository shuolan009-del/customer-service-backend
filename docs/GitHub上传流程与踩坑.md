# GitHub 上传流程与踩坑总结

> 2026-10-12 实测总结。覆盖三个项目（customer-service-backend / ecommerce-operation-assistant /
> knowledge-base）上传 GitHub 的完整方法、本环境网络限制下的替代推送方案、以及全部踩坑记录。

---

## 一、结论速查（本环境网络事实）

| 通道 | 状态 | 证据 |
|---|---|---|
| SSH（`git@github.com:22`） | ❌ 不可用 | 22 端口出站被墙，连接超时 |
| `github.com:443`（git push/fetch/clone） | ❌ 被代理阻断 | `CONNECT tunnel failed, response 502`；`schannel: server closed abruptly` |
| `api.github.com`（REST API） | ⚠️ 可用但不稳 | GET 稳定；POST 可用但单请求 ~6s（代理延迟），Python urllib 经代理易挂死 120s+ |

**推论：**
1. 沙箱内可以**用 API 建仓库**，但**不能 git push**——内容推送要么到用户本机执行，要么走 Git Data API（见第三节）。
2. 代理策略**随时间抖动**（同一天内 17:00 API 建仓库成功、19:18 全部 502、19:40 恢复），失败时先重试再下结论。
3. Python 的 `urllib` 经本代理不稳；**curl 子进程稳定**（但慢）。需要程序化调 API 时用 curl。

---

## 二、标准上传流程（新项目 Checklist）

### 第 1 步：安全前置（推公开仓库前必做）
```bash
# ① .gitignore 是否覆盖敏感项
cat .gitignore
# ② 已跟踪文件里有没有 .env / 密钥（gitignore 对已入索引的文件无效！）
git ls-files | grep -iE "(^|/)\.env$|secret|\.pem$|id_rsa"
# ③ 全仓扫描硬编码密钥（变量名/掩码占位符除外）
#    正则：sk-[A-Za-z0-9]{20} | AKIA[0-9A-Z]{16} | password\s*[:=] | api[_-]?key | BEGIN PRIVATE KEY
# ④ 大文件检查：GitHub 单文件硬限制 100MB，超了 push 直接被拒
find . -type f -size +50M -not -path "*/node_modules/*" -not -path "*/.venv/*"
```
> 本次实战收获：`.codex/config.toml`（AI 工具配置）里藏着**真实 API Key**且不在 .gitignore 里；
> `docker/minio-build/minio` 是 **105MB 二进制**。两者都是推之前必须排掉的雷。

### 第 2 步：本地提交
```bash
git add -A
git diff --cached --name-only | grep -iE "\.env$|secret"   # 再确认一次
git commit -m "feat: ..."
```

### 第 3 步：建仓库（GitHub API）
```bash
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: application/vnd.github+json' \
  --data-binary '{"name":"<仓库名>","private":false}' \
  https://api.github.com/user/repos
```
> ⚠️ JSON body **不要带中文**（经代理会被截断，报 `400 Problems parsing JSON`），description 用英文或留空。

### 第 4 步：推送
- **首选（用户本机）**：`git push -u origin main`（本机直连 GitHub，不受沙箱代理限制）。
- **沙箱内备选**：Git Data API 推送法（下节）。

### 第 5 步：清理与验证
```bash
git remote set-url origin https://github.com/<user>/<repo>.git   # 去掉 URL 里的 token
git remote -v                                                    # 确认无令牌残留
```
推完若 token 在对话/日志里明文出现过，提醒用户去 https://github.com/settings/tokens 轮换。

---

## 三、本环境专用：Git Data API 推送法（绕开被墙的 github.com:443）

### 原理
git 对象模型 = blob（文件内容）+ tree（目录）+ commit（提交）+ ref（分支指针）。
只走 `api.github.com` 逐个上传对象，等价于一次完整 push，且保留全部提交历史
（信息、作者、提交者、时间都能字节级还原——实测远端 commit SHA 与本地一致）。

### 用法
```bash
GH_TOKEN=<pat> python scripts/gh_api_push.py <仓库名> <本地仓库路径> [分支名]
# 例：
GH_TOKEN=ghp_xxx python scripts/gh_api_push.py knowledge-base /f/knowledge_base main
```

### 实现要点（都踩过坑）
1. **HTTP 层用 curl 子进程**，不要用 urllib（urllib 经本代理会 read timeout 挂死）。
   curl 也要 `-m 60` 防挂，失败退避重试。
2. **大 body 写临时文件**再 `--data-binary @文件`——Windows 命令行长度上限 ~32KB，
   263 个文件的 tree JSON 会超限。
3. **blob 上传 8 路并发**（`ThreadPoolExecutor`）。内容寻址、幂等，可安全并行；
   代理 6s/请求下，110 文件从 11 分钟降到 ~2 分钟。
4. **空仓库先初始化**：全新仓库直接建 blob 会 `409 Git Repository is empty`。
   先用 Contents API `PUT /contents/README.md` 放占位 README，再把自己的提交
   **force** 到分支上（占位提交变成不可达对象，不出现在分支历史里）。
5. **建 ref 时 422 "Reference already exists" 是预期内**（占位 README 已建 main），
   直接 fallback 到 `PATCH /git/refs/heads/main {"force": true}`，不要重试。
6. **推完本地同步**：若远端 SHA 与本地一致（通常如此），只需补一个 remote-tracking ref：
   ```bash
   git update-ref refs/remotes/origin/main <远端sha>
   ```
   否则 `git reset --hard <远端sha>` 对齐（工作树干净时安全）。

---

## 四、踩坑记录（按严重程度排序）

| # | 坑 | 现象 | 解法 |
|---|---|---|---|
| 1 | **真实密钥进了初始提交** | `knowledge_base/.codex/config.toml` 含 Anthropic API Key，`.codex/` 不在 .gitignore | `git rm -r --cached .codex/` + `.gitignore` 加 `.codex/` + `git commit --amend`（仓库无 remote 时 amend 即彻底净化历史）；**并轮换该 Key** |
| 2 | **105MB 二进制超 GitHub 单文件 100MB 硬限制** | minio server 二进制被跟踪，push 必被拒 | `git rm --cached` + .gitignore；Dockerfile 改为 `RUN wget/curl` 下载而非 COPY 本地二进制 |
| 3 | **.gitignore 对已 staged 文件无效** | `12.py/11.py/text.py`（误操作嵌套目录）之前已被 `git add`，加 .gitignore 后仍进了提交 | `git rm -r --cached <路径>` 从索引移除，再 amend |
| 4 | 空仓库建 blob 409 | `Git Repository is empty` | 占位 README 初始化 + force 更新 ref（见上节） |
| 5 | 代理读写不对称 + 延迟爆炸 | ls-remote 能通但 push 502；API 单请求 6s；urllib 挂死 | 读走 API 验证；写走 curl 并发；或交接用户本机推 |
| 6 | 令牌权限不足 | `github_pat_` 细粒度令牌 `POST /user/repos` 403 | 细粒度需同时开：Repository access=**All repositories**、Account permissions=**Create repositories**、Repository permissions=**Contents: Read and write**。**最省事：经典 token 只勾 `repo` 一框** |
| 7 | 中文 JSON 被代理截断 | `400 Problems parsing JSON` | API body 一律 ASCII |
| 8 | 分支名不统一 | 老项目是 `master`，新仓库默认 `main` | 推前 `git branch -m master main` 统一 |
| 9 | `.workbuddy/`、`.idea/` 混入 | 本地 agent 记忆/IDE 配置被 `git add -A` 收进去 | .gitignore 补 `.workbuddy/`、`.idea/`、`*.log`、`celerybeat-schedule*` |

---

## 五、三个项目的仓库结构：为什么选「三个独立仓库」

| 仓库 | 项目 | 技术栈 |
|---|---|---|
| `customer-service-backend` | 智能客服 | FastAPI + Vue3 + 数字人 WS + MySQL |
| `ecommerce-operation-assistant` | 商品运营 | LangGraph 多 Agent + FastAPI + Next.js + Alembic |
| `knowledge-base` | 智能智库 | LangGraph 双管线 + Milvus + BGE-M3（需 GPU） |

**理由：**
1. 三项目**不共享代码**，各有独立的依赖、运行环境（GPU/Docker）、迭代节奏——monorepo 的唯一好处（统一版本/共享构建）完全用不上；
2. 独立仓库才能各自设置公开/私有、各自的 Issue/CI/协作者；
3. `customer-service-backend` 已作为独立仓库推送，再合并需改写历史重推，得不偿失。

**不选单仓库多目录的理由**：CI 会全量触发、issue/PR 互相干扰、clone 体积叠加、
权限无法细分（想只开源其中一个都做不到）。

---

## 六、安全清单（每次推公开仓库过一遍）

- [ ] `.env` / `*.secret` / `*.pem` / `id_rsa` 未被跟踪（`git ls-files` 核实，不信 .gitignore）
- [ ] 全仓无硬编码真实密钥（正则扫描；测试文件里的假值如 `sk-test` 可接受）
- [ ] 无 >50MB 文件
- [ ] 无 AI 工具配置目录入库（`.codex/`、`.claude/`、`.agents/`——常含真实 API Key）
- [ ] 无 IDE/本地记忆目录（`.idea/`、`.workbuddy/`）
- [ ] remote URL 无令牌残留；对话中出现过的 token 已提醒用户轮换

---

## 七、复用资产

| 文件 | 用途 |
|---|---|
| `scripts/gh_api_push.py` | Git Data API 并发推送脚本（本环境 git push 被墙时的主力） |
| `scripts/check-frontend-tokens.py` | 前端 CSS 令牌静态核对（本项目既有） |
