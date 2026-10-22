"""Pydantic schemas for tourism module."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlaceOut(BaseModel):
    id: str
    name: str
    name_konkani: Optional[str]
    category: str
    description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    district: Optional[str]
    tags: Optional[list]
    accessibility_info: Optional[dict]
    opening_hours: Optional[dict]
    is_verified: bool
    source_citations: Optional[list]
    created_at: datetime
    model_config = {"from_attributes": True}


class PlaceCreate(BaseModel):
    name: str = Field(max_length=500)
    name_konkani: Optional[str] = Field(default=None, max_length=500)
    category: str = Field(max_length=100)
    description: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    district: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[list[str]] = None
    accessibility_info: Optional[dict] = None
    opening_hours: Optional[dict] = None
    source_citations: Optional[list] = None


class ItineraryCreate(BaseModel):
    title: str = Field(max_length=500)
    days: int = Field(ge=1, le=30)
    budget_inr: Optional[float] = Field(default=None, ge=0)
    group_size: int = Field(default=1, ge=1, le=100)
    places: Optional[list[str]] = None  # list of place IDs
    notes: Optional[str] = None
    is_public: bool = False


class ItineraryOut(ItineraryCreate):
    id: str
    user_id: str
    route_geometry: Optional[dict]
    created_at: datetime
    model_config = {"from_attributes": True}


class TravelQuery(BaseModel):
    query: str = Field(max_length=1000)
    budget_inr: Optional[float] = None
    days: Optional[int] = Field(default=None, ge=1, le=30)
    group_size: Optional[int] = Field(default=None, ge=1, le=100)
    accessibility_required: bool = False
    language: str = Field(default="en", max_length=5)
