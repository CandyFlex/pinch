"""Authentication — OAuth-only via Claude Code's credential file.

SECURITY MODEL:
- Pinch NEVER stores, caches, or writes credentials to disk.
- The OAuth token is read fresh from Claude Code's file on every poll.
- If the file doesn't exist or the token is invalid, Pinch shows an error.
- No API keys are accepted or stored.
"""

import json
import logging
from pathlib import Path

from .config import CREDENTIALS_PATH

log = logging.getLogger(__name__)


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

    token = read_access_token()
    if not token:
        return False, "No OAuth token found — is Claude Code installed?"

    data = fetch_usage(token)
    if data.error:
        return False, f"Connection failed: {data.error}"

    return True, f"Connected! 5h: {data.five_hour.utilization:.0f}%"
