from __future__ import annotations

"""Event Graph service — detect and generate dependent events.

When an event is created or modified, the agent analyses whether it needs
dependent events (transport, meal reservations, accompaniment). All proposals
are returned as AgentAction instances in PENDING state — never executed
directly.

External dependency: Google Maps Distance Matrix API (optional).
If GOOGLE_MAPS_API_KEY is not set, travel times are estimated heuristically.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from calendars.models import Event
    from agents.models import AgentAction

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_MAPS_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

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
])


def _get_travel_time_minutes(origin: str, destination: str) -> int:
    """Return estimated travel time in minutes between two locations.

    Uses Google Maps Distance Matrix API if configured.
    Falls back to DEFAULT_TRAVEL_MINUTES on error or missing key.
    """
    if not GOOGLE_MAPS_API_KEY or not origin or not destination:
        return DEFAULT_TRAVEL_MINUTES

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                GOOGLE_MAPS_URL,
                params={
                    "origins": origin,
                    "destinations": destination,
                    "mode": "transit",
                    "key": GOOGLE_MAPS_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            element = data["rows"][0]["elements"][0]
            if element["status"] == "OK":
                return element["duration"]["value"] // 60  # seconds → minutes
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        logger.warning("Google Maps API error: %s — using default travel time", exc)

    return DEFAULT_TRAVEL_MINUTES


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
            "reasons": [str, ...],
        }
    """
    result = {
        "needs_transport": False,
        "needs_meal": False,
        "needs_accompany": False,
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
        travel_minutes = _get_travel_time_minutes(
            origin="home",  # TODO: resolve from MemberPreference
            destination=event.location,
        )
        departure_at = event.start_at - timedelta(minutes=travel_minutes + 10)  # 10min buffer

        proposals.append({
            "action_type": "event_create",
            "dependent_type": "transport",
            "source_event_id": event.pk,
            "title": f"Transport → {event.location}",
            "start_at": departure_at.isoformat(),
            "end_at": event.start_at.isoformat(),
            "location": event.location,
            "calendar_id": event.calendar_id,
            "members": list(event.members.values_list("pk", flat=True)),
            "reasons": analysis["reasons"],
            "travel_minutes_estimated": travel_minutes,
        })

    if analysis["needs_meal"]:
        # Propose a restaurant 30 min before if it's a dinner event
        meal_start = event.start_at - timedelta(minutes=30)
        proposals.append({
            "action_type": "booking_propose",
            "dependent_type": "meal",
            "source_event_id": event.pk,
            "title": f"Reservation repas — {event.title}",
            "start_at": meal_start.isoformat(),
            "end_at": event.start_at.isoformat(),
            "location": event.location or "",
            "calendar_id": event.calendar_id,
            "members": list(event.members.values_list("pk", flat=True)),
            "reasons": analysis["reasons"],
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

    logger.info(
        "Event Graph: event=%s generated %d proposal(s) — %s",
        event.pk,
        len(proposals),
        [p["dependent_type"] for p in proposals],
    )

    return proposals
