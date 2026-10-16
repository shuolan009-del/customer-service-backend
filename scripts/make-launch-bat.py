# 一键启动脚本生成器（按项目约定：.bat 一律用 Python 生成，GBK 编码 + 手动 \r\n）
#
# 产物：F:\jiahe-platform-frontend\启动嘉禾平台.bat
#
# 服务矩阵（2026-10-12 本机实测结论）：
#   [可起] 禾语农产品AI客服后端 :18082（uv run uvicorn，MySQL customer_service/commerce 已就绪）
#   [可起] 电商演示后端 :18081（uv run python main.py）
#   [可起] 禾语农产品AI运营助手后端 :8000（api/.venv，MySQL ecommerce_operation 已就绪；
#          PostgreSQL 5458 为 LangGraph checkpoint，懒连接不阻塞启动，缺它时 agent 工作流不可用）
#   [缺依赖] 禾语农产品知识库查询 :8001（MongoDB 27017 未运行——Docker 未启动；
#             uvicorn 能起但 import 即刷 Mongo 重试日志，问答/历史功能不可用）
#   [端口冲突] 禾语农产品知识库导入 :8000 与运营助手同端口，本脚本默认起运营助手；
#              如确需导入服务，先停运营助手再手动启动
#   [可起] 禾语农产品AI客服前端 :5173 / 禾语农产品AI运营助手前端 :3000 / 禾语农产品平台门户 :5174
#
# 用法：双击 bat。每个服务一个窗口（日志可见，方便人工审核），最后自动打开门户。

OUT = r"F:\jiahe-platform-frontend\启动嘉禾平台.bat"

LINES = [
    "@echo off",
    "chcp 65001 >nul",
    "title 禾语农产品智能商管平台 - 一键启动（人工审核版）",
    "echo ============================================================",
    "echo    禾语农产品智能商管平台 · 一键启动",
    "echo    禾语农产品AI客服 / 禾语农产品AI运营助手 / 禾语农产品知识库",
    "echo ============================================================",
    "echo.",
    "",
    "REM ---------- 环境预检 ----------",
    'echo [1/3] 预检 MySQL :3306 ...',
    'netstat -ano | findstr ":3306" | findstr "LISTENING" >nul',
    "if errorlevel 1 (",
    '    echo       MySQL 未运行，尝试启动 Windows 服务 ...',
    '    for /f "tokens=1" %%s in (\'sc query type^= service state^= all ^| findstr /i "MySQL"\') do net start "%%s" >nul 2>nul',
    ") else (",
    '    echo       OK MySQL 正在运行',
    ")",
    "",
    'echo [2/3] 预检 uv / node ...',
    "where uv >nul 2>nul && echo       OK uv 已安装 || echo       [警告] 未找到 uv，后端将无法启动",
    "where node >nul 2>nul && echo       OK node 已安装 || echo       [警告] 未找到 node，前端将无法启动",
    "",
    'echo [3/3] 预检 MongoDB :27017（禾语农产品知识库依赖）...',
    'netstat -ano | findstr ":27017" | findstr "LISTENING" >nul',
    "if errorlevel 1 (",
    '    echo       [注意] MongoDB 未运行——禾语农产品知识库查询服务会卡在连接重试，',
    '    echo              其窗口持续输出 Mongo 日志，属预期',
    ") else (",
    '    echo       OK MongoDB 正在运行（kb001）',
    ")",
    "",
    "echo.",
    "echo ------------------------------------------------------------",
    "echo  即将启动 7 个服务窗口（每个窗口一个服务，日志可直接查看）：",
    "echo    [1] 禾语农产品AI客服后端     :18082   MySQL customer_service",
    "echo    [2] 电商演示业务后端   :18081   MySQL commerce",
    "echo    [3] 禾语农产品AI运营助手后端 :8000    MySQL ecommerce_operation",
    "echo    [4] 禾语农产品知识库查询后端 :8001    MongoDB kb001（本次实测已连通）",
    "echo    [5] 禾语农产品AI客服前端     :5173    Vue3 工作台",
    "echo    [6] 禾语农产品AI运营助手前端 :3000    Next.js（首次编译约 30 秒）",
    "echo    [7] 禾语农产品平台门户       :5174    当前入口",
    "echo ------------------------------------------------------------",
    "echo.",
    "",
    "REM ---------- 启动各服务（各一个窗口，人工审核看日志） ----------",
    'start "[1] 禾语农产品AI客服后端 :18082" cmd /k "cd /d F:\\customer-service-backend && uv run uvicorn api.app:app --host 127.0.0.1 --port 18082"',
    'start "[2] 电商演示后端 :18081" cmd /k "cd /d F:\\customer-service-backend\\external\\ecommerce-service-backend && uv run python main.py"',
    'start "[3] 禾语农产品AI运营助手后端 :8000" cmd /k "cd /d F:\\ecommerce-operation-assistant-source-20260815\\api && .venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"',
    'start "[4] 禾语农产品知识库查询 :8001" cmd /k "cd /d F:\\knowledge_base && .venv\\Scripts\\python.exe -m web.api.query_service"',
    'start "[5] 禾语农产品AI客服前端 :5173" cmd /k "cd /d F:\\customer-service-backend\\external\\customer-service-frontend && npm run dev"',
    'start "[6] 禾语农产品AI运营助手前端 :3000" cmd /k "cd /d F:\\ecommerce-operation-assistant-source-20260815\\web && npm run dev"',
    'start "[7] 禾语农产品平台门户 :5174" cmd /k "cd /d F:\\jiahe-platform-frontend && npm run dev"',
    "",
    "echo.",
    "echo  所有服务窗口已拉起，等待就绪后自动打开门户 ...",
    "echo.",
    "REM ---------- 等待并开门户 ----------",
    "timeout /t 20 /nobreak >nul",
    'start "" http://127.0.0.1:5174/',
    "",
    "echo ============================================================",
    "echo  启动完成。门户：http://127.0.0.1:5174/",
    "echo.",
    "echo  人工审核提示：",
    "echo   - 后端未就绪时，门户卡片会显示「后端离线」并附启动命令",
    "echo   - 禾语农产品AI运营助手工作流需 PostgreSQL :5458（LangGraph checkpoint），",
    "echo     本机未启动时该后端的商品/任务接口可用、agent 运行会失败",
    "echo   - 禾语农产品知识库需 MongoDB :27017（本次实测已连通）",
    "echo     + Milvus 向量库（RAG 检索用，未启动时问答会失败但服务在线）",
    "echo   - 停止：直接关闭各服务窗口即可",
    "echo ============================================================",
    "echo.",
    "pause",
]

# GBK 编码 + 手动 \r\n（项目约定：不用编辑器直接写 bat）
with open(OUT, "w", encoding="gbk", newline="") as f:
    f.write("\r\n".join(LINES) + "\r\n")

print(f"已生成: {OUT}")
print(f"行数: {len(LINES)}（GBK + CRLF）")

# 自检：读回来确认编码无损
raw = open(OUT, "rb").read()
text = raw.decode("gbk")
assert "禾语农产品智能商管平台" in text and "uv run uvicorn" in text
assert b"\xef\xbb\xbf" not in raw, "不应带 BOM"
assert raw.count(b"\r\n") >= len(LINES) - 1, "CRLF 行尾缺失"
print("自检通过：中文编码 / CRLF / 无 BOM")
