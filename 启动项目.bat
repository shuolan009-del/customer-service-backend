@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo    电商小二智能客服  -  一键启动
echo ============================================================
echo.

rem ---- 清掉可能失效的代理环境变量（若你之后开启代理软件，请删除这四行）----
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=

echo [1/4] 检查 MySQL (127.0.0.1:3306) ...
powershell -NoProfile -Command "if ((Test-NetConnection 127.0.0.1 -Port 3306 -InformationLevel Quiet -WarningAction SilentlyContinue)) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo.
    echo    [错误] MySQL 未运行，服务无法启动。
    echo           请先启动 MySQL（本机为 Windows 服务 mysqld）后重试。
    echo.
    pause
    exit /b 1
)
echo    OK - MySQL 已就绪
echo.

echo [2/4] 同步客服后端依赖 ...
if not exist ".venv" (
    echo    首次运行，正在安装依赖（可能需要 1-2 分钟）...
    call uv sync
    if errorlevel 1 (
        echo    [错误] uv sync 失败，请检查网络或 uv 是否已安装。
        pause
        exit /b 1
    )
) else (
    echo    OK - 依赖目录已存在，跳过
)
echo.

echo [3/4] 启动三个服务（会打开 3 个新窗口，请不要关闭它们）...
start "客服后端 18082" "%~dp0scripts\run-backend-avatar.bat"
start "电商后端 18081" "%~dp0scripts\run-backend-commerce.bat"
start "客服前端 5173"  "%~dp0scripts\run-frontend.bat"
echo    OK - 已发出启动指令
echo.

echo [4/4] 等待服务就绪（约 18 秒）...
timeout /t 18 /nobreak >nul
start "" "http://127.0.0.1:5173/"

echo.
echo ============================================================
echo    使用说明
echo ============================================================
echo    1. 浏览器已打开 http://127.0.0.1:5173/
echo    2. 左侧数字人：点「连接数字人」，等资源下载到 100%%
echo    3. 中间输入框提问，数字人会自动朗读客服回复
echo    4. 用完点「销毁数字人」释放连接（避免并发限制）
echo.
echo    停止服务：直接关闭那 3 个服务窗口即可
echo    详细验收清单见 docs\试玩演示指南.md
echo ============================================================
echo.
pause
