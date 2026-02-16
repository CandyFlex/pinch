"""Utility functions for time formatting and display helpers."""

from datetime import datetime, timezone


def format_reset_time(iso_str: str | None) -> str:
    """Convert ISO reset timestamp to human-readable relative time.

    Examples: "in 2h 15m", "in 45m", "in 3d 5h"
    """
    if not iso_str:
        return "unknown"
    try:
        reset_dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = reset_dt - now

        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            return "now"

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 and days == 0:
            parts.append(f"{minutes}m")

        return "in " + " ".join(parts) if parts else "now"
    except (ValueError, TypeError):
        return "unknown"


def format_reset_datetime(iso_str: str | None) -> str:
    """Convert ISO reset timestamp to a readable date/time string.

    Example: "Mon Feb 17, 1:00 AM"
    """
    if not iso_str:
        return "Unknown"
    try:
        reset_dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local_dt = reset_dt.astimezone()
        return local_dt.strftime("%a %b %d, %-I:%M %p")
    except (ValueError, TypeError):
        # Windows doesn't support %-I, use %#I instead
        try:
            reset_dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            local_dt = reset_dt.astimezone()
            return local_dt.strftime("%a %b %d, %#I:%M %p")
        except (ValueError, TypeError):
            return "Unknown"


def pct_str(value: float | None) -> str:
    """Format a percentage value as a compact string."""
    if value is None:
        return "--"
    return f"{value:.0f}%"


def compact_countdown(iso_str: str | None) -> str:
    """Short countdown for the taskbar pill: '2h14m', '45m', '3d5h'.

    Returns empty string if unavailable.
    """
    if not iso_str:
        return ""
    try:
        reset_dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        total_seconds = int((reset_dt - now).total_seconds())
        if total_seconds <= 0:
            return "now"

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        if days > 0:
            return f"{days}d{hours}h"
        if hours > 0:
            return f"{hours}h{minutes:02d}m"
        return f"{minutes}m"
    except (ValueError, TypeError):
        return ""
