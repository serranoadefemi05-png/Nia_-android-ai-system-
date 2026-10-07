"""NIA API v1 router assembly."""
from fastapi import APIRouter
from .auth import router as auth_router
from .assistant import router as assistant_router
from .tasks import router as tasks_router
from .memory import router as memory_router
from .tools import router as tools_router
from .web import router as web_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(assistant_router)
v1_router.include_router(tasks_router)
v1_router.include_router(memory_router)
v1_router.include_router(tools_router)
v1_router.include_router(web_router)
