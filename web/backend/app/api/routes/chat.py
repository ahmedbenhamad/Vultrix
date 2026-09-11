import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permission
from app.core.permissions import Permission
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import (
    ChatSessionDetail,
    ChatSessionOut,
    SendMessageRequest,
)
from app.schemas.common import Message
from app.services import assistant_service

router = APIRouter(prefix="/chat", tags=["assistant"])


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSISTANT_USE)),
) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSISTANT_USE)),
) -> ChatSession:
    s = await db.get(ChatSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return s


@router.post("/message", response_model=ChatSessionDetail)
async def send_message(
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSISTANT_USE)),
) -> ChatSession:
    if not body.content.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty message")

    if body.session_id:
        # db.get applies the selectin eager loader, so .messages is populated
        session = await db.get(ChatSession, body.session_id)
        if session is None or session.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        history = [{"role": m.role, "content": m.content} for m in session.messages]
    else:
        session = ChatSession(user_id=user.id, title=body.content[:60])
        session.messages = []  # initialize in memory to avoid an async lazy-load
        db.add(session)
        await db.flush()
        history = []

    session.messages.append(ChatMessage(role="user", content=body.content))

    # assistant call does blocking network I/O -> off the event loop
    reply = await asyncio.to_thread(assistant_service.generate_reply, body.content, history)
    session.messages.append(ChatMessage(role="assistant", content=reply))
    await db.commit()
    return session


@router.delete("/sessions/{session_id}", response_model=Message)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSISTANT_USE)),
) -> Message:
    s = await db.get(ChatSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await db.delete(s)
    await db.commit()
    return Message(message="Session deleted")
