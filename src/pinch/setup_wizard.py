"""First-run setup wizard — OAuth-only auto-detection.

SECURITY MODEL:
- NO credential entry fields. No API keys accepted or stored.
- OAuth token is read from Claude Code's file and tested, never displayed.
- Wizard only saves display preferences (poll_interval, autostart, theme).

THREADING MODEL:
Uses queue-based thread communication instead of root.after()
because root.after() throws RuntimeError when called from a thread while
wait_window() is active on the main loop.
"""

import logging
import queue
import tkinter as tk
from threading import Thread

from .auth import has_oauth_credentials, test_connection
from .config import APP_NAME, APP_TAGLINE, COLOR_TEXT, COLOR_TEXT_DIM, FONT_FAMILY
from . import settings

log = logging.getLogger(__name__)

WIZARD_WIDTH = 440
WIZARD_HEIGHT = 340
WIZARD_BG = "#12131e"
WIZARD_SURFACE = "#1a1b2e"
WIZARD_BORDER = "#2a2b3d"
WIZARD_RADIUS = 16
TRANSPARENT_COLOR = "#ff00ff"

# Button states
BTN_IDLE = "#e06c75"
BTN_HOVER = "#e8838b"
BTN_PRESS = "#c75a63"
BTN_SUCCESS = "#a6e3a1"
BTN_DISABLED = "#45475a"

# Spinner frames for loading animation
SPINNER_FRAMES = ["\u25dc", "\u25dd", "\u25de", "\u25df"]


