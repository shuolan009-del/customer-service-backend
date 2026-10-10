# itwwy/api/app.py

"""
定义fastapi实例

"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routers.chat_router import router
from api.routers.avatar_router import router as avatar_router
from api.routers.avatar_ws_router import router as avatar_ws_router
from infrastructure.database import init_db_engine, close_db_engine
from infrastructure.http_client import init_http_client, close_http_client
from infrastructure.xmov import xmov_client


# 装饰器 是 Python特有的语法 在不改变函数内部 代码的情况下 额外 增加新的功能
# 汽车 什么都不懂  拿去店里 额外 车顶 装个机关枪  封闭开放 （不主张 你去修改代码 但是 愿意让函数 有更多的功能）
@asynccontextmanager
async def lifespan(app: FastAPI):

    # 1. 应用启动
    print("启动服务器...")
    init_db_engine()  # ← 执行这里，创建数据库连接池
    init_http_client()
    # 2. 进入 yield
    yield  # ← FastAPI 开始接收请求


    # 3. 应用关闭（Ctrl+C 或部署平台停止）
    await close_db_engine()  # ← 执行这里，关闭连接池
    await close_http_client()
    await xmov_client.aclose()  # ← 关闭数字人客户端连接池
    print("服务器已关闭")

# 创建应用
app = FastAPI(description="电商小二智能客服应用", lifespan=lifespan)



# 路由分发
app.include_router(router)
app.include_router(avatar_router)  # 数字人（魔珐星云），未启用时各接口返回 503，不影响原有接口
app.include_router(avatar_ws_router)  # 数字人聊天 WebSocket（/ws/avatar/chat），复用同一套对话引擎

# 静态目录：数字人演示页需要以 http://localhost 形式访问（SDK 要求）
_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")




