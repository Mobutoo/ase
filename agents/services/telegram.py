from __future__ import annotations

"""Telegram bot integration service.

Sends formatted proposals and weekly digests to the family/circle chat.
Handles callback queries for approve/reject via inline keyboard buttons.

Environment variables:
    TELEGRAM_BOT_TOKEN   — Bot token from @BotFather
    TELEGRAM_WEBHOOK_URL — Public HTTPS URL for webhook (optional)

The bot NEVER takes irreversible actions autonomously.
All approve/reject callbacks map to AgentAction state transitions.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"


def _tg_url(method: str) -> str:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    return TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN, method=method)


def _post(method: str, payload: dict[str, Any]) -> dict:
    """Make a synchronous POST request to the Telegram Bot API."""
    url = _tg_url(method)
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                logger.error("Telegram API error: %s", data)
            return data
    except httpx.HTTPError as exc:
        logger.error("Telegram HTTP error (%s): %s", method, exc)
        return {"ok": False, "error": str(exc)}


def _format_proposal(action: object) -> str:
    """Format an AgentAction proposal as a readable Telegram message with rich details."""
    payload = action.payload or {}
    dependent_type = payload.get("dependent_type", "")
    title = payload.get("title", "(sans titre)")
    start_at_raw = payload.get("start_at")
    end_at_raw = payload.get("end_at")
    location = payload.get("location", "")

    # Format datetimes
    start_str = ""
    end_str = ""
    if start_at_raw:
        try:
            dt = datetime.fromisoformat(start_at_raw)
            start_str = dt.strftime("%A %d %B %H:%M")
        except ValueError:
            start_str = start_at_raw
    if end_at_raw:
        try:
            dt = datetime.fromisoformat(end_at_raw)
            end_str = dt.strftime("%H:%M")
        except ValueError:
            end_str = end_at_raw

    # Icon based on dependent type
    icon_map = {
        "transport": "🚗",
        "meal": "🍽️",
        "accompany": "👶",
        "food_stock": "🛒",
    }
    icon = icon_map.get(dependent_type, "📋")

    lines = [
        f"{icon} *{title}*",
        "",
    ]

    if start_str and end_str:
        lines.append(f"📅 {start_str} — {end_str}")
    elif start_str:
        lines.append(f"📅 {start_str}")

    if location:
        lines.append(f"📍 {location}")

    # Transport-specific details
    if dependent_type == "transport":
        travel_min = payload.get("travel_minutes_estimated")
        distance = payload.get("travel_distance_km")
        route = payload.get("travel_route_summary")
        origin = payload.get("origin_address")

        if origin:
            lines.append(f"🏠 Départ : {origin}")
        if travel_min:
            lines.append(f"⏱️ Durée estimée : {travel_min} min")
        if distance:
            lines.append(f"📏 Distance : {distance} km")
        if route:
            lines.append(f"🛣️ Itinéraire : {route}")

    # Meal-specific: restaurant suggestions
    if dependent_type == "meal":
        suggestions = payload.get("restaurant_suggestions", [])
        if suggestions:
            lines.append("")
            lines.append("*Restaurants suggérés :*")
            for i, r in enumerate(suggestions[:3], 1):
                rating = f" ⭐{r['rating']}" if r.get("rating") else ""
                price = f" {r['price_level']}" if r.get("price_level") else ""
                lines.append(f"  {i}. {r['name']}{rating}{price}")
                if r.get("address"):
                    lines.append(f"     _{r['address']}_")

    # Reasons
    reasons = payload.get("reasons", [])
    if reasons:
        lines.append("")
        lines.append("_Raisons :_")
        lines.extend(f"  • {r}" for r in reasons)

    lines.append("")
    lines.append(f"_Proposition #{action.pk}_")
    return "\n".join(lines)


def _inline_keyboard(action_id: int) -> dict:
    """Build the inline keyboard for approve/reject."""
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Approuver",
                    "callback_data": json.dumps({"action": "approve", "id": action_id}),
                },
                {
                    "text": "Rejeter",
                    "callback_data": json.dumps({"action": "reject", "id": action_id}),
                },
            ]
        ]
    }


def send_proposal(circle: object, action: object) -> bool:
    """Send a formatted AgentAction proposal to the circle's Telegram chat.

    Args:
        circle: circles.Circle instance — must have telegram_chat_id set.
        action: agents.AgentAction instance in PENDING state.

    Returns:
        True on success, False on failure.
    """
    chat_id = getattr(circle, "telegram_chat_id", None)
    if not chat_id:
        logger.warning("Circle %s has no telegram_chat_id — skipping proposal send.", circle.pk)
        return False

    text = _format_proposal(action)
    result = _post(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": _inline_keyboard(action.pk),
        },
    )
    success = result.get("ok", False)
    if success:
        logger.info("Proposal sent to circle %s for action %s.", circle.pk, action.pk)
    return success


def send_digest(circle: object, digest_data: dict) -> bool:
    """Send a weekly digest summary to the circle's Telegram chat.

    Args:
        circle: circles.Circle instance — must have telegram_chat_id set.
        digest_data: Structured digest dict from digest.generate_digest().

    Returns:
        True on success, False on failure.
    """
    chat_id = getattr(circle, "telegram_chat_id", None)
    if not chat_id:
        logger.warning("Circle %s has no telegram_chat_id — skipping digest send.", circle.pk)
        return False

    week_label = digest_data.get("week_label", "")
    events = digest_data.get("events", [])
    highlights = digest_data.get("highlights", [])

    lines = [
        f"*Digest hebdomadaire* — {week_label}",
        f"_{len(events)} evenement(s) cette semaine_",
        "",
    ]

    for evt in events[:10]:  # cap at 10 events in Telegram message
        start = evt.get("start_at", "")
        title = evt.get("title", "")
        members = ", ".join(evt.get("member_names", []))
        lines.append(f"• *{title}* — {start}" + (f" ({members})" if members else ""))

    if highlights:
        lines.append("\n*Points cles :*")
        for h in highlights:
            lines.append(f"  ▸ {h}")

    text = "\n".join(lines)
    result = _post(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        },
    )
    success = result.get("ok", False)
    if success:
        logger.info("Digest sent to circle %s.", circle.pk)
    return success


def handle_callback_query(callback_query: dict) -> bool:
    """Process an approve/reject callback from a Telegram inline keyboard.

    This is called from the webhook view. It mutates the AgentAction state
    via the same code path as the REST API approve/reject actions.

    Args:
        callback_query: Raw Telegram callback_query dict from webhook payload.

    Returns:
        True if the callback was handled, False otherwise.
    """
    from django.utils import timezone as dj_timezone

    callback_id = callback_query.get("id")
    data_raw = callback_query.get("data", "{}")
    from_user = callback_query.get("from", {})
    telegram_user_id = str(from_user.get("id", ""))

    try:
        data = json.loads(data_raw)
    except json.JSONDecodeError:
        logger.warning("Invalid callback data: %s", data_raw)
        return False

    action_str = data.get("action")
    action_id = data.get("id")

    if action_str not in ("approve", "reject") or not action_id:
        return False

    try:
        from agents.models import AgentAction
        from circles.models import CircleMember

        agent_action = AgentAction.objects.select_related("circle").get(pk=action_id)

        if not agent_action.is_pending:
            _post("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Deja traite."})
            return True

        # Try to resolve CircleMember from Telegram user ID stored in preferences
        member = None
        try:
            from agents.models import MemberPreference
            pref = MemberPreference.objects.filter(
                member__circle=agent_action.circle,
                category="telegram",
                key="user_id",
                value=telegram_user_id,
            ).select_related("member").first()
            if pref:
                member = pref.member
        except Exception:  # noqa: BLE001
            pass

        now = dj_timezone.now()
        if action_str == "approve":
            agent_action.approved_by = member
            agent_action.approved_at = now
            agent_action.save(update_fields=["approved_by", "approved_at"])
            # Schedule execution
            try:
                from agents.tasks import execute_agent_action
                execute_agent_action.delay(agent_action.pk)
            except Exception:  # noqa: BLE001
                pass
            answer_text = "Approuve ! L'action va etre executee."
        else:
            agent_action.rejected_at = now
            agent_action.save(update_fields=["rejected_at"])
            answer_text = "Rejete. Aucune action effectuee."

        _post("answerCallbackQuery", {"callback_query_id": callback_id, "text": answer_text})
        logger.info("Callback %s: action %s %sd via Telegram.", callback_id, action_id, action_str)
        return True

    except AgentAction.DoesNotExist:
        _post("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Action introuvable."})
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("Callback handling error: %s", exc)
        return False
