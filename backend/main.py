"""
NIA Backend — FastAPI Application Entry Point
Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import v1_router
from app.core.config import settings

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("nia")


# ── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NIA backend starting — version %s", settings.APP_VERSION)
    yield
    logger.info("NIA backend shutting down.")


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NIA Backend API",
    description=(
        "NIA — Your Android, with an AI brain.\n\n"
        "AI orchestration, tool registry, memory, web agent, and Arc integration."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────
# Tighten allowed_origins in production to your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://nia.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate Limiting (simple in-process; use Redis in production) ─────────────
_rate_limit_store: dict[str, list[float]] = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    client_ip = request.client.host if request.client else "unknown"
    window = 60.0
    now = time.time()
    hits = _rate_limit_store.setdefault(client_ip, [])
    hits[:] = [t for t in hits if now - t < window]
    if len(hits) >= settings.RATE_LIMIT_PER_MINUTE:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please slow down."},
        )
    hits.append(now)
    return await call_next(request)


# ── Request Logging ────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info("%s %s → %d (%.1f ms)", request.method, request.url.path, response.status_code, elapsed)
    return response


# ── Routes ─────────────────────────────────────────────────────────────────

app.include_router(v1_router)


@app.get("/api/v1/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "service": "nia-backend",
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "NIA Backend API", "docs": "/docs"}
