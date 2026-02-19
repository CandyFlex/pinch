"""Frameless tkinter window that sits on the Windows taskbar — rounded pill design."""

import ctypes
import ctypes.wintypes
import logging
import tkinter as tk

from .config import (
    FONT_FAMILY, FONT_SIZE_OVERLAY, OVERLAY_HEIGHT, OVERLAY_MIN_WIDTH,
    TASKBAR_REPOSITION_SECONDS, color_for_utilization,
)
from .shared_state import SharedState, UsageData
from .theme import get_taskbar_color, get_taskbar_text_color
from .utils import pct_str, compact_countdown

log = logging.getLogger(__name__)

# Windows constants
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
GA_ROOT = 2  # GetAncestor: top-level owner window

# Visibility recovery
SW_SHOWNOACTIVATE = 8

# Fast z-order reassertion interval (ms) — separate from the
# slower reposition loop so we recover quickly from fullscreen apps
TOPMOST_CHECK_MS = 500

# Transparent color key for rounded corners
TRANSPARENT_COLOR = "#ff00ff"

# Pill styling
PILL_BG = "#1e1e2e"
PILL_BORDER = "#45475a"
PILL_RADIUS = 10
PILL_PAD_X = 10
PILL_PAD_Y = 3


def _find_taskbar_rect() -> tuple[int, int, int, int] | None:
    """Find the Windows taskbar bounding rect: (left, top, right, bottom)."""
    user32 = ctypes.windll.user32
    taskbar = user32.FindWindowW("Shell_TrayWnd", None)
    if not taskbar:
        return None
    rect = ctypes.wintypes.RECT()
    if user32.GetWindowRect(taskbar, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def _find_tray_rect() -> tuple[int, int, int, int] | None:
    """Find the system tray notification area bounding rect."""
    user32 = ctypes.windll.user32
    taskbar = user32.FindWindowW("Shell_TrayWnd", None)
    if not taskbar:
        return None
    tray = user32.FindWindowExW(taskbar, None, "TrayNotifyWnd", None)
    if not tray:
        return None
    rect = ctypes.wintypes.RECT()
    if user32.GetWindowRect(tray, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    """Draw a rounded rectangle on a canvas."""
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class TaskbarOverlay:
    """Rounded pill overlay on the taskbar showing usage at a glance.

    Layout: [5h 42% \u00b7 resets 2h14m | Weekly 29%]
    """

    def __init__(self, root: tk.Tk, state: SharedState, on_click=None) -> None:
        self._root = root
        self._state = state
        self._on_click = on_click
        self._alive = True  # set False on destroy to stop all callbacks

        # Frameless, topmost, transparent background for rounded corners
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self._root.configure(bg=TRANSPARENT_COLOR)

        # Make it a tool window (hidden from Alt-Tab)
        self._root.update_idletasks()
        self._hwnd = self._acquire_hwnd()
        log.info("Overlay HWND: 0x%X", self._hwnd)
        if self._hwnd:
            style = ctypes.windll.user32.GetWindowLongW(self._hwnd, GWL_EXSTYLE)
            style = style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongW(self._hwnd, GWL_EXSTYLE, style)

        # Canvas for the rounded pill
        self._canvas = tk.Canvas(
            self._root,
            highlightthickness=0,
            bd=0,
            bg=TRANSPARENT_COLOR,
            cursor="hand2",
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Button-1>", self._handle_click)

        # Display state
        self._five_pct_text = "--%"
        self._five_reset_text = ""
        self._wk_text = "Weekly --%"
        self._five_color = "#6c7086"
        self._wk_color = "#6c7086"

        # Cache last data for countdown refresh
        self._last_data: UsageData | None = None

        # Register for state changes
        self._state.on_change(self._on_data_change)

        # Initial draw + position
        self._root.after(50, self._initial_draw)

        # Periodic reposition
        self._root.after(TASKBAR_REPOSITION_SECONDS * 1000, self._reposition_loop)

        # Countdown refresh every 30s so the timer stays current
        self._root.after(30_000, self._refresh_countdown)

    def _acquire_hwnd(self) -> int:
        """Reliably get the Win32 HWND for this overlay window."""
        user32 = ctypes.windll.user32
        frame_id = self._root.winfo_id()

        # Best: GetAncestor with GA_ROOT returns the actual top-level window
        hwnd = user32.GetAncestor(frame_id, GA_ROOT)
        if hwnd:
            return hwnd

        # Fallback: GetParent
        hwnd = user32.GetParent(frame_id)
        if hwnd:
            return hwnd

        # Last resort: the frame id itself
        return frame_id

    def _initial_draw(self) -> None:
        self._draw_pill()
        self._position_on_taskbar()

        # Re-acquire HWND after window is fully realized (sometimes
        # the HWND changes after the first geometry call)
        new_hwnd = self._acquire_hwnd()
        if new_hwnd != self._hwnd:
            log.info("HWND updated after draw: 0x%X -> 0x%X", self._hwnd, new_hwnd)
            self._hwnd = new_hwnd

        # Start fast topmost check loop (500ms) — recovers quickly
        # when fullscreen apps demote our z-order
        self._root.after(TOPMOST_CHECK_MS, self._topmost_loop)

    def _handle_click(self, event=None) -> None:
        if self._on_click:
            self._on_click()

    def _on_data_change(self, data: UsageData) -> None:
        """Called from the monitor thread — schedule UI update on main thread."""
        if not self._alive:
            return
        try:
            self._root.after(0, self._update_display, data)
        except tk.TclError:
            pass

    def _refresh_countdown(self) -> None:
        """Periodically refresh the countdown text without a full API poll."""
        if not self._alive:
            return
        if self._last_data and not self._last_data.error:
            self._update_display(self._last_data)
        try:
            self._root.after(30_000, self._refresh_countdown)
        except tk.TclError:
            pass

    def _update_display(self, data: UsageData) -> None:
        """Update the overlay text and colors."""
        self._last_data = data

        if data.error:
            self._five_pct_text = "ERR"
            self._five_reset_text = ""
            self._wk_text = "Weekly ERR"
            self._five_color = "#f38ba8"
            self._wk_color = "#f38ba8"
        else:
            five_pct = data.five_hour.utilization
            week_pct = data.seven_day.utilization

            self._five_pct_text = pct_str(five_pct)
            self._five_color = color_for_utilization(five_pct)

            # Countdown for the 5-hour reset
            countdown = compact_countdown(data.five_hour.resets_at)
            self._five_reset_text = f"\u21bb {countdown}" if countdown else ""

            self._wk_text = f"Weekly {pct_str(week_pct)}"
            self._wk_color = color_for_utilization(week_pct)

        self._draw_pill()

    def _draw_pill(self) -> None:
        """Redraw the pill: [5h 42% \u21bb2h14m \u2502 Weekly 29%]"""
        c = self._canvas
        c.delete("all")

        bold_font = (FONT_FAMILY, FONT_SIZE_OVERLAY, "bold")
        dim_font = (FONT_FAMILY, FONT_SIZE_OVERLAY - 1)
        sep_font = (FONT_FAMILY, FONT_SIZE_OVERLAY - 1)

        # Measure each segment
        segments = []  # list of (text, font, color)

        # 5h percentage
        segments.append((self._five_pct_text, bold_font, self._five_color))

        # Reset countdown (dimmed, tight spacing)
        if self._five_reset_text:
            segments.append((" ", dim_font, "#585b70"))
            segments.append((self._five_reset_text, dim_font, "#7f849c"))

        # Separator
        segments.append(("  \u2502  ", sep_font, "#45475a"))

        # Weekly percentage
        segments.append((self._wk_text, bold_font, self._wk_color))

        # Measure all segments
        widths = []
        max_h = 14
        for text, font, _ in segments:
            tid = c.create_text(0, 0, text=text, font=font, anchor="nw")
            bb = c.bbox(tid)
            c.delete(tid)
            w = (bb[2] - bb[0]) if bb else 10
            h = (bb[3] - bb[1]) if bb else 14
            widths.append(w)
            max_h = max(max_h, h)

        total_text_w = sum(widths)
        pill_w = total_text_w + PILL_PAD_X * 2
        pill_h = max_h + PILL_PAD_Y * 2 + 2

        # Resize window
        win_w = max(int(pill_w) + 4, OVERLAY_MIN_WIDTH)
        win_h = max(int(pill_h) + 4, OVERLAY_HEIGHT)
        self._pill_w = win_w
        self._pill_h = win_h
        c.config(width=win_w, height=win_h)

        # Draw pill background
        px = (win_w - pill_w) / 2
        py = (win_h - pill_h) / 2
        _round_rect(c, px, py, px + pill_w, py + pill_h, PILL_RADIUS,
                    fill=PILL_BG, outline=PILL_BORDER, width=1)

        # Draw segments left-to-right
        center_y = win_h / 2
        cursor_x = (win_w - total_text_w) / 2

        for i, (text, font, color) in enumerate(segments):
            c.create_text(cursor_x, center_y, text=text, font=font,
                          fill=color, anchor="w")
            cursor_x += widths[i]

    def _position_on_taskbar(self) -> None:
        """Position the overlay window on the taskbar, left of the system tray."""
        taskbar_rect = _find_taskbar_rect()
        tray_rect = _find_tray_rect()

        w = getattr(self, '_pill_w', OVERLAY_MIN_WIDTH)
        h = getattr(self, '_pill_h', OVERLAY_HEIGHT)

        if not taskbar_rect:
            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            self._root.geometry(f"{w}x{h}+{screen_w - 300}+{screen_h - 40}")
            return

        tb_left, tb_top, tb_right, tb_bottom = taskbar_rect
        tb_height = tb_bottom - tb_top

        if tray_rect:
            tray_left = tray_rect[0]
            x = tray_left - w - 4
        else:
            x = tb_right - w - 200

        y = tb_top + (tb_height - h) // 2
        self._root.geometry(f"{w}x{h}+{x}+{y}")

    def _topmost_loop(self) -> None:
        """Fast loop that re-asserts TOPMOST z-order every 500ms.

        Recovers quickly when fullscreen apps (Chrome, games) demote
        the overlay. Pure tkinter — no ctypes callbacks that can crash.
        """
        if not self._alive:
            return
        try:
            self._force_topmost()
        except Exception as exc:
            log.debug("Topmost check error: %s", exc)
        try:
            self._root.after(TOPMOST_CHECK_MS, self._topmost_loop)
        except tk.TclError:
            pass

    def destroy(self) -> None:
        """Stop all periodic callbacks."""
        self._alive = False

    def _force_topmost(self) -> None:
        """Force the window back to TOPMOST z-order via Win32 API.

        tkinter's -topmost can be demoted by fullscreen apps (Chrome, games).
        This directly calls SetWindowPos to re-assert topmost every cycle,
        checks IsWindowVisible and forces show if the window got hidden,
        and re-applies tkinter's topmost as belt-and-suspenders.
        """
        if not self._alive:
            return

        hwnd = self._hwnd
        if not hwnd:
            hwnd = self._acquire_hwnd()
            if hwnd:
                self._hwnd = hwnd
                log.info("Re-acquired HWND: 0x%X", hwnd)

        if hwnd:
            user32 = ctypes.windll.user32

            # If the window got hidden, force it visible
            if not user32.IsWindowVisible(hwnd):
                log.debug("Overlay hidden — forcing ShowWindow")
                user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

            # Re-assert TOPMOST z-order
            user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )

        # Belt and suspenders: re-apply tkinter topmost + ensure visible
        try:
            self._root.deiconify()
            self._root.attributes("-topmost", True)
            self._root.lift()
        except tk.TclError:
            pass

    def _reposition_loop(self) -> None:
        """Periodically re-check taskbar position and force z-order."""
        if not self._alive:
            return
        try:
            self._position_on_taskbar()
            self._force_topmost()
        except Exception as exc:
            log.debug("Reposition error: %s", exc)
        try:
            self._root.after(TASKBAR_REPOSITION_SECONDS * 1000, self._reposition_loop)
        except tk.TclError:
            pass  # window destroyed during shutdown
