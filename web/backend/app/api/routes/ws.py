"""WebSocket live feed for a single assessment: status/phase/progress/log/finding."""

import asyncio
import contextlib

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core import events
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.permissions import Permission
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models.assessment import Assessment
from app.models.log import LogEntry
from app.models.user import User

router = APIRouter(tags=["ws"])


async def _authenticate(websocket: WebSocket, db) -> User | None:
    token = websocket.cookies.get(settings.ACCESS_COOKIE_NAME) or websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            return None
        user = await db.get(User, int(payload.get("sub", "")))
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
    return user if (user and user.is_active) else None


async def _snapshot(db, assessment_id: int) -> dict | None:
    a = await db.get(Assessment, assessment_id)
    if a is None:
        return None
    logs = (
        await db.execute(
            select(LogEntry)
            .where(LogEntry.assessment_id == assessment_id)
            .order_by(LogEntry.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return {
        "type": "snapshot",
        "assessment": {
            "id": a.id, "status": a.status, "phase": a.phase, "progress": a.progress,
            "findings_count": a.findings_count, "error": a.error,
        },
        "logs": [
            {"level": lg.level, "source": lg.source, "message": lg.message,
             "created_at": lg.created_at.isoformat() if lg.created_at else None}
            for lg in reversed(logs)
        ],
    }


@router.websocket("/ws/assessments/{assessment_id}")
async def assessment_feed(websocket: WebSocket, assessment_id: int) -> None:
    async with AsyncSessionLocal() as db:
        user = await _authenticate(websocket, db)
        if user is None or not user.has_permission(Permission.ASSESSMENT_READ):
            await websocket.close(code=4401)  # unauthorized
            return
        a = await db.get(Assessment, assessment_id)
        if a is None or (a.created_by_id != user.id and not user.has_permission(Permission.ASSESSMENT_READ_ALL)):
            await websocket.close(code=4404)  # not found / not owned
            return
        snapshot = await _snapshot(db, assessment_id)

    await websocket.accept()
    if snapshot:
        await websocket.send_json(snapshot)

    queue = events.subscribe(assessment_id)

    async def _sender() -> None:
        # Push events to the client; emit a keep-alive ping when idle.
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25)
            except TimeoutError:
                event = {"type": "ping"}
            await websocket.send_json(event)

    async def _receiver() -> None:
        # Drain inbound frames so Starlette observes the client's disconnect
        # promptly. Without a reader, the sender keeps writing to a dead socket,
        # which floods asyncio's "socket.send() raised exception." warning on
        # Windows during high-log-rate scans.
        try:
            while True:
                await websocket.receive()
        except WebSocketDisconnect:
            pass

    sender = asyncio.create_task(_sender())
    receiver = asyncio.create_task(_receiver())
    try:
        # Whichever side finishes first — a client disconnect (receiver) or a
        # failed send (sender) — tears the connection down.
        await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in (sender, receiver):
            task.cancel()
        for task in (sender, receiver):
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await task
        events.unsubscribe(assessment_id, queue)
        with contextlib.suppress(Exception):
            await websocket.close()
