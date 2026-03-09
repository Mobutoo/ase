from __future__ import annotations

"""NLP service — parse natural language into structured event data.

Pipeline:
1. Try LLM via LiteLLM endpoint (httpx, async-capable).
2. Fall back to regex patterns for common FR/EN date-time formats.

Returns a dict: {member_id, title, start_at, end_at, location, rrule, confidence}
confidence is a float 0.0–1.0 (1.0 = LLM success, 0.5 = regex match).
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "")
AGENT_NLP_MODEL = os.environ.get("AGENT_NLP_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Regex patterns — FR and EN
# ---------------------------------------------------------------------------

# Date patterns: "15 mars 2025", "March 15 2025", "15/03/2025", "2025-03-15"
_MONTH_FR = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
}
_MONTH_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

_DATE_NUMERIC_RE = re.compile(
    r"(?P<day>\d{1,2})[/\-\.](?P<month>\d{1,2})[/\-\.](?P<year>\d{4})"
)
_DATE_ISO_RE = re.compile(
    r"(?P<year>\d{4})[/\-\.](?P<month>\d{1,2})[/\-\.](?P<day>\d{1,2})"
)
_DATE_WORD_RE = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month_str>[a-zéûôàèù]+)\s+(?P<year>\d{4})",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"(?P<hour>\d{1,2})[h:H](?P<minute>\d{2})?")
_DURATION_FR_RE = re.compile(r"(?P<hours>\d+)\s*h(?:eure)?s?\s*(?:(?P<minutes>\d+)\s*min)?")
_DURATION_EN_RE = re.compile(r"(?P<hours>\d+)\s*hour(?:s)?\s*(?:(?P<minutes>\d+)\s*min(?:ute)?s?)?")


def _parse_date_regex(text: str) -> datetime | None:
    """Attempt to extract a date from text using regex patterns."""
    # ISO: YYYY-MM-DD
    m = _DATE_ISO_RE.search(text)
    if m:
        try:
            return datetime(int(m["year"]), int(m["month"]), int(m["day"]), tzinfo=timezone.utc)
        except ValueError:
            pass

    # Numeric: DD/MM/YYYY
    m = _DATE_NUMERIC_RE.search(text)
    if m:
        try:
            return datetime(int(m["year"]), int(m["month"]), int(m["day"]), tzinfo=timezone.utc)
        except ValueError:
            pass

    # Word: "15 mars 2025" or "15 March 2025"
    m = _DATE_WORD_RE.search(text)
    if m:
        month_str = m["month_str"].lower()
        month = _MONTH_FR.get(month_str) or _MONTH_EN.get(month_str)
        if month:
            try:
                return datetime(int(m["year"]), month, int(m["day"]), tzinfo=timezone.utc)
            except ValueError:
                pass

    return None


def _parse_time_regex(text: str) -> tuple[int, int] | None:
    """Return (hour, minute) extracted from text, or None."""
    m = _TIME_RE.search(text)
    if m:
        hour = int(m["hour"])
        minute = int(m["minute"]) if m["minute"] else 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    return None


def _parse_duration_regex(text: str) -> int:
    """Return event duration in minutes from text, default 60."""
    for pattern in (_DURATION_FR_RE, _DURATION_EN_RE):
        m = pattern.search(text)
        if m:
            hours = int(m["hours"]) if m["hours"] else 0
            minutes = int(m["minutes"]) if m.groupdict().get("minutes") and m["minutes"] else 0
            total = hours * 60 + minutes
            if total > 0:
                return total
    return 60  # default 1 hour


def _regex_fallback(text: str, circle: object) -> dict:
    """Parse text using regex patterns. Returns structured dict with confidence 0.5."""
    result: dict = {
        "member_id": None,
        "title": text.strip(),
        "start_at": None,
        "end_at": None,
        "location": None,
        "rrule": None,
        "confidence": 0.5,
        "source": "regex",
    }

    date = _parse_date_regex(text)
    time_parts = _parse_time_regex(text)
    duration_minutes = _parse_duration_regex(text)

    if date:
        if time_parts:
            hour, minute = time_parts
            start_at = date.replace(hour=hour, minute=minute)
        else:
            start_at = date.replace(hour=9, minute=0)  # default morning
        result["start_at"] = start_at.isoformat()
        result["end_at"] = (start_at + timedelta(minutes=duration_minutes)).isoformat()

    return result


def _build_llm_prompt(text: str, circle: object) -> list[dict]:
    """Build the messages list for the LLM NLP extraction call."""
    member_names = []
    try:
        member_names = [m.display_name for m in circle.members.select_related("user").all()]
    except Exception:  # noqa: BLE001
        pass

    system = (
        "You are a calendar assistant. Extract event information from the user message. "
        "Respond ONLY with valid JSON matching this schema: "
        '{"member_id": null, "member_name": <string|null>, "title": <string>, '
        '"start_at": <ISO8601 string|null>, "end_at": <ISO8601 string|null>, '
        '"location": <string|null>, "rrule": <RFC5545 RRULE string|null>, '
        '"confidence": <float 0.0-1.0>}. '
        "Use null for fields you cannot determine. "
        "Dates must be UTC ISO8601. "
        f"Known circle members: {', '.join(member_names) or 'unknown'}."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]


def parse_natural_language(text: str, circle: object) -> dict:
    """Parse a natural language event description into structured data.

    Tries LLM first, falls back to regex on failure or low confidence.

    Args:
        text: Natural language input (FR or EN).
        circle: circles.Circle instance (used for member name resolution).

    Returns:
        dict with keys: member_id, title, start_at, end_at, location, rrule, confidence.
    """
    if not text or not text.strip():
        return {
            "member_id": None,
            "title": "",
            "start_at": None,
            "end_at": None,
            "location": None,
            "rrule": None,
            "confidence": 0.0,
            "source": "empty",
        }

    # --- LLM attempt ---
    if LITELLM_URL and LITELLM_API_KEY:
        try:
            messages = _build_llm_prompt(text, circle)
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"{LITELLM_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LITELLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": AGENT_NLP_MODEL,
                        "messages": messages,
                        "temperature": 0.0,
                        "max_tokens": 512,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)

                # Resolve member name → id if possible
                if parsed.get("member_name") and not parsed.get("member_id"):
                    try:
                        name = parsed["member_name"]
                        member = circle.members.filter(display_name__iexact=name).first()
                        if member:
                            parsed["member_id"] = member.pk
                    except Exception:  # noqa: BLE001
                        pass

                parsed.setdefault("source", "llm")
                parsed.setdefault("confidence", 0.9)
                logger.debug("NLP LLM result for circle %s: %s", circle.pk, parsed)
                return parsed

        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("NLP LLM failed, falling back to regex: %s", exc)

    # --- Regex fallback ---
    result = _regex_fallback(text, circle)
    logger.debug("NLP regex result for circle %s: %s", circle.pk, result)
    return result
