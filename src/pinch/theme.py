"""Windows dark mode detection and theme helpers."""

import logging
import winreg

log = logging.getLogger(__name__)


def is_dark_mode() -> bool:
    """Check if Windows is using dark mode for apps."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0  # 0 = dark mode
    except OSError:
        return True  # Default to dark


def get_taskbar_color() -> str:
    """Return a background color that blends with the Windows taskbar."""
    if is_dark_mode():
        return "#1e1e2e"
    else:
        return "#f0f0f0"


def get_taskbar_text_color() -> str:
    """Return text color that contrasts with taskbar background."""
    if is_dark_mode():
        return "#cdd6f4"
    else:
        return "#1e1e2e"
