@echo off
cd /d "%~dp0..\external\customer-service-frontend"
title 客服前端 5173
echo ============================================================
echo  客服前端（Vue 3 + Vite，含左侧数字人面板）
echo  地址: http://127.0.0.1:5173/
echo ============================================================
echo.
if not exist "node_modules" (
    echo 首次运行，正在安装前端依赖 ...
    call npm install
    if errorlevel 1 (
        echo [错误] npm install 失败，请检查网络。
        pause
        exit /b 1
    )
)
call npm run dev
echo.
echo [服务已退出] 按任意键关闭本窗口 ...
pause >nul
