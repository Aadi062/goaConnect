"""
GoaConnect Cybersecurity AI Force — FastAPI Application Entry Point
"""
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.v1 import auth, security, tourism, health, agents

configure_logging()
logger = structlog.get_logger("goaconnect.main")
settings = get_settings()

# Rate limiter (uses Redis when configured, falls back to memory)
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", service=settings.app_name, environment=settings.environment)
    yield
    logger.info("shutdown", service=settings.app_name)


app = FastAPI(
    title="GoaConnect Cybersecurity AI Force",
    description=(
        "Multi-agent cybersecurity platform + Goa tourism and heritage AI. "
        "Phase A-H implementation — see /docs for interactive API explorer."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS — restricted to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    structlog.contextvars.unbind_contextvars("request_id")
    return response


# Global exception handler — never leak internal stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", exc_type=type(exc).__name__, path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again or contact support."},
    )


# Routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(security.router, prefix="/api/v1")
app.include_router(tourism.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")

# Static frontend — served last so API routes take priority
_static_dir = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(_static_dir / "index.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Return index.html for any unknown path so the SPA router works."""
    file = _static_dir / full_path
    if file.is_file():
        return FileResponse(file)
    return FileResponse(_static_dir / "index.html")


app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
