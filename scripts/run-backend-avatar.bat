@echo off
cd /d "%~dp0.."
title 客服后端 18082
echo ============================================================
echo  客服后端（含数字人接口与 WebSocket）
echo  地址: http://127.0.0.1:18082
echo  文档: http://127.0.0.1:18082/docs
echo ============================================================
echo.
uv run uvicorn api.app:app --host 127.0.0.1 --port 18082
echo.
echo [服务已退出] 按任意键关闭本窗口 ...
pause >nul
