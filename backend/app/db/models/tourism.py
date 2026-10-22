"""Tourism place and itinerary models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Place(Base):
    """A point of interest in Goa — beach, heritage site, restaurant, etc."""
    __tablename__ = "places"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    name_konkani: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    accessibility_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    opening_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Itinerary(Base):
    """User-planned trip itinerary."""
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    budget_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    group_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    places: Mapped[list | None] = mapped_column(JSON, nullable=True)
    route_geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
