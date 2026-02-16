"""Background thread that polls the OAuth usage API at regular intervals.

SECURITY MODEL:
- Reads OAuth token fresh from Claude Code's file on each poll (never cached).
- Only calls the read-only, non-billable usage endpoint.
- No credentials are stored in memory longer than a single poll cycle.
"""

import logging
import threading

from .config import POLL_INTERVAL_SECONDS
from .auth import read_access_token
from .shared_state import SharedState, UsageData
from .usage_api import fetch_usage
from . import settings

log = logging.getLogger(__name__)


class UsageMonitor:
    """Background daemon thread that polls the Anthropic OAuth usage API."""

    def __init__(self, state: SharedState, interval: int | None = None) -> None:
        self._state = state
        self._interval = interval or POLL_INTERVAL_SECONDS
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background polling thread."""
        self._thread = threading.Thread(target=self._run, daemon=True, name="UsageMonitor")
        self._thread.start()
        log.info("Usage monitor started (poll every %ds)", self._interval)

    def stop(self) -> None:
        """Signal the monitor to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        log.info("Usage monitor stopped")

    def update_interval(self, interval: int) -> None:
        """Update the poll interval (takes effect next cycle)."""
        self._interval = interval
        log.info("Poll interval updated to %ds", interval)

    def poll_once(self) -> UsageData:
        """Do a single poll. Returns the fetched data."""
        token = read_access_token()
        if not token:
            data = UsageData(error="No OAuth token — is Claude Code installed?")
            self._state.update(data)
            return data
        data = fetch_usage(token)
        # Token goes out of scope here — not retained
        self._state.update(data)
        return data

    def _run(self) -> None:
        """Main loop: poll, update state, sleep."""
        consecutive_errors = 0
        while not self._stop_event.is_set():
            data = self.poll_once()

            if data.error:
                consecutive_errors += 1
                log.warning("Poll error (%d consecutive)", consecutive_errors)
            else:
                if consecutive_errors > 0:
                    log.info("Poll recovered after %d errors", consecutive_errors)
                consecutive_errors = 0

            # Re-read interval from settings each cycle
            s = settings.load()
            self._interval = s.get("poll_interval", POLL_INTERVAL_SECONDS)

            # Back off on repeated errors: double interval up to 5 minutes
            sleep_time = self._interval
            if consecutive_errors > 3:
                sleep_time = min(self._interval * (2 ** (consecutive_errors - 3)), 300)

            self._stop_event.wait(sleep_time)
