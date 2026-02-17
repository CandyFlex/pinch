"""Main application coordinator — wires all components together."""

import logging
import tkinter as tk

from .autostart import is_autostart_enabled, toggle_autostart
from .popup_view import PopupView
from .settings_ui import SettingsUI
from .setup_wizard import SetupWizard
from .shared_state import SharedState
from .taskbar_overlay import TaskbarOverlay
from .tray_icon import TrayIcon
from .usage_monitor import UsageMonitor
from . import settings

log = logging.getLogger(__name__)


class App:
    """Top-level coordinator for Pinch."""

    def __init__(self) -> None:
        self._state = SharedState()
        self._root: tk.Tk | None = None
        self._overlay: TaskbarOverlay | None = None
        self._tray: TrayIcon | None = None
        self._popup: PopupView | None = None
        self._settings_ui: SettingsUI | None = None
        self._monitor: UsageMonitor | None = None

    def run(self) -> None:
        """Start all components and enter the main loop."""
        log.info("Starting Pinch")

        # Tk root (hidden — overlay draws its own window)
        self._root = tk.Tk()
        self._root.withdraw()

        # First-run wizard if no settings exist
        if not settings.exists():
            wizard = SetupWizard(self._root)
            result = wizard.run()
            if result is None:
                log.info("Setup wizard cancelled, exiting")
                self._root.destroy()
                return

        # Load settings
        s = settings.load()

        # Create a separate toplevel for the overlay
        overlay_win = tk.Toplevel(self._root)
        overlay_win.withdraw()

        # Popup view
        self._popup = PopupView(self._root, self._state)

        # Settings window
        self._settings_ui = SettingsUI(
            self._root,
            on_settings_changed=self._on_settings_changed,
        )

        # Taskbar overlay
        self._overlay = TaskbarOverlay(
            overlay_win,
            self._state,
            on_click=self._toggle_popup,
        )
        overlay_win.deiconify()

        # System tray icon
        self._tray = TrayIcon(
            self._state,
            on_show_details=self._toggle_popup,
            on_show_settings=self._show_settings,
            on_toggle_autostart=self._handle_autostart_toggle,
            on_reconnect=self._handle_reconnect,
            on_exit=self._shutdown,
            get_autostart_state=is_autostart_enabled,
        )
        self._tray.start()

        # Background monitor
        self._monitor = UsageMonitor(
            self._state,
            interval=s.get("poll_interval", 30),
        )
        self._monitor.start()

        # Do an initial poll immediately
        self._root.after(100, self._monitor.poll_once)

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._shutdown)

        log.info("All components started, entering main loop")
        self._root.mainloop()

    def _toggle_popup(self) -> None:
        """Show or hide the detail popup."""
        if self._popup:
            if self._root:
                self._root.after(0, self._popup.toggle)

    def _show_settings(self) -> None:
        """Show the settings window."""
        if self._settings_ui:
            if self._root:
                self._root.after(0, self._settings_ui.show)

    def _on_settings_changed(self, new_settings: dict) -> None:
        """Handle settings changes — update monitor interval, etc."""
        if self._monitor:
            interval = new_settings.get("poll_interval", 30)
            self._monitor.update_interval(interval)
        log.info("Settings updated")

    def _handle_reconnect(self) -> None:
        """Force re-read of credentials and immediate re-poll."""
        if self._monitor:
            self._monitor.reconnect()

    def _handle_autostart_toggle(self) -> None:
        """Toggle Windows auto-start."""
        new_state = toggle_autostart()
        log.info("Auto-start toggled to: %s", new_state)

    def _shutdown(self) -> None:
        """Clean shutdown of all components."""
        log.info("Shutting down...")
        if self._monitor:
            self._monitor.stop()
        if self._tray:
            self._tray.stop()
        if self._popup:
            self._popup.hide()
        if self._settings_ui:
            self._settings_ui.hide()
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except tk.TclError:
                pass
        log.info("Shutdown complete")
