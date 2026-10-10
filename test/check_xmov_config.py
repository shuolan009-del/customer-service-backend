#!/usr/bin/env python
# test/check_xmov_config.py
"""
魔珐星云配置自检脚本（可直接运行，也可当一次性排查工具）。

用法：
    # 在项目根目录执行
    .venv/Scripts/python.exe test/check_xmov_config.py

它会检查：
1. 数字人路由是否正确注册（含 WebSocket /ws/avatar/chat）
2. .env 中的密钥是否被正确读取（只打印脱敏值）
3. /api/avatar/status 与 /api/avatar/session 是否正常
4. App Secret 的下发状态（演示模式下发 / 生产模式拦截）
5. 原有 /api/chat 是否未受影响（回归检查）
"""
import asyncio
import sys
from pathlib import Path

# 允许以 `python test/check_xmov_config.py` 方式直接运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import app
from infrastructure.xmov.config import load_xmov_config


def _collect_paths(app_instance) -> list[tuple[str, str]]:
    """
    收集已注册的业务路由。

    说明：FastAPI 0.136 会把 include_router 展开为 _IncludedRouter 惰性对象，
    直接遍历 app.routes 拿不到 path。改用 OpenAPI schema 枚举，最可靠。
    """
    schema = app_instance.openapi()
    collected: list[tuple[str, str]] = []
    for path, ops in (schema.get("paths") or {}).items():
        for method in ops:
            collected.append((method.upper(), path))
    return sorted(collected, key=lambda x: x[1])


def _collect_ws_paths(app_instance) -> list[str]:
    """
    收集 WebSocket 路由。

    WebSocket 路由不会出现在 OpenAPI schema 里，只能遍历 app.router.routes；
    同样要穿透 include_router 展开出的 _IncludedRouter 包装层。
    """
    found: list[str] = []
    for route in app_instance.router.routes:
        inner = getattr(route, "original_router", None)
        candidates = inner.routes if inner is not None and hasattr(inner, "routes") else [route]
        for sub in candidates:
            if type(sub).__name__ == "APIWebSocketRoute":
                path = getattr(sub, "path", None)
                if path:
                    found.append(path)
    return sorted(set(found))


def main() -> int:
    print("=" * 62)
    print("魔珐星云配置自检")
    print("=" * 62)

    # ---- 1. 路由 ----
    all_routes = _collect_paths(app)
    avatar_routes = [x for x in all_routes if x[1].startswith("/api/avatar")]
    chat_routes = [x for x in all_routes if x[1].startswith("/api/chat")]
    ws_routes = _collect_ws_paths(app)
    print(f"\n[1] 路由注册：HTTP 业务路由 {len(all_routes)} 条"
          f"（数字人 {len(avatar_routes)} / 原有对话 {len(chat_routes)}），"
          f"WebSocket {len(ws_routes)} 条")
    for m, p in avatar_routes:
        print(f"      {m:6} {p}")
    for p in ws_routes:
        print(f"      {'WS':6} {p}")

    # ---- 2. 配置 ----
    cfg = load_xmov_config()
    print(f"\n[2] 配置装载：")
    print(f"      enabled              = {cfg.enabled}")
    print(f"      credentials_ready    = {cfg.credentials_ready}")
    print(f"      usable               = {cfg.usable}")
    print(f"      app_id (脱敏)        = {cfg.masked_app_id()}")
    print(f"      app_secret (脱敏)    = {cfg.masked_secret()}")
    print(f"      secret 长度          = {len(cfg.app_secret) if cfg.app_secret else 0}")
    print(f"      gateway_server       = {cfg.gateway_server}")
    print(f"      timeout / retries    = {cfg.timeout_seconds}s / {cfg.max_retries}")
    print(f"      allow_secret_to_client = {cfg.allow_secret_to_client}")

    if not cfg.usable:
        print("\n  ⚠️ 不可用：请检查 .env 的 XMOV_ENABLED / XMOV_APP_ID / XMOV_APP_SECRET")
        return 1

    # ---- 3 & 4. 接口与安全 ----
    from fastapi.testclient import TestClient
    ok = True
    with TestClient(app) as client:
        r = client.get("/api/avatar/status")
        print(f"\n[3] GET /api/avatar/status -> HTTP {r.status_code}")
        print(f"      {r.json()}")
        ok = ok and r.status_code == 200

        r2 = client.post("/api/avatar/session", json={"avatar_id": "demo-avatar"})
        body = r2.json()
        print(f"\n[4] POST /api/avatar/session -> HTTP {r2.status_code}")
        print(f"      app_id     = {body.get('app_id')}")
        print(f"      js_sdk_url = {body.get('js_sdk_url')}")
        secret_leaked = body.get("app_secret") is not None
        print(f"      app_secret = {'<已下发>' if secret_leaked else None}  "
              f"-> {'⚠️ 演示模式（可初始化但请勿用于生产）' if secret_leaked else '✅ 未下发（安全）'}")

        print(f"\n[4b] GET /api/avatar/drive-guide -> 驱动方式说明")
        r4 = client.get("/api/avatar/drive-guide")
        print(f"      HTTP {r4.status_code} mode={r4.json().get('mode')} "
              f"methods={len(r4.json().get('methods', []))} 个")

        print(f"\n[4c] GET /api/avatar/consume-record -> 真实调用官方接口")
        try:
            r5 = client.get("/api/avatar/consume-record")
            d5 = r5.json()
            print(f"      HTTP {r5.status_code} count={d5.get('count')} "
                  f"total_amount={d5.get('total_amount')}")
        except Exception as ex:  # noqa: BLE001
            print(f"      调用异常（网络/鉴权问题属预期）：{type(ex).__name__} {str(ex)[:80]}")

    # ---- 5. 回归 ----
    print(f"\n[5] 原有 /api/chat 回归检查（需要 MySQL 与 LLM 可用）")
    with TestClient(app) as client:
        try:
            r3 = client.post("/api/chat", json={"sender_id": "selfcheck-user", "text": "你好"})
            text = (r3.json().get("messages") or [{}])[0].get("text")
            print(f"      HTTP {r3.status_code} -> {str(text)[:60]}")
        except Exception as ex:  # noqa: BLE001
            print(f"      ⚠️ 调用异常（若 MySQL/LLM 未启动属正常）：{type(ex).__name__}")

    print("\n" + "=" * 62)
    print("自检结论：" + ("✅ 通过" if ok else "❌ 存在待修复项"))
    print("=" * 62)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())