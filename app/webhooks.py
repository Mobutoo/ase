"""
Webhook service for Ase → n8n → OpenClaw AI integration.

All functions are fire-and-forget with short timeouts to never block requests.
Errors are caught explicitly and logged — never silently swallowed.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_session_event(session):
    """Send session-complete event to n8n webhook.

    Returns True on success, False on failure, None if webhook not configured.
    Never raises — safe to call from signals.
    """
    webhook_url = getattr(settings, "N8N_WEBHOOK_SESSION", None)
    if not webhook_url:
        logger.debug("N8N_WEBHOOK_SESSION not configured, skipping session event")
        return None

    payload = {
        "event": "session_complete",
        "user": session.user.username,
        "mode": session.mode,
        "planned_duration": session.planned_duration,
        "actual_duration": session.actual_duration,
        "energy_before": session.energy_before,
        "energy_after": session.energy_after,
        "completed": session.completed,
        "timestamp": session.ended_at.isoformat() if session.ended_at else None,
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=5)
        success = resp.status_code == 200
        if not success:
            logger.warning(
                "n8n session webhook returned HTTP %s for user=%s",
                resp.status_code,
                session.user.username,
            )
        return success
    except requests.RequestException as exc:
        logger.error(
            "n8n session webhook request failed for user=%s: %s",
            session.user.username,
            exc,
        )
        return False


def send_daily_plan_request(user, tasks, energy_history):
    """Request AI daily plan from n8n.

    Blocks up to 30 s (n8n processes + AI responds).
    Returns parsed JSON dict on success, None on failure.
    """
    webhook_url = getattr(settings, "N8N_WEBHOOK_DAILY_PLAN", None)
    if not webhook_url:
        logger.debug("N8N_WEBHOOK_DAILY_PLAN not configured, skipping daily plan request")
        return None

    payload = {
        "event": "daily_plan_request",
        "user": user.username,
        "tasks": tasks,
        "energy_patterns": energy_history,
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "n8n daily-plan webhook returned HTTP %s for user=%s",
            resp.status_code,
            user.username,
        )
        return None
    except requests.JSONDecodeError as exc:
        logger.error(
            "n8n daily-plan webhook returned invalid JSON for user=%s: %s",
            user.username,
            exc,
        )
        return None
    except requests.RequestException as exc:
        logger.error(
            "n8n daily-plan webhook request failed for user=%s: %s",
            user.username,
            exc,
        )
        return None


def send_reflection_prompt(user, sessions_today):
    """Request end-of-day reflection prompt from AI.

    Blocks up to 30 s.
    Returns parsed JSON dict on success, None on failure.
    """
    webhook_url = getattr(settings, "N8N_WEBHOOK_REFLECTION", None)
    if not webhook_url:
        logger.debug("N8N_WEBHOOK_REFLECTION not configured, skipping reflection request")
        return None

    serialized_sessions = [
        {
            "mode": s.mode,
            "planned_duration": s.planned_duration,
            "actual_duration": s.actual_duration,
            "completed": s.completed,
            "energy_before": s.energy_before,
            "energy_after": s.energy_after,
        }
        for s in sessions_today
    ]

    payload = {
        "event": "reflection_request",
        "user": user.username,
        "sessions_today": serialized_sessions,
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "n8n reflection webhook returned HTTP %s for user=%s",
            resp.status_code,
            user.username,
        )
        return None
    except requests.JSONDecodeError as exc:
        logger.error(
            "n8n reflection webhook returned invalid JSON for user=%s: %s",
            user.username,
            exc,
        )
        return None
    except requests.RequestException as exc:
        logger.error(
            "n8n reflection webhook request failed for user=%s: %s",
            user.username,
            exc,
        )
        return None
