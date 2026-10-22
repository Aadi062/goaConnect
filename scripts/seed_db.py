#!/usr/bin/env python3
"""
GoaConnect database seeder — creates schemas and populates initial Goa tourism data.
Run: python scripts/seed_db.py
Requires DATABASE_URL_SYNC in environment.
"""
import os
import sys
import uuid
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://goauser:goapassword@localhost:5432/goaconnect"
)

GOA_PLACES = [
    {"name": "Calangute Beach", "name_konkani": "Kalangut", "category": "beach",
     "description": "Queen of Goan beaches — most popular with tourists.", "district": "North Goa",
     "latitude": 15.5437, "longitude": 73.7554, "tags": ["beach", "swimming", "watersports"],
     "is_verified": True, "source_citations": ["Goa Tourism Official Website"]},
    {"name": "Basilica of Bom Jesus", "category": "heritage",
     "description": "UNESCO World Heritage site. Houses remains of St. Francis Xavier. Built 1605.",
     "district": "North Goa", "latitude": 15.5009, "longitude": 73.9116,
     "tags": ["unesco", "heritage", "church", "religion"],
     "is_verified": True, "source_citations": ["UNESCO World Heritage List", "ASI"]},
    {"name": "Dudhsagar Falls", "name_konkani": "Dudhsagar", "category": "nature",
     "description": "One of India's tallest waterfalls at 310m. Located in Bhagwan Mahaveer Sanctuary.",
     "district": "South Goa", "latitude": 15.3143, "longitude": 74.3144,
     "tags": ["waterfall", "nature", "trekking", "wildlife"],
     "is_verified": True, "source_citations": ["Goa Forest Department"]},
    {"name": "Chapora Fort", "category": "heritage",
     "description": "Portuguese fort from 1717 with panoramic ocean views. Popular filming location.",
     "district": "North Goa", "latitude": 15.6043, "longitude": 73.7414,
     "tags": ["fort", "heritage", "sunset", "photography"],
     "is_verified": True, "source_citations": ["ASI Goa"]},
    {"name": "Palolem Beach", "category": "beach",
     "description": "Crescent-shaped beach in South Goa — relatively quieter than North Goa.",
     "district": "South Goa", "latitude": 15.0103, "longitude": 74.0231,
     "tags": ["beach", "quiet", "yoga", "kayaking"],
     "is_verified": True, "source_citations": ["Goa Tourism Official Website"]},
    {"name": "Fontainhas Latin Quarter", "category": "heritage",
     "description": "Goa's Latin Quarter with Portuguese-era houses, cobblestone lanes, and feni bars.",
     "district": "North Goa", "latitude": 15.4989, "longitude": 73.8356,
     "tags": ["heritage", "colonial", "culture", "art"],
     "is_verified": True, "source_citations": ["Goa State Heritage Policy"]},
    {"name": "Anjuna Flea Market", "category": "market",
     "description": "Famous Wednesday flea market with local crafts, clothing, and spices.",
     "district": "North Goa", "latitude": 15.5743, "longitude": 73.7414,
     "tags": ["market", "shopping", "crafts", "culture"],
     "is_verified": True, "source_citations": ["Goa Tourism Official Website"]},
    {"name": "Bhagwan Mahaveer Wildlife Sanctuary", "category": "nature",
     "description": "Largest wildlife sanctuary in Goa covering 240 sq km. Home to the Dudhsagar Falls.",
     "district": "South Goa", "latitude": 15.3756, "longitude": 74.3179,
     "tags": ["wildlife", "nature", "sanctuary", "trekking"],
     "is_verified": True, "source_citations": ["Goa Forest Department", "Wildlife Institute of India"]},
]


def seed():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(engine)

    with Session() as session:
        # Ensure schemas exist
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS tourism"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS security"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit"))
            conn.commit()

        # Insert places
        for p in GOA_PLACES:
            existing = session.execute(
                text("SELECT id FROM tourism.places WHERE name = :name"),
                {"name": p["name"]}
            ).fetchone()
            if not existing:
                session.execute(
                    text("""
                        INSERT INTO tourism.places
                        (id, name, name_konkani, category, description, latitude, longitude,
                         district, tags, is_verified, source_citations, created_at)
                        VALUES (:id, :name, :name_konkani, :category, :description, :latitude, :longitude,
                                :district, :tags::json, :is_verified, :source_citations::json, :created_at)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "name": p["name"],
                        "name_konkani": p.get("name_konkani"),
                        "category": p["category"],
                        "description": p.get("description"),
                        "latitude": p.get("latitude"),
                        "longitude": p.get("longitude"),
                        "district": p.get("district"),
                        "tags": str(p.get("tags", [])).replace("'", '"'),
                        "is_verified": p.get("is_verified", False),
                        "source_citations": str(p.get("source_citations", [])).replace("'", '"'),
                        "created_at": datetime.now(timezone.utc),
                    }
                )
                print(f"  + Added: {p['name']}")
            else:
                print(f"  ~ Exists: {p['name']}")

        session.commit()
    print("\n✓ Seed complete.")


if __name__ == "__main__":
    seed()
