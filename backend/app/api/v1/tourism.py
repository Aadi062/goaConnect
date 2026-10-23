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
from app.core.logging import get_logger

router = APIRouter(prefix="/tourism", tags=["tourism"])
logger = get_logger("api.tourism")


@router.get("/places", response_model=list[PlaceOut])
async def search_places(
    q: Optional[str] = Query(default=None, max_length=200),
    category: Optional[str] = Query(default=None, max_length=100),
    district: Optional[str] = Query(default=None, max_length=100),
    semantic: bool = Query(default=False, description="Use semantic/AI search instead of exact match"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Search places. When `semantic=true` and a query is provided, uses
    vector similarity (Ollama embeddings) or keyword ranking as fallback.
    """
    query = select(Place)
    if category:
        query = query.where(Place.category == category)
    if district:
        query = query.where(Place.district == district)

    # If semantic search requested with a query term, rank by relevance
    if q and semantic:
        # Fetch candidates first (category/district filtered)
        result = await db.execute(query.limit(200))
        candidates = result.scalars().all()
        if candidates:
            from app.services.search import semantic_search_places
            # Convert ORM objects to dicts for the search service
            candidate_dicts = [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description or "",
                    "category": p.category or "",
                    "district": p.district or "",
                }
                for p in candidates
            ]
            ranked = await semantic_search_places(q, candidate_dicts, top_k=page_size)
            ranked_ids = [r["place"]["id"] for r in ranked]
            # Preserve ranking order
            place_map = {str(p.id): p for p in candidates}
            ordered = [place_map[pid] for pid in ranked_ids if pid in place_map]
            # Apply pagination
            offset = (page - 1) * page_size
            return ordered[offset: offset + page_size]
        return []

    # Standard SQL search
    if q:
        query = query.where(Place.name.ilike(f"%{q}%"))
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
    AI travel assistant — calls TravelAssistantAgent with Ollama LLM (if available)
    and falls back to curated rules-based recommendations.
    """
    await log_event(
        db, "tourism.assistant.query", "travel_assistant", "success",
        user_id=current_user.id,
        detail={"query_length": len(query.query), "language": query.language},
    )

    try:
        from app.agents.core.manager import ManagerAgent
        from app.agents.core.base import AgentInput

        # Import tourism agents to ensure they are registered
        import app.agents.tourism.tourism_agents  # noqa: F401

        manager = ManagerAgent()
        task = AgentInput(
            task_id=str(uuid.uuid4()),
            task_type="travel_query",
            payload={
                "query": query.query,
                "budget_inr": query.budget_inr,
                "days": query.days or 3,
                "language": query.language or "en",
            },
            requester_id=str(current_user.id),
        )
        output = await manager.run(task)
        return {
            "query": query.query,
            "response": output.result.get("response", ""),
            "source_citations": output.result.get("source_citations", []),
            "agent_model": output.result.get("agent_model", "unknown"),
            "llm_available": output.result.get("llm_available", False),
            "confidence": output.confidence,
            "agent_status": output.status,
        }
    except Exception as exc:
        logger.error("travel_assistant_error", exc=str(exc))
        # Hard fallback — never return a 500 to the user
        return {
            "query": query.query,
            "response": (
                "Welcome to Goa! Top picks: Calangute Beach (North Goa), "
                "Basilica of Bom Jesus (UNESCO, Old Goa), and Palolem Beach (South Goa). "
                "Best time to visit: October–March. Local tip: try fish curry rice! 🐟"
            ),
            "source_citations": ["Goa Tourism Official Website"],
            "agent_model": "emergency_fallback",
            "llm_available": False,
            "confidence": 0.5,
            "agent_status": "fallback",
        }
