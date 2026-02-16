"""Persistent user preferences stored in %LOCALAPPDATA%/Pinch/settings.json.

SECURITY MODEL:
- This file stores ONLY display preferences (poll interval, autostart, theme).
- NO credentials, tokens, API keys, or authentication data are ever written to disk.
- OAuth tokens are read live from Claude Code's credential file on each poll.
- File permissions are restricted to the owning user on creation.
"""

import json
import logging
import os
import stat
from pathlib import Path

log = logging.getLogger(__name__)

# Use LocalAppData (not Roaming) — prevents cloud sync / domain roaming exposure
SETTINGS_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Pinch"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULTS = {
    "poll_interval": 30,    # seconds between API polls
    "autostart": False,     # start with Windows
    "theme": "auto",        # "auto", "dark", "light"
}


def _ensure_dir() -> None:
    """Create the settings directory if it doesn't exist."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def _lock_file_permissions(path: Path) -> None:
    """Restrict file to owner-only read/write."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # Best effort — Windows ACLs may not fully respect POSIX modes


def load() -> dict:
    """Load settings from disk, returning defaults for missing keys."""
    settings = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            # Only accept known keys — reject anything unexpected
            for key in DEFAULTS:
                if key in data:
                    settings[key] = data[key]
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to load settings: %s", exc)
    return settings


def save(settings: dict) -> None:
    """Save settings to disk with restricted permissions."""
    _ensure_dir()
    # Strip any keys that aren't in DEFAULTS — defense in depth
    clean = {k: v for k, v in settings.items() if k in DEFAULTS}
    try:
        SETTINGS_FILE.write_text(
            json.dumps(clean, indent=2),
            encoding="utf-8",
        )
        _lock_file_permissions(SETTINGS_FILE)
        log.info("Settings saved to %s", SETTINGS_FILE)
    except OSError as exc:
        log.error("Failed to save settings: %s", exc)


def exists() -> bool:
    """Check if a settings file exists (for first-run detection)."""
    return SETTINGS_FILE.exists()


def get(key: str, default=None):
    """Load settings and return a single key."""
    settings = load()
    return settings.get(key, default)


def set_key(key: str, value) -> None:
    """Update a single key and save."""
    if key not in DEFAULTS:
        return  # Reject unknown keys
    settings = load()
    settings[key] = value
    save(settings)
