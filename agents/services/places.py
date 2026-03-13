from __future__ import annotations

"""Google Places service — search for nearby restaurants and services.

Uses Google Places API (New) for nearby search, filtered by member
preferences stored in MemberPreference.

Environment:
    GOOGLE_MAPS_API_KEY — shared with event_graph.py
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# Places API (New) endpoints
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Default search radius in meters
DEFAULT_RADIUS_METERS = 2000

# Place types relevant for family calendar
RESTAURANT_TYPES = ["restaurant", "cafe", "bakery", "meal_delivery", "meal_takeaway"]


def _get_member_food_preferences(member_id: int) -> dict[str, Any]:
    """Load food/restaurant preferences from MemberPreference.

    Returns a dict with keys like:
        cuisine_types: list[str]  — e.g. ["italian", "japanese"]
        price_level: str          — "PRICE_LEVEL_INEXPENSIVE" to "PRICE_LEVEL_VERY_EXPENSIVE"
        dietary: list[str]        — e.g. ["vegetarian", "halal"]
        exclude: list[str]        — restaurant names or types to exclude
    """
    prefs: dict[str, Any] = {
        "cuisine_types": [],
        "price_level": "",
        "dietary": [],
        "exclude": [],
    }

    try:
        from agents.models import MemberPreference

        qs = MemberPreference.objects.filter(
            member_id=member_id,
            category="restaurant",
        )
        for p in qs:
            if p.key in prefs and isinstance(p.value, list):
                prefs[p.key] = p.value
            elif p.key in prefs and isinstance(p.value, str):
                prefs[p.key] = p.value
    except Exception:  # noqa: BLE001
        pass

    return prefs


def search_nearby_restaurants(
    latitude: float,
    longitude: float,
    member_ids: list[int] | None = None,
    radius_meters: int = DEFAULT_RADIUS_METERS,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Search for nearby restaurants using Google Places API (New).

    Args:
        latitude: Center point latitude.
        longitude: Center point longitude.
        member_ids: Optional list of member IDs to load preferences for.
        radius_meters: Search radius in meters.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with keys: name, address, rating, price_level,
        place_id, types, location (lat/lng).
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set — returning empty restaurant list.")
        return []

    # Build request body for Places API (New)
    body: dict[str, Any] = {
        "includedTypes": RESTAURANT_TYPES,
        "maxResultCount": max_results,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.rating,"
            "places.priceLevel,places.id,places.types,places.location,"
            "places.regularOpeningHours"
        ),
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(PLACES_NEARBY_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        places = data.get("places", [])
        results = []

        # Load preferences for filtering
        preferences: dict[str, Any] = {}
        if member_ids:
            for mid in member_ids:
                member_prefs = _get_member_food_preferences(mid)
                # Merge: union of exclude lists, intersection-like for cuisines
                for k in ("exclude", "dietary"):
                    preferences.setdefault(k, [])
                    preferences[k].extend(member_prefs.get(k, []))

        exclude_names = {n.lower() for n in preferences.get("exclude", [])}

        for place in places:
            display_name = place.get("displayName", {}).get("text", "")

            # Filter out excluded restaurants
            if display_name.lower() in exclude_names:
                continue

            location = place.get("location", {})
            results.append({
                "name": display_name,
                "address": place.get("formattedAddress", ""),
                "rating": place.get("rating"),
                "price_level": place.get("priceLevel", ""),
                "place_id": place.get("id", ""),
                "types": place.get("types", []),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            })

        logger.info(
            "Places search: found %d restaurants near (%.4f, %.4f), returning %d after filters.",
            len(places), latitude, longitude, len(results),
        )
        return results[:max_results]

    except httpx.HTTPError as exc:
        logger.error("Google Places API error: %s", exc)
        return []
    except (KeyError, TypeError) as exc:
        logger.error("Google Places response parse error: %s", exc)
        return []


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode an address string to (latitude, longitude).

    Uses Google Geocoding API. Returns None if geocoding fails.
    """
    if not GOOGLE_MAPS_API_KEY or not address:
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url, params={"address": address, "key": GOOGLE_MAPS_API_KEY})
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if results:
            loc = results[0]["geometry"]["location"]
            return (loc["lat"], loc["lng"])
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        logger.warning("Geocoding failed for '%s': %s", address, exc)

    return None
