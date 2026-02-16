"""System tray icon with crab claw design and context menu."""

import logging
import threading

import pystray
from PIL import Image, ImageDraw

from .config import APP_NAME, COLOR_ACCENT, color_for_utilization
from .shared_state import SharedState, UsageData
from .utils import pct_str

log = logging.getLogger(__name__)

ICON_SIZE = 64


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b)."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _create_icon_image(accent_color: str = "#e06c75") -> Image.Image:
    """Create a crab claw / pincer icon.

    Draws a bold stylized pincer shape that reads clearly at 16-64px.
    Two thick curved claws opening upward with a gap between tips.
    """
    # Render at 2x then downsample for anti-aliasing
    render_size = ICON_SIZE * 2
    img = Image.new("RGBA", (render_size, render_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = render_size

    # Background circle
    bg_rgb = _hex_to_rgb(accent_color)
    draw.ellipse([3, 3, s - 4, s - 4], fill=bg_rgb)

    # Claw color (dark against the colored background)
    claw = _hex_to_rgb("#1e1e2e")

    # Center and scale factors
    cx, cy = s // 2, s // 2

    # Draw a bold pincer / crab claw shape:
    # Two thick crescents curving outward and up, meeting at a base

    # Left claw — thick crescent (outer ellipse minus inner ellipse)
    # Outer: large ellipse offset left
    draw.pieslice([8, 12, cx + 8, s - 16], start=220, end=350, fill=claw)
    # Hollow out the inner part to make it a crescent
    draw.pieslice([20, 24, cx - 2, s - 28], start=210, end=355, fill=bg_rgb)

    # Right claw — mirror
    draw.pieslice([cx - 8, 12, s - 8, s - 16], start=190, end=320, fill=claw)
    draw.pieslice([cx + 2, 24, s - 20, s - 28], start=185, end=330, fill=bg_rgb)

    # Claw tips — rounded dots at the top ends of each crescent
    draw.ellipse([18, 16, 34, 32], fill=claw)  # Left tip
    draw.ellipse([s - 34, 16, s - 18, 32], fill=claw)  # Right tip

    # Base connector — rounded rectangle joining the two claws at bottom
    base_y = cy + 14
    draw.rounded_rectangle(
        [cx - 20, base_y, cx + 20, base_y + 22],
        radius=8, fill=claw,
    )

    # Downsample to final size with anti-aliasing
    img = img.resize((ICON_SIZE, ICON_SIZE), resample=Image.LANCZOS)
    return img


class TrayIcon:
    """System tray icon powered by pystray."""

    def __init__(
        self,
        state: SharedState,
        on_show_details=None,
        on_show_settings=None,
        on_toggle_autostart=None,
        on_exit=None,
        get_autostart_state=None,
    ) -> None:
        self._state = state
        self._on_show_details = on_show_details
        self._on_show_settings = on_show_settings
        self._on_toggle_autostart = on_toggle_autostart
        self._on_exit = on_exit
        self._get_autostart_state = get_autostart_state
        self._icon: pystray.Icon | None = None
        self._current_color = COLOR_ACCENT

        # Register for state updates
        self._state.on_change(self._on_data_change)

    def start(self) -> None:
        """Start the tray icon in a background thread."""
        menu = pystray.Menu(
            pystray.MenuItem("Show Details", self._handle_show_details, default=True),
            pystray.MenuItem("Settings...", self._handle_show_settings),
            pystray.MenuItem(
                "Start with Windows",
                self._handle_toggle_autostart,
                checked=lambda item: self._get_autostart_state() if self._get_autostart_state else False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._handle_exit),
        )

        self._icon = pystray.Icon(
            name="pinch",
            icon=_create_icon_image(self._current_color),
            title=f"{APP_NAME}: Loading...",
            menu=menu,
        )

        thread = threading.Thread(target=self._icon.run, daemon=True, name="TrayIcon")
        thread.start()
        log.info("Tray icon started")

    def stop(self) -> None:
        """Stop the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
        log.info("Tray icon stopped")

    def _on_data_change(self, data: UsageData) -> None:
        """Update icon color and tooltip when data changes."""
        if not self._icon:
            return

        if data.error:
            tooltip = f"{APP_NAME}: Error - {data.error}"
            new_color = "#f38ba8"
        else:
            five = data.five_hour.utilization
            week = data.seven_day.utilization
            tooltip = f"{APP_NAME}\n5h: {pct_str(five)} | Week: {pct_str(week)}"
            # Icon color based on the more urgent metric
            new_color = color_for_utilization(max(five, week))

        try:
            self._icon.title = tooltip
            if new_color != self._current_color:
                self._current_color = new_color
                self._icon.icon = _create_icon_image(new_color)
        except Exception as exc:
            log.debug("Tray update error: %s", exc)

    def _handle_show_details(self, icon=None, item=None) -> None:
        if self._on_show_details:
            self._on_show_details()

    def _handle_show_settings(self, icon=None, item=None) -> None:
        if self._on_show_settings:
            self._on_show_settings()

    def _handle_toggle_autostart(self, icon=None, item=None) -> None:
        if self._on_toggle_autostart:
            self._on_toggle_autostart()

    def _handle_exit(self, icon=None, item=None) -> None:
        if self._on_exit:
            self._on_exit()
