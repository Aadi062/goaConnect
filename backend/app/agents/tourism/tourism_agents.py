"""
Tourism and heritage agents.
Isolated from security domain — no access to security schemas or audit tables.
"""
from __future__ import annotations

from app.agents.core.base import (
    AgentInput, AgentOutput, AgentRole, BaseAgent, ToolPermission
)
from app.agents.core.manager import register_agent
from app.core.logging import get_logger

logger = get_logger("agent.tourism")


@register_agent
class TravelAssistantAgent(BaseAgent):
    """
    AI travel assistant for Goa.
    Read-only access to places. No security data access.
    """
    role = AgentRole.TRAVEL_ASSISTANT
    permitted_tools = {ToolPermission.READ_PLACES}
    timeout_seconds = 30

    # Static fallback content — used when LLM is not available
    GOA_HIGHLIGHTS = {
        "beaches": ["Calangute", "Baga", "Anjuna", "Palolem", "Vagator", "Morjim"],
        "heritage": ["Basilica of Bom Jesus", "Se Cathedral", "Chapora Fort", "Aguada Fort"],
        "nature": ["Dudhsagar Falls", "Bhagwan Mahaveer Sanctuary", "Salim Ali Bird Sanctuary"],
        "cuisine": ["Fish curry rice", "Prawn balchão", "Bebinca", "Feni", "Sanna"],
        "districts": ["North Goa", "South Goa"],
    }

    async def run(self, task: AgentInput) -> AgentOutput:
        query = task.payload.get("query", "")
        budget = task.payload.get("budget_inr")
        days = task.payload.get("days", 3)
        language = task.payload.get("language", "en")

        # Rules-based recommendation (LLM adapter plugged in Phase E)
        recommendations = []
        query_lower = query.lower()

        if any(w in query_lower for w in ["beach", "sea", "swim", "water"]):
            recommendations.extend(self.GOA_HIGHLIGHTS["beaches"][:3])
        if any(w in query_lower for w in ["heritage", "church", "fort", "history", "culture"]):
            recommendations.extend(self.GOA_HIGHLIGHTS["heritage"][:3])
        if any(w in query_lower for w in ["nature", "waterfall", "wildlife", "trek"]):
            recommendations.extend(self.GOA_HIGHLIGHTS["nature"][:2])
        if not recommendations:
            recommendations = self.GOA_HIGHLIGHTS["beaches"][:2] + self.GOA_HIGHLIGHTS["heritage"][:2]

        response_text = (
            f"For a {days}-day trip to Goa"
            + (f" with ₹{budget:,.0f} budget" if budget else "")
            + f", I recommend: {', '.join(recommendations[:5])}. "
            "Goa offers beautiful beaches, UNESCO heritage churches, vibrant nightlife, "
            "and incredible Konkani cuisine. Best time to visit: October to March."
        )

        return self._build_output(
            task.task_id,
            status="success",
            result={
                "response": response_text,
                "recommendations": recommendations[:5],
                "source_citations": [
                    "Goa Tourism Official Website (https://www.goatourism.gov.in)",
                    "Archaeological Survey of India",
                ],
                "agent_model": "rules_based_v1",
                "llm_available": False,
            },
            confidence=0.7,
            evidence=[{"source": "static_knowledge_base", "query": query[:100]}],
            reasoning=f"Matched query keywords to {len(recommendations)} Goa highlights.",
        )


