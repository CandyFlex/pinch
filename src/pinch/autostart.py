"""Manage Windows auto-start via registry."""

import logging
import sys
import winreg

from .config import APP_REGISTRY_KEY, APP_REGISTRY_VALUE

log = logging.getLogger(__name__)


def is_autostart_enabled() -> bool:
    """Check if Pinch is registered to start with Windows."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REGISTRY_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_REGISTRY_VALUE)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_autostart(enabled: bool) -> None:
    """Enable or disable auto-start on login."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
        if enabled:
            exe_path = sys.executable
            if getattr(sys, "frozen", False):
                cmd = f'"{exe_path}"'
            else:
                script = sys.argv[0]
                cmd = f'"{exe_path}" "{script}"'
            winreg.SetValueEx(key, APP_REGISTRY_VALUE, 0, winreg.REG_SZ, cmd)
            log.info("Auto-start enabled: %s", cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_REGISTRY_VALUE)
                log.info("Auto-start disabled")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except OSError as exc:
        log.error("Failed to set auto-start: %s", exc)


def toggle_autostart() -> bool:
    """Toggle auto-start and return the new state."""
    current = is_autostart_enabled()
    set_autostart(not current)
    return not current
