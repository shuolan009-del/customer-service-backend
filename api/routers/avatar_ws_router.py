# api/routers/avatar_ws_router.py

"""数字人聊天 WebSocket 接口（魔珐星云联动用）。

协议（纯 JSON 文本帧，不传二进制音频帧）:

客户端 -> 服务端:
    {"type": "user_text", "sender_id": "u1", "text": "...", "message_id": "(可选)"}

服务端 -> 客户端:
    {"type": "user_ack",  "message_id": "..."}
    {"type": "bot_text",  "message_id": "...", "index": 0, "text": "...", "object": {...}}
    {"type": "turn_end",  "message_id": "..."}
    {"type": "interrupt"}                                   # 要求前端立刻打断数字人播报
    {"type": "error",     "message": "..."}

设计说明:
- 数字人开口由**前端**把 bot_text 交给魔珐星云 SDK 的 speak() 完成；
  服务端既不做 TTS，也不推 PCM 音频（transcript 模式）。
- 业务逻辑与 POST /api/chat 完全一致，复用同一套 DialogueService / DialogueEngine，
  因此 Task / Knowledge / ChitChat 三条轨道行为不变。
- 引擎较重（要读 flow yml），按连接构建一次后复用；数据库 session 每轮新建（与 HTTP 一致）。
- 新消息到达时取消上一轮仍在进行的生成，并推 interrupt 让前端停播，
  避免「旧回复和新回复一起往前端发」。
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.routers.dependencies import get_engine
from domain.messages import BotMessage, FocusedObject, MessageType, UserMessage
from engine.dialogue_engine import DialogueEngine
from infrastructure import database
from repository.dialogue_state_repository import DialogueStateRepository
from service.dialogue_service import DialogueService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/avatar/chat")
async def avatar_chat_ws(ws: WebSocket) -> None:
    """数字人聊天通道：收用户文本，推机器人文本。"""
    await ws.accept()
    engine: DialogueEngine = await get_engine()
    current_turn: asyncio.Task | None = None

    async def cancel_current(reason: str) -> None:
        """取消上一轮尚未完成的生成。

        cancel() 只是「发出取消请求」，必须 await 真正等它停下来，
        否则旧任务可能还在往连接里写数据，和新一轮的回复混在一起。
        """
        nonlocal current_turn
        if current_turn is None or current_turn.done():
            current_turn = None
            return
        current_turn.cancel()
        try:
            await current_turn
        except (asyncio.CancelledError, Exception):
            pass
        finally:
            current_turn = None
        logger.info("avatar ws turn cancelled: %s", reason)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(ws, {"type": "error", "message": "invalid json"})
                continue

            msg_type = payload.get("type")
            if msg_type == "user_text":
                # 新消息到达 → 先打断上一轮，再启动新一轮
                await cancel_current("new user_text arrived")
                await _send_json(ws, {"type": "interrupt"})
                current_turn = asyncio.create_task(_run_turn(ws, engine, payload))
            else:
                await _send_json(ws, {"type": "error", "message": f"unknown type: {msg_type}"})
    except WebSocketDisconnect:
        logger.info("avatar ws client disconnected")
    except Exception:
        logger.exception("avatar ws handler crashed")
    finally:
        await cancel_current("ws closing")


async def _run_turn(ws: WebSocket, engine: DialogueEngine, payload: dict[str, Any]) -> None:
    """处理一次用户输入：调对话引擎拿回复，再把回复文本逐条推给前端。"""
    sender_id = (payload.get("sender_id") or "").strip()
    if not sender_id:
        await _send_json(ws, {"type": "error", "message": "missing sender_id"})
        return

    text = (payload.get("text") or "").strip()
    if not text:
        await _send_json(ws, {"type": "error", "message": "empty text"})
        return

    message_id = payload.get("message_id") or str(uuid.uuid4())
    user_message = UserMessage(
        sender_id=sender_id,
        message_id=message_id,
        type=MessageType.TEXT,
        text=text,
    )

    await _send_json(ws, {"type": "user_ack", "message_id": message_id})

    # 复用现有对话引擎，session 生命周期与 HTTP 链路一致
    try:
        async with database.async_session() as session:
            repository = DialogueStateRepository(session=session)
            service = DialogueService(
                dialogue_state_repository=repository,
                dialogue_engine=engine,
            )
            result = await service.process_message(user_message)
        messages: list[BotMessage] = result.messages
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("avatar dialogue turn failed")
        await _send_json(ws, {"type": "error", "message": f"dialogue failed: {exc}"})
        return

    for index, bot_msg in enumerate(messages):
        await _send_json(
            ws,
            {
                "type": "bot_text",
                "message_id": message_id,
                "index": index,
                "text": bot_msg.text,
                "object": _focused_object_to_dict(bot_msg.object),
            },
        )

    await _send_json(ws, {"type": "turn_end", "message_id": message_id})


def _focused_object_to_dict(obj: FocusedObject | None) -> dict | None:
    """领域对象 → 前端可用的 dict（mode='json' 保证枚举/日期可序列化）。"""
    if obj is None:
        return None
    return obj.model_dump(mode="json")


async def _send_json(ws: WebSocket, data: dict) -> None:
    """发送失败不抛异常：客户端可能已经断开，这属于正常情况。"""
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        logger.debug("avatar ws send failed (client likely closed)", exc_info=True)
