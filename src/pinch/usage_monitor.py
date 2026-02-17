"""Background thread that polls the OAuth usage API at regular intervals.

SECURITY MODEL:
- Reads OAuth token fresh from Claude Code's file on each poll (never cached).
- Only calls the read-only, non-billable usage endpoint.
- No credentials are stored in memory longer than a single poll cycle.

RECOVERY LOGIC:
- On 401, waits briefly and re-reads credentials (Claude Code may have refreshed).
- Checks token expiry proactively before each poll.
- Backs off exponentially on repeated errors (up to 5 minutes).
"""

import logging
import threading
import time

from .config import POLL_INTERVAL_SECONDS
from .auth import read_access_token, check_token_health
from .shared_state import SharedState, UsageData
from .usage_api import fetch_usage
from . import settings

log = logging.getLogger(__name__)

# Seconds to wait before retrying after a 401
_AUTH_RETRY_DELAY = 5
# Maximum retries on 401 before giving up for this cycle
_AUTH_MAX_RETRIES = 2


class UsageMonitor:
    """Background daemon thread that polls the Anthropic OAuth usage API."""

    def __init__(self, state: SharedState, interval: int | None = None) -> None:
        self._state = state
        self._interval = interval or POLL_INTERVAL_SECONDS
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._force_poll = threading.Event()

    def start(self) -> None:
        """Start the background polling thread."""
        self._thread = threading.Thread(target=self._run, daemon=True, name="UsageMonitor")
        self._thread.start()
        log.info("Usage monitor started (poll every %ds)", self._interval)

    def stop(self) -> None:
        """Signal the monitor to stop."""
        self._stop_event.set()
        self._force_poll.set()  # Unblock any wait
        if self._thread:
            self._thread.join(timeout=5)
        log.info("Usage monitor stopped")

    def update_interval(self, interval: int) -> None:
        """Update the poll interval (takes effect next cycle)."""
        self._interval = interval
        log.info("Poll interval updated to %ds", interval)

    def reconnect(self) -> None:
        """Force an immediate re-poll (called from Reconnect button)."""
        log.info("Reconnect requested — forcing immediate poll")
        self._force_poll.set()

    def poll_once(self) -> UsageData:
        """Do a single poll with automatic 401 retry.

        On 401: waits briefly, re-reads the credentials file (Claude Code
        may have refreshed the token in the background), and retries.
        """
        # Check token health before polling
        status, health_msg = check_token_health()
        if status == "expired":
            log.warning("Token expired: %s", health_msg)
            # Still try — the file might have been refreshed since we checked
        elif status == "expiring":
            log.info("Token expiring soon: %s", health_msg)
        elif status == "missing":
            data = UsageData(error="No OAuth token — is Claude Code installed?")
            self._state.update(data)
            return data

        # First attempt
        token = read_access_token()
        if not token:
            data = UsageData(error="No OAuth token — is Claude Code installed?")
            self._state.update(data)
            return data

        data = fetch_usage(token)

        # If 401, retry with fresh credentials
        if data.error and "401" in data.error:
            for attempt in range(1, _AUTH_MAX_RETRIES + 1):
                log.info(
                    "Got 401 — waiting %ds then re-reading credentials (attempt %d/%d)",
                    _AUTH_RETRY_DELAY, attempt, _AUTH_MAX_RETRIES,
                )
                time.sleep(_AUTH_RETRY_DELAY)

                # Re-read credentials (Claude Code may have refreshed the token)
                token = read_access_token()
                if not token:
                    continue

                data = fetch_usage(token)
                if not data.error or "401" not in data.error:
                    if not data.error:
                        log.info("Recovered from 401 on retry %d", attempt)
                    break

            # If still 401 after retries, give a helpful error
            if data.error and "401" in data.error:
                data = UsageData(
                    error="Token expired — open Claude Code to refresh, then click Reconnect"
                )

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
                log.warning("Poll error (%d consecutive): %s", consecutive_errors, data.error)
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

            # Wait, but break early if force_poll or stop is signaled
            self._force_poll.clear()
            self._force_poll.wait(sleep_time)
            if self._stop_event.is_set():
                break
            # If force_poll was set (reconnect), the wait returns early
            # and we loop back to poll immediately
