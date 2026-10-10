@echo off
cd /d "%~dp0..\external\ecommerce-service-backend"
title 电商后端 18081
echo ============================================================
echo  电商业务后端（订单 / 商品 / 物流 / 退款）
echo  地址: http://127.0.0.1:18081
echo  文档: http://127.0.0.1:18081/docs
echo ============================================================
echo.
uv run python main.py
echo.
echo [服务已退出] 按任意键关闭本窗口 ...
pause >nul
