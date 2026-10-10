"""数字人 WebSocket 通道自检：/ws/avatar/chat

验证内容：
1. 应用能正常启动（lifespan 生效）
2. 原有 POST /api/chat 未受影响（回归）
3. POST /api/avatar/session 在演示模式下能下发凭证
4. /ws/avatar/chat 能完成一轮：interrupt -> user_ack -> bot_text -> turn_end
5. 未知 type 会返回 error
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 允许以 `python test/check_avatar_ws.py` 方式直接运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.app import app

SENDER = "ws-check-user"


def main() -> int:
    failures: list[str] = []

    with TestClient(app) as client:
        # --- 1. HTTP 回归 ---
        resp = client.post("/api/chat", json={"sender_id": SENDER, "text": "你好"})
        print(f"[1] POST /api/chat -> HTTP {resp.status_code}")
        if resp.status_code != 200:
            failures.append("HTTP 回归失败")
        else:
            texts = [m.get("text") for m in resp.json().get("messages", []) if m.get("text")]
            print(f"    回复: {' / '.join(texts)[:80]}")

        # --- 2. 凭证接口（演示模式下应下发 app_secret）---
        resp = client.post("/api/avatar/session", json={})
        print(f"[2] POST /api/avatar/session -> HTTP {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            has_secret = bool(body.get("app_secret"))
            print(f"    app_id={body.get('app_id')}  app_secret={'已下发' if has_secret else '未下发'}")
            print(f"    gateway_server={body.get('gateway_server')}")
            if not has_secret:
                failures.append("演示模式下 app_secret 未下发（检查 XMOV_ALLOW_SECRET_TO_CLIENT）")
        else:
            failures.append(f"凭证接口异常 HTTP {resp.status_code}")

        # --- 3+4. WebSocket 一轮对话 ---
        print("[3] WS /ws/avatar/chat 一轮对话 ...")
        events: list[dict] = []
        with client.websocket_connect("/ws/avatar/chat") as ws:
            ws.send_text(json.dumps({
                "type": "user_text",
                "sender_id": SENDER,
                "text": "你好，我想问下我的订单",
            }, ensure_ascii=False))

            for _ in range(40):
                data = json.loads(ws.receive_text())
                events.append(data)
                if data.get("type") in ("turn_end", "error"):
                    break

            kinds = [e.get("type") for e in events]
            print(f"    事件序列: {kinds}")

            for required in ("interrupt", "user_ack", "bot_text", "turn_end"):
                if required not in kinds:
                    failures.append(f"WS 未收到 {required}")

            for e in events:
                if e.get("type") == "bot_text":
                    print(f"    bot_text: {(e.get('text') or '')[:60]}")
                if e.get("type") == "error":
                    print(f"    error: {e.get('message')}")
                    failures.append(f"WS 返回错误: {e.get('message')}")

            # --- 4. 未知 type（复用同一连接）---
            ws.send_text(json.dumps({"type": "nope"}, ensure_ascii=False))
            unknown = json.loads(ws.receive_text())
            print(f"[4] 未知 type -> {unknown.get('type')} / {unknown.get('message')}")
            if unknown.get("type") != "error":
                failures.append("未知 type 未返回 error")

    print()
    if failures:
        print("自检结论：❌ 失败")
        for item in failures:
            print("  -", item)
        return 1
    print("自检结论：✅ 通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