def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    """Draw a rounded rectangle on a canvas."""
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class SetupWizard:
    """First-run wizard — detects OAuth credentials and verifies connection."""

    def __init__(self, root: tk.Tk, on_complete=None) -> None:
        self._root = root
        self._on_complete = on_complete
        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._result_settings: dict | None = None
        self._msg_queue: queue.Queue = queue.Queue()
        self._spinner_idx = 0
        self._spinner_active = False
        self._btn_rect_id: int | None = None
        self._btn_text_id: int | None = None

    def run(self) -> dict | None:
        """Show the wizard and return settings when complete."""
        self._win = tk.Toplevel(self._root)
        self._win.title(f"{APP_NAME} Setup")
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self._win.configure(bg=TRANSPARENT_COLOR)

        # Center on screen
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = (screen_w - WIZARD_WIDTH) // 2
        y = (screen_h - WIZARD_HEIGHT) // 2
        self._win.geometry(f"{WIZARD_WIDTH}x{WIZARD_HEIGHT}+{x}+{y}")

        self._canvas = tk.Canvas(
            self._win, width=WIZARD_WIDTH, height=WIZARD_HEIGHT,
            highlightthickness=0, bd=0, bg=TRANSPARENT_COLOR,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Draw outer shell
        self._draw_background()

        # Detect OAuth and show appropriate screen
        has_oauth = has_oauth_credentials()
        if has_oauth:
            self._show_oauth_detected()
        else:
            self._show_no_oauth()

        # Start polling the message queue
        self._poll_queue()

        self._win.focus_set()
        self._win.grab_set()
        self._root.wait_window(self._win)

        return self._result_settings

    # ── Drawing helpers ──────────────────────────────────────────────

    def _draw_background(self) -> None:
        """Draw the outer rounded window background."""
        c = self._canvas
        _round_rect(c, 0, 0, WIZARD_WIDTH - 1, WIZARD_HEIGHT - 1,
                     WIZARD_RADIUS + 1, fill=WIZARD_BORDER, outline="")
        _round_rect(c, 1, 1, WIZARD_WIDTH - 2, WIZARD_HEIGHT - 2,
                     WIZARD_RADIUS, fill=WIZARD_BG, outline="")
        _round_rect(c, 20, 20, WIZARD_WIDTH - 20, WIZARD_HEIGHT - 20,
                     12, fill=WIZARD_SURFACE, outline=WIZARD_BORDER, width=1)

    def _draw_button(self, x: int, y: int, w: int, h: int, text: str,
                     color: str = BTN_IDLE, text_color: str = "#1e1e2e",
                     tag: str = "btn_main") -> tuple[int, int]:
        """Draw a rounded button with hover/press states."""
        c = self._canvas
        rect_id = _round_rect(c, x, y, x + w, y + h, 10,
                               fill=color, outline="", tags=tag)
        text_id = c.create_text(
            x + w // 2, y + h // 2, text=text,
            font=(FONT_FAMILY, 10, "bold"), fill=text_color,
            anchor="center", tags=tag,
        )

        def on_enter(e):
            if c.itemcget(rect_id, "fill") not in (BTN_DISABLED, BTN_SUCCESS):
                c.itemconfig(rect_id, fill=BTN_HOVER)

        def on_leave(e):
            if c.itemcget(rect_id, "fill") not in (BTN_DISABLED, BTN_SUCCESS):
                c.itemconfig(rect_id, fill=color)

        def on_press(e):
            if c.itemcget(rect_id, "fill") not in (BTN_DISABLED, BTN_SUCCESS):
                c.itemconfig(rect_id, fill=BTN_PRESS)

        def on_release(e):
            if c.itemcget(rect_id, "fill") not in (BTN_DISABLED, BTN_SUCCESS):
                c.itemconfig(rect_id, fill=BTN_HOVER)

        c.tag_bind(tag, "<Enter>", on_enter)
        c.tag_bind(tag, "<Leave>", on_leave)
        c.tag_bind(tag, "<ButtonPress-1>", on_press)
        c.tag_bind(tag, "<ButtonRelease-1>", on_release)

        return rect_id, text_id

    # ── Thread-safe messaging ────────────────────────────────────────

    def _poll_queue(self) -> None:
        """Poll the message queue for thread results. Runs on main thread."""
        if not self._win or not self._win.winfo_exists():
            return
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                handler = msg.get("handler")
                if handler:
                    handler(**msg.get("kwargs", {}))
        except queue.Empty:
            pass
        self._win.after(50, self._poll_queue)

    def _post(self, handler, **kwargs) -> None:
        """Thread-safe: post a message to the main thread."""
        self._msg_queue.put({"handler": handler, "kwargs": kwargs})

    # ── Spinner animation ────────────────────────────────────────────

    def _start_spinner(self) -> None:
        self._spinner_active = True
        self._animate_spinner()

    def _stop_spinner(self) -> None:
        self._spinner_active = False

    def _animate_spinner(self) -> None:
        if not self._spinner_active or not self._win or not self._win.winfo_exists():
            return
        self._spinner_idx = (self._spinner_idx + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self._spinner_idx]
        if hasattr(self, '_status_id'):
            current_text = self._canvas.itemcget(self._status_id, "text")
            if current_text and current_text[0] in SPINNER_FRAMES:
                self._canvas.itemconfig(self._status_id, text=frame + current_text[1:])
            else:
                self._canvas.itemconfig(self._status_id, text=frame + " " + current_text)
        self._win.after(120, self._animate_spinner)

    # ── OAuth detected screen ────────────────────────────────────────

    def _show_oauth_detected(self) -> None:
        """OAuth credentials found — offer auto-connect."""
        c = self._canvas
        cx = WIZARD_WIDTH // 2

        c.create_text(
            cx, 50, text=APP_NAME,
            font=(FONT_FAMILY, 18, "bold"),
            fill=COLOR_TEXT, anchor="center",
        )

        c.create_text(
            cx, 75, text=APP_TAGLINE,
            font=(FONT_FAMILY, 9, "italic"),
            fill=COLOR_TEXT_DIM, anchor="center",
        )

        c.create_line(50, 100, WIZARD_WIDTH - 50, 100, fill=WIZARD_BORDER, width=1)

        # Detection badge
        badge_w, badge_h = 220, 32
        badge_x = (WIZARD_WIDTH - badge_w) // 2
        badge_y = 118
        _round_rect(c, badge_x, badge_y, badge_x + badge_w, badge_y + badge_h,
                     8, fill="#1e3a2a", outline="#2d5a3e", width=1)
        c.create_text(
            cx, badge_y + badge_h // 2,
            text="\u2713  Claude Code Detected",
            font=(FONT_FAMILY, 10, "bold"),
            fill="#a6e3a1", anchor="center",
        )

        c.create_text(
            cx, 175,
            text="Found OAuth session. No credentials are stored by Pinch.",
            font=(FONT_FAMILY, 8),
            fill=COLOR_TEXT_DIM, anchor="center",
        )

        c.create_text(
            cx, 198,
            text="Click below to verify your connection and start monitoring.",
            font=(FONT_FAMILY, 9),
            fill=COLOR_TEXT, anchor="center",
        )

        # Status area
        self._status_id = c.create_text(
            cx, 238, text="",
            font=(FONT_FAMILY, 9),
            fill=COLOR_TEXT_DIM, anchor="center",
        )

        # Auto-Connect button
        btn_w, btn_h = 180, 42
        btn_x = (WIZARD_WIDTH - btn_w) // 2
        btn_y = 260
        self._btn_rect_id, self._btn_text_id = self._draw_button(
            btn_x, btn_y, btn_w, btn_h, "Auto-Connect",
        )
        self._canvas.tag_bind("btn_main", "<ButtonRelease-1>",
                              lambda e: self._test_oauth())

    # ── No OAuth screen ──────────────────────────────────────────────

    def _show_no_oauth(self) -> None:
        """No OAuth credentials — inform user to install Claude Code."""
        c = self._canvas
        cx = WIZARD_WIDTH // 2

        c.create_text(
            cx, 50, text=APP_NAME,
            font=(FONT_FAMILY, 18, "bold"),
            fill=COLOR_TEXT, anchor="center",
        )

        c.create_text(
            cx, 75, text=APP_TAGLINE,
            font=(FONT_FAMILY, 9, "italic"),
            fill=COLOR_TEXT_DIM, anchor="center",
        )

        c.create_line(50, 100, WIZARD_WIDTH - 50, 100, fill=WIZARD_BORDER, width=1)

        # Warning badge
        badge_w, badge_h = 260, 32
        badge_x = (WIZARD_WIDTH - badge_w) // 2
        badge_y = 118
        _round_rect(c, badge_x, badge_y, badge_x + badge_w, badge_y + badge_h,
                     8, fill="#3a2a1e", outline="#5a3e2d", width=1)
        c.create_text(
            cx, badge_y + badge_h // 2,
            text="\u26A0  Claude Code Not Found",
            font=(FONT_FAMILY, 10, "bold"),
            fill="#f9e2af", anchor="center",
        )

        c.create_text(
            cx, 178,
            text="Pinch requires Claude Code to be installed and\n"
                 "logged in. It reads your OAuth session to monitor\n"
                 "usage — no credentials are stored by Pinch.",
            font=(FONT_FAMILY, 9),
            fill=COLOR_TEXT, anchor="center", justify="center",
        )

        c.create_text(
            cx, 230,
            text="Install Claude Code, log in, then relaunch Pinch.",
            font=(FONT_FAMILY, 8),
            fill=COLOR_TEXT_DIM, anchor="center",
        )

        # Status area
        self._status_id = c.create_text(
            cx, 258, text="",
            font=(FONT_FAMILY, 9),
            fill=COLOR_TEXT_DIM, anchor="center",
        )

        # Retry button
        btn_w, btn_h = 140, 42
        btn_x = (WIZARD_WIDTH - btn_w) // 2
        btn_y = 275
        self._btn_rect_id, self._btn_text_id = self._draw_button(
            btn_x, btn_y, btn_w, btn_h, "Retry",
        )
        self._canvas.tag_bind("btn_main", "<ButtonRelease-1>",
                              lambda e: self._retry_detect())

    # ── Actions ──────────────────────────────────────────────────────

    def _retry_detect(self) -> None:
        """Re-check for OAuth credentials."""
        if has_oauth_credentials():
            self._canvas.delete("all")
            self._draw_background()
            self._show_oauth_detected()
        else:
            self._canvas.itemconfig(self._status_id,
                                    text="Still not found. Install Claude Code first.",
                                    fill="#f38ba8")

    def _disable_button(self) -> None:
        if self._btn_rect_id:
            self._canvas.itemconfig(self._btn_rect_id, fill=BTN_DISABLED)

    def _test_oauth(self) -> None:
        """Test OAuth connection in a background thread."""
        self._disable_button()
        self._canvas.itemconfig(self._status_id,
                                text="\u25dc  Connecting...", fill="#f9e2af")
        self._start_spinner()

        def _do_test():
            try:
                success, msg = test_connection()
            except Exception as exc:
                success, msg = False, str(exc)
            self._post(self._on_test_result, success=success, msg=msg)

        Thread(target=_do_test, daemon=True).start()

    def _on_test_result(self, success: bool, msg: str) -> None:
        """Handle test result — runs on main thread via queue."""
        self._stop_spinner()

        if success:
            self._canvas.itemconfig(self._status_id,
                                    text=f"\u2713  {msg}", fill="#a6e3a1")

            if self._btn_rect_id:
                self._canvas.itemconfig(self._btn_rect_id, fill=BTN_SUCCESS)
            if self._btn_text_id:
                self._canvas.itemconfig(self._btn_text_id,
                                        text="\u2713  Connected!", fill="#1e3a2a")

            # Save display-only settings (no credentials)
            s = dict(settings.DEFAULTS)
            settings.save(s)
            self._result_settings = s

            self._countdown(3)
        else:
            self._canvas.itemconfig(self._status_id,
                                    text=f"\u2717  {msg}", fill="#f38ba8")
            if self._btn_rect_id:
                self._canvas.itemconfig(self._btn_rect_id, fill=BTN_IDLE)
            if self._btn_text_id:
                self._canvas.itemconfig(self._btn_text_id,
                                        text="Auto-Connect", fill="#1e1e2e")

    def _countdown(self, seconds: int) -> None:
        if not self._win or not self._win.winfo_exists():
            return
        if seconds <= 0:
            self._finish()
            return
        self._canvas.itemconfig(self._status_id,
                                text=f"\u2713  Launching in {seconds}s...",
                                fill="#a6e3a1")
        self._win.after(1000, self._countdown, seconds - 1)

    def _finish(self) -> None:
        if self._win:
            try:
                self._win.grab_release()
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None
        if self._on_complete:
            self._on_complete(self._result_settings)
