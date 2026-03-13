from __future__ import annotations

"""Event Graph service — detect and generate dependent events.

When an event is created or modified, the agent analyses whether it needs
dependent events (transport, meal reservations, accompaniment). All proposals
are returned as AgentAction instances in PENDING state — never executed
directly.

External dependency: Google Maps Directions API (optional).
If GOOGLE_MAPS_API_KEY is not set, travel times are estimated heuristically.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from calendars.models import Event
    from agents.models import AgentAction

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

# Heuristic travel time when Maps API is unavailable (minutes)
DEFAULT_TRAVEL_MINUTES = 30

# Minimum event duration (minutes) to consider generating dependents
MIN_EVENT_DURATION_MINUTES = 30

# Event types/keywords that trigger dependent generation
TRANSPORT_KEYWORDS = frozenset([
    "concert", "spectacle", "match", "cinema", "musee", "theatre",
    "school", "ecole", "hopital", "hospital", "aeroport", "airport",
    "gare", "station", "rendez-vous", "rdv", "reunion", "meeting",
])

MEAL_KEYWORDS = frozenset([
    "dejeuner", "diner", "lunch", "dinner", "repas", "restaurant",
    "brunch", "petit-dejeuner", "breakfast",
    # Food planning / cooking keywords (Mealie & Grocy integration)
    "cuisine", "recette", "menu", "repas",
])

# Keywords related to grocery shopping and pantry management (Grocy integration)
FOOD_STOCK_KEYWORDS = frozenset([
    "courses", "marche", "marché", "ingredient", "ingrédient",
    "stock", "peremption", "péremption", "frigo", "congelateur",
    "congélateur", "garde-manger",
])


def _resolve_home_address(event: Event) -> str:
    """Resolve the home address for the event's first member.

    Looks up MemberPreference(category="address", key="home") for the first
    member assigned to the event. Returns empty string if not found.
    """
    try:
        from agents.models import MemberPreference

        member_ids = list(event.members.values_list("pk", flat=True))
        if not member_ids:
            return ""

        pref = MemberPreference.objects.filter(
            member_id__in=member_ids,
            category="address",
            key="home",
        ).first()
        if pref and pref.value:
            return str(pref.value) if isinstance(pref.value, str) else pref.value.get("address", "")
    except Exception:  # noqa: BLE001
        pass
    return ""


def _get_travel_info(origin: str, destination: str) -> dict[str, Any]:
    """Return travel info between two locations using Google Directions API.

    Returns a dict with:
        duration_minutes: int — estimated travel time
        distance_km: float — distance in km
        summary: str — route summary (e.g. "via A6")
        steps_summary: str — brief step-by-step directions

    Falls back to heuristic defaults on error or missing key.
    """
    default = {
        "duration_minutes": DEFAULT_TRAVEL_MINUTES,
        "distance_km": 0.0,
        "summary": "",
        "steps_summary": "",
    }

    if not GOOGLE_MAPS_API_KEY or not origin or not destination:
        return default

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                GOOGLE_DIRECTIONS_URL,
                params={
                    "origin": origin,
                    "destination": destination,
                    "mode": "driving",
                    "language": "fr",
                    "key": GOOGLE_MAPS_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "OK" or not data.get("routes"):
            logger.warning("Directions API status: %s", data.get("status"))
            return default

        route = data["routes"][0]
        leg = route["legs"][0]

        duration_minutes = leg["duration"]["value"] // 60
        distance_km = round(leg["distance"]["value"] / 1000, 1)
        summary = route.get("summary", "")

        # Build a brief summary of the first 3 steps
        steps = leg.get("steps", [])
        step_texts = []
        for step in steps[:3]:
            instruction = step.get("html_instructions", "")
            # Strip HTML tags
            import re
            clean = re.sub(r"<[^>]+>", "", instruction)
            if clean:
                step_texts.append(clean)

        return {
            "duration_minutes": duration_minutes,
            "distance_km": distance_km,
            "summary": summary,
            "steps_summary": " → ".join(step_texts) if step_texts else "",
        }

    except (httpx.HTTPError, KeyError, IndexError) as exc:
        logger.warning("Google Directions API error: %s — using default travel time", exc)

    return default


def _title_matches_keywords(title: str, keywords: frozenset[str]) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in keywords)


def analyze_event(event: Event) -> dict:
    """Analyse an event and return a dict describing what dependents are needed.

    Returns::

        {
            "needs_transport": bool,
            "needs_meal": bool,
            "needs_accompany": bool,
            "needs_food_stock": bool,
            "reasons": [str, ...],
        }
    """
    result = {
        "needs_transport": False,
        "needs_meal": False,
        "needs_accompany": False,
        "needs_food_stock": False,
        "reasons": [],
    }

    title = event.title or ""
    duration_minutes = 0
    if event.start_at and event.end_at:
        duration_minutes = int((event.end_at - event.start_at).total_seconds() / 60)

    if duration_minutes < MIN_EVENT_DURATION_MINUTES:
        return result

    if event.location and _title_matches_keywords(title, TRANSPORT_KEYWORDS):
        result["needs_transport"] = True
        result["reasons"].append(f"Event '{title}' has location and matches transport keywords.")

    if _title_matches_keywords(title, MEAL_KEYWORDS):
        result["needs_meal"] = True
        result["reasons"].append(f"Event '{title}' matches meal keywords.")

    if _title_matches_keywords(title, FOOD_STOCK_KEYWORDS):
        result["needs_food_stock"] = True
        result["reasons"].append(f"Event '{title}' matches food stock / shopping keywords.")

    # Accompany: if event has child members and is outside school hours
    if event.start_at:
        hour = event.start_at.hour
        has_child_member = False
        try:
            has_child_member = event.members.filter(role="child").exists()
        except Exception:  # noqa: BLE001
            pass
        if has_child_member and (hour < 8 or hour >= 17):
            result["needs_accompany"] = True
            result["reasons"].append("Event includes child members outside standard hours.")

    return result


def generate_dependents(event: Event) -> list[dict]:
    """Generate AgentAction proposal payloads for dependent events.

    Does NOT write to the database — returns a list of payload dicts
    ready to be persisted as AgentAction records by the caller (task layer).

    Each payload matches the AgentAction.payload schema and contains
    enough data to create an Event if approved.
    """
    analysis = analyze_event(event)
    proposals: list[dict] = []

    circle = None
    try:
        circle = event.calendar.owner.circle
    except Exception:  # noqa: BLE001
        pass

    if analysis["needs_transport"] and event.location:
        # Resolve home address from member preferences
        home_address = _resolve_home_address(event)
        origin = home_address or "home"

        # Use Directions API for full itinerary
        travel_info = _get_travel_info(origin=origin, destination=event.location)
        travel_minutes = travel_info["duration_minutes"]
        departure_at = event.start_at - timedelta(minutes=travel_minutes + 10)  # 10min buffer

        proposals.append({
            "action_type": "event_create",
            "dependent_type": "transport",
            "source_event_id": event.pk,
            "title": f"🚗 Départ → {event.location}",
            "start_at": departure_at.isoformat(),
            "end_at": event.start_at.isoformat(),
            "location": event.location,
            "calendar_id": event.calendar_id,
            "members": list(event.members.values_list("pk", flat=True)),
            "reasons": analysis["reasons"],
            "travel_minutes_estimated": travel_minutes,
            "travel_distance_km": travel_info["distance_km"],
            "travel_route_summary": travel_info["summary"],
            "travel_steps": travel_info["steps_summary"],
            "origin_address": origin,
        })

    if analysis["needs_meal"]:
        # Search for nearby restaurants using Places API
        member_ids = list(event.members.values_list("pk", flat=True))
        restaurant_suggestions = []

        if event.location:
            try:
                from agents.services.places import geocode_address, search_nearby_restaurants
                coords = geocode_address(event.location)
                if coords:
                    restaurant_suggestions = search_nearby_restaurants(
                        latitude=coords[0],
                        longitude=coords[1],
                        member_ids=member_ids,
                        max_results=3,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Restaurant search failed: %s", exc)

        meal_start = event.start_at - timedelta(minutes=30)
        proposals.append({
            "action_type": "booking_propose",
            "dependent_type": "meal",
            "source_event_id": event.pk,
            "title": f"🍽️ Repas — {event.title}",
            "start_at": meal_start.isoformat(),
            "end_at": event.start_at.isoformat(),
            "location": event.location or "",
            "calendar_id": event.calendar_id,
            "members": member_ids,
            "reasons": analysis["reasons"],
            "restaurant_suggestions": restaurant_suggestions,
        })

    if analysis["needs_accompany"]:
        proposals.append({
            "action_type": "event_create",
            "dependent_type": "accompany",
            "source_event_id": event.pk,
            "title": f"Accompagnement — {event.title}",
            "start_at": (event.start_at - timedelta(minutes=15)).isoformat(),
            "end_at": event.end_at.isoformat() if event.end_at else None,
            "location": event.location or "",
            "calendar_id": event.calendar_id,
            "members": list(event.members.filter(role="child").values_list("pk", flat=True)),
            "reasons": analysis["reasons"],
        })

    if analysis["needs_food_stock"]:
        # Propose a stock/shopping check one day before the event so ingredients
        # can be sourced in time. The agent surfaces this as a Grocy review task.
        stock_check_at = event.start_at - timedelta(days=1)
        proposals.append({
            "action_type": "task_propose",
            "dependent_type": "food_stock",
            "source_event_id": event.pk,
            "title": f"Vérifier stocks & courses — {event.title}",
            "start_at": stock_check_at.isoformat(),
            "end_at": event.start_at.isoformat(),
            "calendar_id": event.calendar_id,
            "members": list(event.members.values_list("pk", flat=True)),
            "reasons": analysis["reasons"],
        })

    logger.info(
        "Event Graph: event=%s generated %d proposal(s) — %s",
        event.pk,
        len(proposals),
        [p["dependent_type"] for p in proposals],
    )

    return proposals
