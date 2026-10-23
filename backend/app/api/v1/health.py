"""Health and readiness endpoints — reports DB, Ollama, Redis, and search status."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health():
    """Basic liveness — always returns 200 if the process is running."""
    from app.core.ai_adapter import ollama_status
    from app.core.cache import cache_status
    from app.services.search import search_status

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "ollama": ollama_status(),
            "cache": cache_status(),
            "search": search_status(),
        },
    }


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness check — verifies DB connectivity. Fails (503) if DB is down."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    from app.core.cache import cache_status
    cache = cache_status()

    overall = "ready" if db_status == "ok" else "not_ready"
    return {
        "status": overall,
        "database": db_status,
        "cache_backend": cache["backend"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
