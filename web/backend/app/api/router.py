from fastapi import APIRouter

from app.api.routes import (
    assessments,
    auth,
    chat,
    logs,
    reports,
    roles,
    schedules,
    stats,
    users,
    ws,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(stats.router)
api_router.include_router(assessments.router)
api_router.include_router(schedules.router)
api_router.include_router(logs.router)
api_router.include_router(reports.router)
api_router.include_router(chat.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(ws.router)
