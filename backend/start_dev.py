"""
GoaConnect Dev Server Startup Script
=====================================
Run: python start_dev.py

- Creates SQLite database tables automatically
- Seeds 8 Goa tourism places
- Creates a default admin user (admin / Admin@GoaConnect1)
- Starts uvicorn on http://localhost:8000
- API docs at http://localhost:8000/docs

NO Docker, NO PostgreSQL required for development.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# ── Set environment before any app imports ──────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./goaConnect_dev.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./goaConnect_dev.db")
os.environ.setdefault("SECRET_KEY", "goaConnect-dev-secret-key-32chars")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "info")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8000")

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base
from app.core.security import hash_password

# Import models so Base.metadata is populated
import app.db.models.user      # noqa
import app.db.models.security  # noqa
import app.db.models.tourism   # noqa

DB_URL = os.environ["DATABASE_URL"]

GOA_PLACES = [
    {"name": "Calangute Beach", "name_konkani": "Kalangut", "category": "beach",
     "description": "Queen of Goan beaches — most popular with tourists, great for swimming and water sports.",
     "district": "North Goa", "latitude": 15.5437, "longitude": 73.7554,
     "tags": ["beach", "swimming", "watersports", "popular"],
     "is_verified": True, "source_citations": ["Goa Tourism Official Website"]},
    {"name": "Basilica of Bom Jesus", "category": "heritage",
     "description": "UNESCO World Heritage site. Houses the mortal remains of St. Francis Xavier. Built in 1605.",
     "district": "North Goa", "latitude": 15.5009, "longitude": 73.9116,
     "tags": ["unesco", "heritage", "church", "history"],
     "is_verified": True, "source_citations": ["UNESCO World Heritage List", "ASI"]},
    {"name": "Dudhsagar Falls", "name_konkani": "Dudhsagar", "category": "nature",
     "description": "One of India's tallest waterfalls at 310m. Inside Bhagwan Mahaveer Sanctuary.",
     "district": "South Goa", "latitude": 15.3143, "longitude": 74.3144,
     "tags": ["waterfall", "nature", "trekking", "wildlife"],
     "is_verified": True, "source_citations": ["Goa Forest Department"]},
    {"name": "Chapora Fort", "category": "heritage",
     "description": "Portuguese fort from 1717 with panoramic views of Vagator and the Arabian Sea.",
     "district": "North Goa", "latitude": 15.6043, "longitude": 73.7414,
     "tags": ["fort", "heritage", "sunset", "photography"],
     "is_verified": True, "source_citations": ["ASI Goa"]},
    {"name": "Palolem Beach", "category": "beach",
     "description": "Crescent-shaped beach in South Goa. Quieter, good for kayaking and yoga retreats.",
     "district": "South Goa", "latitude": 15.0103, "longitude": 74.0231,
     "tags": ["beach", "quiet", "yoga", "kayaking"],
     "is_verified": True, "source_citations": ["Goa Tourism Official Website"]},
    {"name": "Fontainhas Latin Quarter", "category": "heritage",
     "description": "Goa's UNESCO-listed Latin Quarter with Portuguese-era tiled houses and narrow lanes.",
     "district": "North Goa", "latitude": 15.4989, "longitude": 73.8356,
     "tags": ["heritage", "colonial", "culture", "photography"],
     "is_verified": True, "source_citations": ["Goa State Heritage Policy"]},
    {"name": "Anjuna Flea Market", "category": "market",
     "description": "Famous Wednesday flea market. Local handicrafts, spices, clothing, and street food.",
     "district": "North Goa", "latitude": 15.5743, "longitude": 73.7414,
     "tags": ["market", "shopping", "crafts", "culture", "wednesday"],
     "is_verified": True, "source_citations": ["Goa Tourism Official Website"]},
    {"name": "Bhagwan Mahaveer Wildlife Sanctuary", "category": "nature",
     "description": "Largest wildlife sanctuary in Goa (240 sq km). Home to leopards, monkeys, and Dudhsagar Falls.",
     "district": "South Goa", "latitude": 15.3756, "longitude": 74.3179,
     "tags": ["wildlife", "sanctuary", "nature", "trekking"],
     "is_verified": True, "source_citations": ["Goa Forest Department", "WII"]},
]


async def init_db():
    """Create all tables and seed initial data."""
    print("\n[GoaConnect] Initialising database...")
    engine = create_async_engine(DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  [OK] Tables created")

    async with session_factory() as session:
        from sqlalchemy import select, text
        from app.db.models.user import User
        from app.db.models.tourism import Place

        # Seed admin user if not present
        existing_admin = (await session.execute(
            select(User).where(User.username == "admin")
        )).scalar_one_or_none()
        if not existing_admin:
            admin = User(
                id=str(uuid.uuid4()),
                email="admin@goaconnect.local",
                username="admin",
                hashed_password=hash_password("Admin@GoaConnect1"),
                role="admin",
                is_active=True,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(admin)
            print("  [OK] Admin user created  [admin / Admin@GoaConnect1]")
        else:
            print("  [--] Admin user already exists")

        # Seed security analyst user
        existing_analyst = (await session.execute(
            select(User).where(User.username == "analyst")
        )).scalar_one_or_none()
        if not existing_analyst:
            analyst = User(
                id=str(uuid.uuid4()),
                email="analyst@goaconnect.local",
                username="analyst",
                hashed_password=hash_password("Analyst@GoaConnect1"),
                role="security_analyst",
                is_active=True,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(analyst)
            print("  [OK] Analyst user created [analyst / Analyst@GoaConnect1]")

        # Seed guest user
        existing_guest = (await session.execute(
            select(User).where(User.username == "guest")
        )).scalar_one_or_none()
        if not existing_guest:
            guest = User(
                id=str(uuid.uuid4()),
                email="guest@goaconnect.local",
                username="guest",
                hashed_password=hash_password("Guest@GoaConnect1"),
                role="viewer",
                is_active=True,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(guest)
            print("  [OK] Guest user created   [guest / Guest@GoaConnect1]")
        else:
            print("  [--] Guest user already exists")

        # Seed places
        place_count = 0
        for p in GOA_PLACES:
            exists = (await session.execute(
                select(Place).where(Place.name == p["name"])
            )).scalar_one_or_none()
            if not exists:
                import json
                place = Place(
                    id=str(uuid.uuid4()),
                    name=p["name"],
                    name_konkani=p.get("name_konkani"),
                    category=p["category"],
                    description=p.get("description"),
                    latitude=p.get("latitude"),
                    longitude=p.get("longitude"),
                    district=p.get("district"),
                    tags=p.get("tags"),
                    is_verified=p.get("is_verified", False),
                    source_citations=p.get("source_citations"),
                    created_at=datetime.now(timezone.utc),
                )
                session.add(place)
                place_count += 1

        await session.commit()
        if place_count:
            print(f"  [OK] Seeded {place_count} Goa places")
        else:
            print(f"  [--] Places already seeded")

    await engine.dispose()
    print("  [OK] Database ready\n")


if __name__ == "__main__":
    asyncio.run(init_db())

    print("=" * 60)
    print("  GoaConnect Cybersecurity AI Force - Dev Server")
    print("=" * 60)
    print("  URL:      http://localhost:8000")
    print("  API Docs: http://localhost:8000/docs")
    print("  Health:   http://localhost:8000/health")
    print("  Ready:    http://localhost:8000/ready")
    print()
    print("  Users:    admin   / Admin@GoaConnect1      (role: admin)")
    print("            analyst / Analyst@GoaConnect1    (role: security_analyst)")
    print()
    print("  Key endpoints:")
    print("    POST /api/v1/auth/login        - get JWT token")
    print("    GET  /api/v1/security/posture  - security posture")
    print("    GET  /api/v1/security/alerts   - list alerts")
    print("    POST /api/v1/agents/tasks      - run an AI agent task")
    print("    GET  /api/v1/tourism/places    - browse Goa places")
    print("    POST /api/v1/tourism/assistant - AI travel assistant")
    print("=" * 60)
    print("  Press Ctrl+C to stop\n")

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
