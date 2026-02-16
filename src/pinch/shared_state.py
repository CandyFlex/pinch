"""Thread-safe container for usage data.

SECURITY MODEL:
- Contains only usage metric data (percentages, timestamps).
- No credentials, tokens, or authentication data flows through this module.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Callable

log = logging.getLogger(__name__)


@dataclass
class UsageBucket:
    """A single usage metric bucket."""
    utilization: float = 0.0
    resets_at: str | None = None


@dataclass
class ExtraUsage:
    """Extra usage / overuse credits info."""
    is_enabled: bool = False
    monthly_limit: float = 0.0
    used_credits: float = 0.0
    utilization: float = 0.0


@dataclass
class UsageData:
    """Complete usage snapshot from the API."""
    five_hour: UsageBucket = field(default_factory=UsageBucket)
    seven_day: UsageBucket = field(default_factory=UsageBucket)
    seven_day_sonnet: UsageBucket = field(default_factory=UsageBucket)
    extra_usage: ExtraUsage = field(default_factory=ExtraUsage)
    error: str | None = None
    last_updated: str | None = None


class SharedState:
    """Thread-safe wrapper around UsageData with change callbacks."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = UsageData()
        self._callbacks: list[Callable[[UsageData], None]] = []

    def update(self, data: UsageData) -> None:
        """Update the stored data and notify all callbacks."""
        with self._lock:
            self._data = data
        for cb in self._callbacks:
            try:
                cb(data)
            except Exception:
                log.debug("Callback error in %s", cb.__name__, exc_info=True)

    def get(self) -> UsageData:
        """Return a snapshot of the current data."""
        with self._lock:
            return self._data

    def on_change(self, callback: Callable[[UsageData], None]) -> None:
        """Register a callback to be invoked on every update."""
        self._callbacks.append(callback)