@register_agent
class ItineraryPlannerAgent(BaseAgent):
    """Plans multi-day Goa itineraries based on budget, group size, and interests."""
    role = AgentRole.ITINERARY_PLANNER
    permitted_tools = {ToolPermission.READ_PLACES}
    timeout_seconds = 30

    async def run(self, task: AgentInput) -> AgentOutput:
        days = task.payload.get("days", 3)
        budget_inr = task.payload.get("budget_inr", 10000)
        group_size = task.payload.get("group_size", 2)
        accessibility = task.payload.get("accessibility_required", False)

        daily_budget = budget_inr / (days * group_size) if days and group_size else 0

        # Simple day-by-day template
        itinerary = []
        templates = [
            {"day": 1, "theme": "North Goa Beaches", "places": ["Calangute Beach", "Baga Beach", "Fort Aguada"], "estimated_cost_inr": 500},
            {"day": 2, "theme": "Heritage & Old Goa", "places": ["Basilica of Bom Jesus", "Sé Cathedral", "Museum of Goa"], "estimated_cost_inr": 300},
            {"day": 3, "theme": "South Goa & Nature", "places": ["Palolem Beach", "Dudhsagar Falls (if accessible)", "Cabo de Rama Fort"], "estimated_cost_inr": 800},
            {"day": 4, "theme": "Markets & Culture", "places": ["Anjuna Flea Market", "Mapusa Market", "Fontainhas Latin Quarter"], "estimated_cost_inr": 400},
            {"day": 5, "theme": "Wildlife & Spice", "places": ["Bhagwan Mahaveer Sanctuary", "Sahakari Spice Farm", "Bondla Wildlife Sanctuary"], "estimated_cost_inr": 600},
        ]

        for i in range(min(days, len(templates))):
            day_plan = templates[i].copy()
            if accessibility:
                day_plan["accessibility_note"] = "Please verify wheelchair/mobility access before visiting"
            itinerary.append(day_plan)

        return self._build_output(
            task.task_id,
            status="success",
            result={
                "days": days,
                "total_budget_inr": budget_inr,
                "group_size": group_size,
                "daily_per_person_budget": round(daily_budget, 2),
                "itinerary": itinerary,
                "tips": [
                    "Book accommodations in advance during peak season (Dec-Jan)",
                    "Carry cash — many local vendors don't accept cards",
                    "Rent a scooter for easy local transport",
                ],
            },
            confidence=0.75,
            evidence=[{"source": "goa_travel_templates_v1"}],
            reasoning=f"Generated {days}-day itinerary for {group_size} person(s) with ₹{budget_inr} budget.",
        )


@register_agent
class HeritageGuideAgent(BaseAgent):
    """Provides detailed information on Goa's UNESCO and state-protected heritage sites."""
    role = AgentRole.HERITAGE_GUIDE
    permitted_tools = {ToolPermission.READ_PLACES}
    timeout_seconds = 20

    HERITAGE_DB = {
        "basilica of bom jesus": {
            "full_name": "Basilica of Bom Jesus",
            "type": "UNESCO World Heritage (Churches and Convents of Goa)",
            "year": 1605,
            "location": "Old Goa",
            "description": "Houses the mortal remains of St. Francis Xavier. Baroque architecture built in 1605.",
            "visiting_hours": "Mon-Sat 9am-6:30pm, Sun 10am-6:30pm",
            "entry": "Free",
            "district": "North Goa",
        },
        "se cathedral": {
            "full_name": "Sé Cathedral",
            "type": "UNESCO World Heritage (Churches and Convents of Goa)",
            "year": 1619,
            "location": "Old Goa",
            "description": "One of the largest churches in Asia, built by the Portuguese.",
            "entry": "Free",
            "district": "North Goa",
        },
        "chapora fort": {
            "full_name": "Chapora Fort",
            "type": "State Protected Monument",
            "year": 1717,
            "location": "Vagator, North Goa",
            "description": "17th century Portuguese fort with panoramic views. Famous from Dil Chahta Hai.",
            "entry": "Free",
            "district": "North Goa",
        },
    }

    async def run(self, task: AgentInput) -> AgentOutput:
        site_query = task.payload.get("site", "").lower().strip()
        info = self.HERITAGE_DB.get(site_query)

        if not info:
            # Fuzzy match
            matches = [k for k in self.HERITAGE_DB if site_query in k or k in site_query]
            if matches:
                info = self.HERITAGE_DB[matches[0]]

        if not info:
            return self._build_output(
                task.task_id,
                status="partial",
                result={"message": f"No heritage info found for '{site_query}'. Available: {list(self.HERITAGE_DB.keys())}"},
                confidence=0.1,
            )

        return self._build_output(
            task.task_id,
            status="success",
            result=info,
            confidence=0.9,
            evidence=[{"source": "goa_heritage_knowledge_base", "site": site_query}],
            reasoning=f"Retrieved heritage info for '{site_query}' from curated knowledge base.",
        )
