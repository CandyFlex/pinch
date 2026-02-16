"""HTTP client for the Anthropic OAuth usage API.

SECURITY MODEL:
- Only calls the OAuth usage endpoint (read-only, no billing).
- Uses explicit SSL context with certificate verification.
- Never sends API keys or makes billable API calls.
- Error messages are sanitized — no raw response bodies shown to users.
"""

import json
import logging
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone

from .config import OAUTH_BETA_HEADER, USAGE_API_URL
from .shared_state import UsageData, UsageBucket, ExtraUsage

log = logging.getLogger(__name__)


def _ssl_context() -> ssl.SSLContext:
    """Create an SSL context with certificate verification enforced.

    Uses the system certificate store. Falls back to default context
    if certifi is not available (still verified via system certs).
    """
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    # Enforce minimum TLS 1.2
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def fetch_usage(access_token: str) -> UsageData:
    """Call the Anthropic OAuth usage API and return parsed UsageData.

    This is a read-only, non-billable endpoint.
    Uses only stdlib urllib — no requests dependency needed.
    """
    req = urllib.request.Request(
        USAGE_API_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "anthropic-beta": OAUTH_BETA_HEADER,
            "Content-Type": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        log.error("API HTTP %d", exc.code)
        return UsageData(error=f"HTTP {exc.code}")
    except urllib.error.URLError as exc:
        reason = str(exc.reason) if exc.reason else "Unknown"
        # Sanitize — don't expose internal network details
        if "certificate" in reason.lower():
            return UsageData(error="SSL certificate error")
        return UsageData(error="Connection failed")
    except Exception:
        return UsageData(error="Connection failed")

    return _parse_response(raw)


def _parse_response(raw: dict) -> UsageData:
    """Parse the raw JSON response into UsageData."""
    def _bucket(key: str) -> UsageBucket:
        d = raw.get(key) or {}
        return UsageBucket(
            utilization=float(d.get("utilization", 0)),
            resets_at=d.get("resets_at"),
        )

    extra_raw = raw.get("extra_usage") or {}
    # API returns cents (e.g. 1139 = $11.39) — convert to dollars
    extra = ExtraUsage(
        is_enabled=bool(extra_raw.get("is_enabled", False)),
        monthly_limit=float(extra_raw.get("monthly_limit", 0)) / 100.0,
        used_credits=float(extra_raw.get("used_credits", 0)) / 100.0,
        utilization=float(extra_raw.get("utilization", 0)),
    )

    return UsageData(
        five_hour=_bucket("five_hour"),
        seven_day=_bucket("seven_day"),
        seven_day_sonnet=_bucket("seven_day_sonnet"),
        extra_usage=extra,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )
