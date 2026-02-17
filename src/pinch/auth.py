"""Authentication — OAuth-only via Claude Code's credential file.

SECURITY MODEL:
- Pinch NEVER stores, caches, or writes credentials to disk.
- The OAuth token is read fresh from Claude Code's file on every poll.
- If the file doesn't exist or the token is invalid, Pinch shows an error.
- No API keys are accepted or stored.
"""

import json
import logging
import time
from pathlib import Path

from .config import CREDENTIALS_PATH

log = logging.getLogger(__name__)

# Buffer before expiry to trigger early re-read (5 minutes in ms)
_EXPIRY_BUFFER_MS = 5 * 60 * 1000


def read_access_token(path: Path | None = None) -> str | None:
    """Read the OAuth access token from ~/.claude/.credentials.json.

    Returns the token string, or None if unavailable.
    The token is never logged, printed, or cached.
    """
    cred_path = path or CREDENTIALS_PATH
    try:
        data = json.loads(cred_path.read_text(encoding="utf-8"))
        token = data.get("claudeAiOauth", {}).get("accessToken")
        if not token:
            log.error("No accessToken found in credentials file")
            return None
        return token
    except FileNotFoundError:
        log.error("Credentials file not found: %s", cred_path)
        return None
    except (json.JSONDecodeError, KeyError) as exc:
        log.error("Failed to parse credentials file")
        return None


def check_token_health(path: Path | None = None) -> tuple[str, str]:
    """Check if the OAuth token exists and whether it's expired or expiring soon.

    Returns (status, message) where status is one of:
    - "ok"       — token exists and has plenty of time left
    - "expiring" — token is within 5 minutes of expiry
    - "expired"  — token has passed its expiresAt timestamp
    - "missing"  — no token or credentials file found
    """
    cred_path = path or CREDENTIALS_PATH
    try:
        data = json.loads(cred_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "missing", "Credentials file not found"
    except (json.JSONDecodeError, KeyError):
        return "missing", "Credentials file is corrupt"

    oauth = data.get("claudeAiOauth", {})
    token = oauth.get("accessToken")
    if not token:
        return "missing", "No accessToken in credentials"

    expires_at = oauth.get("expiresAt")
    if not expires_at:
        return "ok", "Token present (no expiry info)"

    now_ms = int(time.time() * 1000)
    try:
        exp_ms = int(expires_at)
    except (ValueError, TypeError):
        return "ok", "Token present (unparseable expiry)"

    if now_ms > exp_ms:
        return "expired", "Token expired — open Claude Code to refresh"
    elif now_ms > exp_ms - _EXPIRY_BUFFER_MS:
        mins_left = max(0, (exp_ms - now_ms) // 60000)
        return "expiring", f"Token expires in {mins_left}m"
    else:
        mins_left = (exp_ms - now_ms) // 60000
        return "ok", f"Token valid ({mins_left}m remaining)"


def has_oauth_credentials(path: Path | None = None) -> bool:
    """Check if OAuth credentials file exists and contains a token."""
    cred_path = path or CREDENTIALS_PATH
    try:
        data = json.loads(cred_path.read_text(encoding="utf-8"))
        token = data.get("claudeAiOauth", {}).get("accessToken")
        return bool(token)
    except Exception:
        return False


def test_connection() -> tuple[bool, str]:
    """Test OAuth connection by fetching usage data.

    Returns (success, message). Never exposes token content in the message.
    """
    from .usage_api import fetch_usage

    # Check health first
    status, health_msg = check_token_health()
    if status == "missing":
        return False, f"No OAuth token — is Claude Code installed?"
    if status == "expired":
        return False, health_msg

    token = read_access_token()
    if not token:
        return False, "No OAuth token found — is Claude Code installed?"

    data = fetch_usage(token)
    if data.error:
        return False, f"Connection failed: {data.error}"

    return True, f"Connected! 5h: {data.five_hour.utilization:.0f}%"
