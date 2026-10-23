"""
Tourism and heritage agents.
Isolated from security domain — no access to security schemas or audit tables.
LLM enhancement via ai_adapter (Ollama) with automatic rules-based fallback.
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
    Uses Ollama (qwen2.5) when available; falls back to curated rules.
    """
    role = AgentRole.TRAVEL_ASSISTANT
    permitted_tools = {ToolPermission.READ_PLACES}
    timeout_seconds = 30

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

        llm_used = False
        agent_model = "rules_based_v1"
        response_text = ""

        # ---- Attempt LLM enhancement ----------------------------------------
        try:
            from app.core import ai_adapter
            system_prompt = (
                "You are GoaConnect AI, a helpful Goa tourism assistant. "
                "Provide accurate, concise travel advice about Goa, India. "
                "Always mention beaches, heritage sites, or local cuisine as appropriate. "
                "Keep responses under 150 words. Be friendly and enthusiastic about Goa."
            )
            user_prompt = (
                f"User query: {query}\n"
                f"Trip duration: {days} days\n"
                + (f"Budget: ₹{budget:,.0f} INR\n" if budget else "")
                + f"Language preference: {language}\n"
                "Please provide travel recommendations."
            )
            llm_response = await ai_adapter.generate(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.4,
                max_tokens=200,
            )
            if llm_response:
                response_text = llm_response
                llm_used = True
                agent_model = "ollama_qwen2.5"
        except Exception as exc:
            logger.debug("travel_llm_skipped", reason=str(exc))

        # ---- Rules-based fallback -------------------------------------------
        if not response_text:
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
                "source_citations": [
                    "Goa Tourism Official Website (https://www.goatourism.gov.in)",
                    "Archaeological Survey of India",
                ],
                "agent_model": agent_model,
                "llm_available": llm_used,
            },
            confidence=0.85 if llm_used else 0.7,
            evidence=[{"source": "static_knowledge_base" if not llm_used else "ollama_llm", "query": query[:100]}],
            reasoning=f"{'LLM-generated' if llm_used else 'Rules-based'} response for Goa travel query.",
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
        interests = task.payload.get("interests", [])

        daily_budget = budget_inr / (days * group_size) if days and group_size else 0

        # ---- Attempt LLM enhancement for personalised itinerary ---------------
        llm_used = False
        llm_note = ""
        try:
            from app.core import ai_adapter
            system_prompt = (
                "You are a Goa trip planning expert. Generate a brief, practical enhancement "
                "tip for a Goa itinerary based on the traveller's interests and constraints. "
                "Keep it under 80 words."
            )
            user_prompt = (
                f"Days: {days}, Group size: {group_size}, Budget: ₹{budget_inr:,.0f} INR\n"
                f"Interests: {', '.join(interests) if interests else 'general sightseeing'}\n"
                f"Accessibility required: {accessibility}\n"
                "Provide one specific insider tip for this trip."
            )
            tip = await ai_adapter.generate(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.5,
                max_tokens=100,
            )
            if tip:
                llm_note = tip.strip()
                llm_used = True
        except Exception as exc:
            logger.debug("itinerary_llm_skipped", reason=str(exc))

        # Day templates
        templates = [
            {"day": 1, "theme": "North Goa Beaches", "places": ["Calangute Beach", "Baga Beach", "Fort Aguada"], "estimated_cost_inr": 500},
            {"day": 2, "theme": "Heritage & Old Goa", "places": ["Basilica of Bom Jesus", "Sé Cathedral", "Museum of Goa"], "estimated_cost_inr": 300},
            {"day": 3, "theme": "South Goa & Nature", "places": ["Palolem Beach", "Dudhsagar Falls", "Cabo de Rama Fort"], "estimated_cost_inr": 800},
            {"day": 4, "theme": "Markets & Culture", "places": ["Anjuna Flea Market", "Mapusa Market", "Fontainhas Latin Quarter"], "estimated_cost_inr": 400},
            {"day": 5, "theme": "Wildlife & Spice", "places": ["Bhagwan Mahaveer Sanctuary", "Sahakari Spice Farm", "Bondla Wildlife Sanctuary"], "estimated_cost_inr": 600},
        ]

        itinerary = []
        for i in range(min(days, len(templates))):
            day_plan = templates[i].copy()
            if accessibility:
                day_plan["accessibility_note"] = "Please verify wheelchair/mobility access before visiting"
            itinerary.append(day_plan)

        static_tips = [
            "Book accommodations in advance during peak season (Dec-Jan)",
            "Carry cash — many local vendors don't accept cards",
            "Rent a scooter for easy local transport",
        ]
        if llm_note:
            static_tips.insert(0, f"💡 AI tip: {llm_note}")

        return self._build_output(
            task.task_id,
            status="success",
            result={
                "days": days,
                "total_budget_inr": budget_inr,
                "group_size": group_size,
                "daily_per_person_budget": round(daily_budget, 2),
                "itinerary": itinerary,
                "tips": static_tips,
                "agent_model": "ollama_qwen2.5" if llm_used else "rules_based_v1",
            },
            confidence=0.8 if llm_used else 0.75,
            evidence=[{"source": "goa_travel_templates_v1"}],
            reasoning=f"Generated {days}-day itinerary for {group_size} person(s). LLM tip: {llm_used}.",
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
        "aguada fort": {
            "full_name": "Fort Aguada",
            "type": "State Protected Monument",
            "year": 1612,
            "location": "Sinquerim, North Goa",
            "description": "17th century Portuguese fort with a lighthouse. Overlooks the confluence of the Mandovi river and the Arabian Sea.",
            "entry": "Free",
            "district": "North Goa",
        },
    }

    async def run(self, task: AgentInput) -> AgentOutput:
        site_query = task.payload.get("site", "").lower().strip()
        info = self.HERITAGE_DB.get(site_query)

        if not info:
            matches = [k for k in self.HERITAGE_DB if site_query in k or k in site_query]
            if matches:
                info = self.HERITAGE_DB[matches[0]]

        # ---- LLM enhancement for richer description -------------------------
        if info:
            try:
                from app.core import ai_adapter
                system_prompt = (
                    "You are a Goa heritage expert. Provide one interesting historical fact "
                    "or visitor tip for the given heritage site. Under 60 words."
                )
                llm_fact = await ai_adapter.generate(
                    prompt=f"Heritage site: {info['full_name']}\nContext: {info['description']}",
                    system=system_prompt,
                    temperature=0.6,
                    max_tokens=80,
                )
                if llm_fact:
                    info = {**info, "ai_insight": llm_fact.strip()}
            except Exception:
                pass

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
