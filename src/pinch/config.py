"""Constants and configuration for Pinch."""

from pathlib import Path

# App identity
APP_NAME = "Pinch"
APP_TAGLINE = "Know your limits before they know you."
APP_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REGISTRY_VALUE = "Pinch"

# API
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_BETA_HEADER = "oauth-2025-04-20"
POLL_INTERVAL_SECONDS = 30
TASKBAR_REPOSITION_SECONDS = 1

# Credentials
CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

# Thresholds (percentage)
THRESHOLD_GREEN = 50    # 0-50% = green
THRESHOLD_YELLOW = 80   # 50-80% = yellow
                        # 80-100% = red

# Colors (dark theme)
COLOR_BG = "#1e1e2e"
COLOR_BG_POPUP = "#1a1b2e"
COLOR_TEXT = "#cdd6f4"
COLOR_TEXT_DIM = "#6c7086"
COLOR_GREEN = "#a6e3a1"
COLOR_YELLOW = "#f9e2af"
COLOR_RED = "#f38ba8"
COLOR_BLUE = "#89b4fa"
COLOR_BORDER = "#313244"
COLOR_BAR_BG = "#313244"
COLOR_ACCENT = "#e06c75"  # Crab coral-red

# Font
FONT_FAMILY = "Segoe UI"
FONT_SIZE_OVERLAY = 9
FONT_SIZE_POPUP_TITLE = 11
FONT_SIZE_POPUP_BODY = 9

# Overlay dimensions
OVERLAY_HEIGHT = 24
OVERLAY_MIN_WIDTH = 200

# Popup dimensions
POPUP_WIDTH = 300
POPUP_HEIGHT = 330


def color_for_utilization(pct: float) -> str:
    """Return color string based on utilization percentage."""
    if pct < THRESHOLD_GREEN:
        return COLOR_GREEN
    elif pct < THRESHOLD_YELLOW:
        return COLOR_YELLOW
    else:
        return COLOR_RED
