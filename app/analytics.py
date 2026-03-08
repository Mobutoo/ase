"""
Pure analytics functions for Ase — Phase 3+4.

All functions are immutable: return new dicts/lists, no side effects.
All DB access uses Django ORM aggregations — no raw SQL.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import ExtractHour, ExtractIsoWeekDay
from django.utils import timezone

from app.models import EnergyReading, Session

User = get_user_model()

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _sessions_for_date(user, target_date):
    return Session.objects.filter(user=user, completed=True, started_at__date=target_date)


def _week_bounds(target_date):
    monday = target_date - timedelta(days=target_date.weekday())
    return monday, monday + timedelta(days=6)


def _month_bounds(target_date):
    first = target_date.replace(day=1)
    if first.month == 12:
        last = first.replace(year=first.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last = first.replace(month=first.month + 1, day=1) - timedelta(days=1)
    return first, last


def _aggregate_sessions(qs):
    agg = qs.aggregate(
        total_sessions=Count("id"),
        total_minutes=Sum("actual_duration"),
        avg_energy_before=Avg("energy_before"),
        avg_energy_after=Avg("energy_after"),
    )
    mode_rows = (
        qs.values("mode")
        .annotate(count=Count("id"), total_minutes=Sum("actual_duration"))
        .order_by("-count")
    )
    return {
        "total_sessions": agg["total_sessions"] or 0,
        "total_minutes": agg["total_minutes"] or 0,
        "avg_energy_before": round(agg["avg_energy_before"] or 0, 2),
        "avg_energy_after": round(agg["avg_energy_after"] or 0, 2),
        "mode_breakdown": [
            {"mode": r["mode"], "count": r["count"], "total_minutes": r["total_minutes"] or 0}
            for r in mode_rows
        ],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_daily_stats(user, target_date: date) -> dict:
    """Session stats for a single day."""
    qs = _sessions_for_date(user, target_date)
    return {"date": target_date.isoformat(), **_aggregate_sessions(qs)}


def get_weekly_stats(user, target_date: date) -> dict:
    """Session stats for the ISO week containing target_date."""
    monday, sunday = _week_bounds(target_date)
    qs = Session.objects.filter(
        user=user, completed=True,
        started_at__date__gte=monday, started_at__date__lte=sunday,
    )
    daily = [get_daily_stats(user, monday + timedelta(days=i)) for i in range(7)]
    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "daily_breakdown": daily,
        **_aggregate_sessions(qs),
    }


def get_monthly_stats(user, target_date: date) -> dict:
    """Session stats for the calendar month of target_date."""
    first, last = _month_bounds(target_date)
    qs = Session.objects.filter(
        user=user, completed=True,
        started_at__date__gte=first, started_at__date__lte=last,
    )
    num_days = (last - first).days + 1
    daily = [get_daily_stats(user, first + timedelta(days=i)) for i in range(num_days)]
    return {
        "month": target_date.month,
        "year": target_date.year,
        "daily_breakdown": daily,
        **_aggregate_sessions(qs),
    }


def get_energy_heatmap(user, days: int = 30) -> list:
    """
    Average energy grouped by hour-of-day and ISO weekday for the past N days.

    Returns: [{hour, weekday (1=Mon..7=Sun), avg_level}]
    """
    since = timezone.now() - timedelta(days=days)
    rows = (
        EnergyReading.objects.filter(user=user, timestamp__gte=since)
        .annotate(hour=ExtractHour("timestamp"), weekday=ExtractIsoWeekDay("timestamp"))
        .values("hour", "weekday")
        .annotate(avg_level=Avg("level"))
        .order_by("weekday", "hour")
    )
    return [
        {"hour": r["hour"], "weekday": r["weekday"], "avg_level": round(r["avg_level"], 2)}
        for r in rows
    ]


def get_density_chart(user, year: int) -> list:
    """
    GitHub-style contribution chart for a full year.

    Intensity scale: 0=none, 1=1 session, 2=2-3, 3=4-6, 4=7+
    Returns: [{date, intensity (0-4), total_minutes, session_count}]
    """
    qs = (
        Session.objects.filter(user=user, completed=True, started_at__year=year)
        .values(day=F("started_at__date"))
        .annotate(session_count=Count("id"), total_minutes=Sum("actual_duration"))
        .order_by("day")
    )
    day_map = {
        str(r["day"]): {"session_count": r["session_count"], "total_minutes": r["total_minutes"] or 0}
        for r in qs
    }

    def _intensity(n):
        if n == 0: return 0
        if n == 1: return 1
        if n <= 3: return 2
        if n <= 6: return 3
        return 4

    start, end = date(year, 1, 1), date(year, 12, 31)
    result, current = [], start
    while current <= end:
        iso = current.isoformat()
        data = day_map.get(iso, {"session_count": 0, "total_minutes": 0})
        result.append({
            "date": iso,
            "intensity": _intensity(data["session_count"]),
            "total_minutes": data["total_minutes"],
            "session_count": data["session_count"],
        })
        current += timedelta(days=1)
    return result


def get_streak(user) -> dict:
    """
    Compute current and longest consecutive active-day streaks.

    A day is active if the user completed at least one session.
    Returns: {current_streak, longest_streak, freeze_days_used, last_active_date}
    """
    active_days = set(
        Session.objects.filter(user=user, completed=True)
        .values_list("started_at__date", flat=True)
        .distinct()
    )
    if not active_days:
        return {"current_streak": 0, "longest_streak": 0, "freeze_days_used": 0, "last_active_date": None}

    sorted_days = sorted(active_days, reverse=True)
    today = timezone.localdate()
    settings_obj = getattr(user, "settings", None)
    freeze_budget = settings_obj.streak_freeze_days_remaining if settings_obj else 0

    # Current streak (with freeze days)
    current_streak, freeze_days_used = 0, 0
    cursor = today
    while True:
        if cursor in active_days:
            current_streak += 1
            cursor -= timedelta(days=1)
        elif freeze_budget > 0:
            freeze_budget -= 1
            freeze_days_used += 1
            cursor -= timedelta(days=1)
        else:
            break

    # Longest streak (no freezes for historical accuracy)
    longest, run, prev = 0, 0, None
    for d in sorted(active_days):
        if prev is None or (d - prev).days == 1:
            run += 1
        else:
            longest = max(longest, run)
            run = 1
        prev = d
    longest = max(longest, run)

    return {
        "current_streak": current_streak,
        "longest_streak": longest,
        "freeze_days_used": freeze_days_used,
        "last_active_date": sorted_days[0].isoformat(),
    }


def get_focus_score(user, target_date: date) -> float:
    """
    Focus score (0.0-100.0) for a single day.

    Formula:
      base        = min(sessions / 4, 1) * 50
      depth       = avg(actual / planned, capped at 1) * 30
      energy_bonus = max(0, (avg_energy_after - 3) / 2 * 20)
    """
    qs = _sessions_for_date(user, target_date)
    total = qs.count()
    if total == 0:
        return 0.0

    depth_rows = qs.filter(planned_duration__gt=0, actual_duration__isnull=False).annotate(
        ratio=F("actual_duration") * 1.0 / F("planned_duration")
    )
    ratios = [min(float(r.ratio), 1.0) for r in depth_rows]
    avg_depth = sum(ratios) / len(ratios) if ratios else 0.5

    agg = qs.aggregate(avg_energy=Avg("energy_after"))
    avg_energy = agg["avg_energy"] or 3.0
    energy_bonus = max(0.0, (avg_energy - 3.0) / 2.0 * 20.0)

    raw = min(total / 4, 1.0) * 50.0 + avg_depth * 30.0 + energy_bonus
    return round(min(raw, 100.0), 1)


def check_achievements(user) -> list:
    """
    Return list of achievement_type strings that are newly earned but not yet recorded.

    Idempotent — reads existing Achievement records, returns only NEW ones.
    Does NOT create Achievement objects (caller's responsibility).
    """
    from app.models_phase34 import Achievement  # deferred to avoid circular imports

    already = set(
        Achievement.objects.filter(user=user).values_list("achievement_type", flat=True)
    )
    earned = []
    total = Session.objects.filter(user=user, completed=True).count()
    longest = get_streak(user)["longest_streak"]
    energy_count = EnergyReading.objects.filter(user=user).count()

    session_milestones = [
        ("first_session", 1), ("sessions_10", 10), ("sessions_50", 50),
        ("sessions_100", 100), ("sessions_500", 500),
    ]
    streak_milestones = [("streak_3", 3), ("streak_7", 7), ("streak_30", 30)]

    for ach_type, threshold in session_milestones:
        if ach_type not in already and total >= threshold:
            earned.append(ach_type)

    for ach_type, threshold in streak_milestones:
        if ach_type not in already and longest >= threshold:
            earned.append(ach_type)

    if "energy_tracker" not in already and energy_count >= 10:
        earned.append("energy_tracker")

    deep_work = Session.objects.filter(
        user=user, completed=True, actual_duration__gte=90
    ).exists()
    if "deep_work_master" not in already and deep_work:
        earned.append("deep_work_master")

    return earned


def get_leaderboard(period: str = "weekly") -> list:
    """
    Ranked list of users (profile_public=True) by total completed session minutes.

    Args:
        period: "weekly" | "monthly" | "all_time"
    Returns:
        [{rank, username, avatar, total_minutes, total_sessions}]
    """
    today = timezone.localdate()
    if period == "weekly":
        monday, sunday = _week_bounds(today)
        date_filter = Q(sessions__started_at__date__gte=monday, sessions__started_at__date__lte=sunday)
    elif period == "monthly":
        first, last = _month_bounds(today)
        date_filter = Q(sessions__started_at__date__gte=first, sessions__started_at__date__lte=last)
    else:
        date_filter = Q()

    rows = (
        User.objects.filter(Q(sessions__completed=True) & date_filter)
        .annotate(
            total_minutes=Sum("sessions__actual_duration"),
            total_sessions=Count("sessions__id"),
        )
        .filter(settings__profile_public=True)
        .order_by("-total_minutes")
        .select_related("settings")
        .values("username", "settings__image", "total_minutes", "total_sessions")
    )
    return [
        {
            "rank": idx + 1,
            "username": r["username"],
            "avatar": r["settings__image"] or "default.png",
            "total_minutes": r["total_minutes"] or 0,
            "total_sessions": r["total_sessions"] or 0,
        }
        for idx, r in enumerate(rows)
    ]
