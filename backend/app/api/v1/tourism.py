"""Tourism API routes: places, itineraries, AI travel assistant."""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user, require_analyst
from app.db.models.user import User
from app.db.models.tourism import Place, Itinerary
from app.schemas.tourism import PlaceCreate, PlaceOut, ItineraryCreate, ItineraryOut, TravelQuery
from app.services.security.audit import log_event

router = APIRouter(prefix="/tourism", tags=["tourism"])


@router.get("/places", response_model=list[PlaceOut])
async def search_places(
    q: Optional[str] = Query(default=None, max_length=200),
    category: Optional[str] = Query(default=None, max_length=100),
    district: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Place)
    if q:
        query = query.where(Place.name.ilike(f"%{q}%"))
    if category:
        query = query.where(Place.category == category)
    if district:
        query = query.where(Place.district == district)
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Place.name).offset(offset).limit(page_size)
    )
    return result.scalars().all()


@router.get("/places/{place_id}", response_model=PlaceOut)
async def get_place(place_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.post("/places", response_model=PlaceOut, status_code=status.HTTP_201_CREATED)
async def create_place(
    data: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    place = Place(id=str(uuid.uuid4()), **data.model_dump())
    db.add(place)
    await db.flush()
    await log_event(
        db, "tourism.place.created", "create_place", "success",
        user_id=current_user.id, resource=f"place:{place.id}",
        detail={"name": place.name, "category": place.category},
    )
    return place


@router.get("/itineraries", response_model=list[ItineraryOut])
async def list_itineraries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Itinerary).where(
            (Itinerary.user_id == current_user.id) | (Itinerary.is_public == True)
        ).order_by(Itinerary.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.post("/itineraries", response_model=ItineraryOut, status_code=status.HTTP_201_CREATED)
async def create_itinerary(
    data: ItineraryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    itin = Itinerary(id=str(uuid.uuid4()), user_id=current_user.id, **data.model_dump())
    db.add(itin)
    await db.flush()
    return itin


@router.post("/assistant")
async def travel_assistant(
    query: TravelQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI travel assistant endpoint. Currently returns a structured placeholder.
    Replace with agent orchestrator call once AI layer is configured.
    """
    await log_event(
        db, "tourism.assistant.query", "travel_assistant", "success",
        user_id=current_user.id,
        detail={"query_length": len(query.query), "language": query.language},
    )
    # Placeholder response — agent layer wired in Phase D
    return {
        "query": query.query,
        "response": "The GoaConnect AI Travel Assistant is initializing. Configure Ollama with qwen2.5:7b and set OLLAMA_BASE_URL to enable full AI responses.",
        "suggestions": [
            "Calangute Beach — North Goa's most popular beach",
            "Basilica of Bom Jesus — UNESCO World Heritage Site, Old Goa",
            "Dudhsagar Falls — stunning tiered waterfall in the Bhagwan Mahaveer Sanctuary",
        ],
        "source_citations": [],
        "agent_status": "placeholder",
    }
