"""Settings window — accessed from tray menu 'Settings...'.

SECURITY MODEL:
- NO credential fields. No API keys, no tokens, no auth mode selection.
- Only display preferences: poll interval, auto-start, theme.
- Connection test reads OAuth live from Claude Code's file — never stored.
"""

import logging
import queue
import tkinter as tk
from threading import Thread

from .auth import test_connection
from .config import APP_NAME, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM, FONT_FAMILY
from . import settings

log = logging.getLogger(__name__)

WIN_W = 360
WIN_H = 380
BG = "#1a1b2e"
SURFACE = "#12131e"
BORDER = "#2a2b3d"
RADIUS = 14
TRANSPARENT = "#ff00ff"
INPUT_BG = "#11111b"
BTN_BG = "#313244"
BTN_HOVER = "#45475a"
BTN_PRESS = "#585b70"
ACCENT = COLOR_ACCENT
ACCENT_HOVER = "#e8838b"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"

POLL_OPTIONS = [
    ("15s", 15),
    ("30s", 30),
    ("60s", 60),
    ("2 min", 120),
]


def _rr(c: tk.Canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle."""
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return c.create_polygon(pts, smooth=True, **kw)


class SettingsUI:
    """Canvas-based settings window — polished dark theme."""

    def __init__(self, root: tk.Tk, on_settings_changed=None) -> None:
        self._root = root
        self._on_settings_changed = on_settings_changed
        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._msg_queue: queue.Queue = queue.Queue()
        self._poll_idx = 1  # default 30s
        self._autostart = False

    @property
    def is_visible(self) -> bool:
        return self._win is not None and self._win.winfo_exists()

    def show(self) -> None:
        if self.is_visible:
            self._win.lift()
            self._win.focus_set()
            return

        self._win = tk.Toplevel(self._root)
        self._win.title(f"{APP_NAME} Settings")
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-transparentcolor", TRANSPARENT)
        self._win.configure(bg=TRANSPARENT)

        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = (screen_w - WIN_W) // 2
        y = (screen_h - WIN_H) // 2
        self._win.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        self._s = settings.load()
        self._poll_idx = next(
            (i for i, (_, v) in enumerate(POLL_OPTIONS) if v == self._s.get("poll_interval", 30)),
            1,
        )
        self._autostart = self._s.get("autostart", False)

        self._build()
        self._poll_queue()
        self._win.bind("<Escape>", lambda e: self.hide())
        self._win.focus_set()

    def hide(self) -> None:
        if self._win:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None

    # ── Build ────────────────────────────────────────────────────────

    def _build(self) -> None:
        c = tk.Canvas(
            self._win, width=WIN_W, height=WIN_H,
            highlightthickness=0, bd=0, bg=TRANSPARENT,
        )
        c.pack(fill=tk.BOTH, expand=True)
        self._canvas = c

        # Outer border glow + background
        _rr(c, 0, 0, WIN_W - 1, WIN_H - 1, RADIUS + 1, fill=BORDER, outline="")
        _rr(c, 1, 1, WIN_W - 2, WIN_H - 2, RADIUS, fill=BG, outline="")

        # Title bar
        c.create_text(24, 28, text=f"{APP_NAME} Settings",
                       font=(FONT_FAMILY, 13, "bold"), fill=COLOR_TEXT, anchor="w")

        # Close X button with hover
        close_id = c.create_text(WIN_W - 24, 28, text="\u2715",
                                  font=(FONT_FAMILY, 11), fill="#585b70", anchor="e")
        c.tag_bind(close_id, "<Enter>", lambda e: c.itemconfig(close_id, fill=RED))
        c.tag_bind(close_id, "<Leave>", lambda e: c.itemconfig(close_id, fill="#585b70"))
        c.tag_bind(close_id, "<Button-1>", lambda e: self.hide())

        c.create_line(20, 52, WIN_W - 20, 52, fill=BORDER, width=1)

        # ── Connection Section ──
        y = 70
        c.create_text(24, y, text="CONNECTION",
                       font=(FONT_FAMILY, 8, "bold"), fill="#585b70", anchor="w")
        y += 22

        # OAuth status badge
        _rr(c, 24, y, WIN_W - 24, y + 30, 8, fill=SURFACE, outline=BORDER, width=1)
        c.create_text(36, y + 15, text="\u2713  OAuth via Claude Code",
                       font=(FONT_FAMILY, 9), fill=GREEN, anchor="w")
        y += 42

        # Test Connection button
        self._test_btn_id = _rr(c, 24, y, 160, y + 32, 8, fill=BTN_BG, outline="")
        self._test_txt_id = c.create_text(92, y + 16, text="Test Connection",
                                           font=(FONT_FAMILY, 9, "bold"), fill=COLOR_TEXT, anchor="center")
        self._test_status_id = c.create_text(170, y + 16, text="",
                                              font=(FONT_FAMILY, 8), fill=COLOR_TEXT_DIM, anchor="w")

        for tid in (self._test_btn_id, self._test_txt_id):
            c.tag_bind(tid, "<Enter>", lambda e: c.itemconfig(self._test_btn_id, fill=BTN_HOVER))
            c.tag_bind(tid, "<Leave>", lambda e: c.itemconfig(self._test_btn_id, fill=BTN_BG))
            c.tag_bind(tid, "<ButtonPress-1>", lambda e: c.itemconfig(self._test_btn_id, fill=BTN_PRESS))
            c.tag_bind(tid, "<ButtonRelease-1>", lambda e: self._test_connection())
        y += 48

        c.create_line(20, y, WIN_W - 20, y, fill=BORDER, width=1)
        y += 16

        # ── Poll Interval Section ──
        c.create_text(24, y, text="POLL INTERVAL",
                       font=(FONT_FAMILY, 8, "bold"), fill="#585b70", anchor="w")
        y += 24

        # Segmented control for poll interval
        seg_x = 24
        seg_w = (WIN_W - 48) // len(POLL_OPTIONS)
        seg_h = 32
        self._seg_items = []
        for i, (label, _) in enumerate(POLL_OPTIONS):
            sx = seg_x + i * seg_w
            is_sel = (i == self._poll_idx)
            fill = ACCENT if is_sel else SURFACE
            text_fill = "#1e1e2e" if is_sel else COLOR_TEXT_DIM

            rid = _rr(c, sx + 1, y, sx + seg_w - 1, y + seg_h, 6,
                       fill=fill, outline=BORDER, width=1)
            tid = c.create_text(sx + seg_w // 2, y + seg_h // 2, text=label,
                                 font=(FONT_FAMILY, 9, "bold"), fill=text_fill, anchor="center")
            self._seg_items.append((rid, tid, i))

            idx = i  # capture
            for item in (rid, tid):
                c.tag_bind(item, "<Button-1>", lambda e, idx=idx: self._select_poll(idx))
                c.tag_bind(item, "<Enter>", lambda e, rid=rid, idx=idx: (
                    c.itemconfig(rid, fill=ACCENT_HOVER) if idx == self._poll_idx
                    else c.itemconfig(rid, fill=BTN_HOVER)
                ))
                c.tag_bind(item, "<Leave>", lambda e, rid=rid, idx=idx: (
                    c.itemconfig(rid, fill=ACCENT) if idx == self._poll_idx
                    else c.itemconfig(rid, fill=SURFACE)
                ))
        y += seg_h + 20

        c.create_line(20, y, WIN_W - 20, y, fill=BORDER, width=1)
        y += 16

        # ── Startup Section ──
        c.create_text(24, y, text="STARTUP",
                       font=(FONT_FAMILY, 8, "bold"), fill="#585b70", anchor="w")
        y += 24

        # Custom toggle switch for autostart
        self._toggle_x = 24
        self._toggle_y = y
        self._draw_toggle(c, y)

        c.create_text(68, y + 12, text="Start with Windows",
                       font=(FONT_FAMILY, 9), fill=COLOR_TEXT, anchor="w")
        y += 44

        c.create_line(20, y, WIN_W - 20, y, fill=BORDER, width=1)
        y += 20

        # ── Save / Cancel ──
        btn_w, btn_h = 110, 36

        # Save button (accent)
        save_x = WIN_W - 24 - btn_w
        self._save_bg = _rr(c, save_x, y, save_x + btn_w, y + btn_h, 8,
                             fill=ACCENT, outline="")
        self._save_txt = c.create_text(save_x + btn_w // 2, y + btn_h // 2,
                                        text="Save", font=(FONT_FAMILY, 10, "bold"),
                                        fill="#1e1e2e", anchor="center")
        for tid in (self._save_bg, self._save_txt):
            c.tag_bind(tid, "<Enter>", lambda e: c.itemconfig(self._save_bg, fill=ACCENT_HOVER))
            c.tag_bind(tid, "<Leave>", lambda e: c.itemconfig(self._save_bg, fill=ACCENT))
            c.tag_bind(tid, "<ButtonPress-1>", lambda e: c.itemconfig(self._save_bg, fill="#c75a63"))
            c.tag_bind(tid, "<ButtonRelease-1>", lambda e: self._save())

        # Cancel button
        cancel_x = save_x - btn_w - 10
        self._cancel_bg = _rr(c, cancel_x, y, cancel_x + btn_w, y + btn_h, 8,
                               fill=BTN_BG, outline="")
        self._cancel_txt = c.create_text(cancel_x + btn_w // 2, y + btn_h // 2,
                                          text="Cancel", font=(FONT_FAMILY, 10, "bold"),
                                          fill=COLOR_TEXT, anchor="center")
        for tid in (self._cancel_bg, self._cancel_txt):
            c.tag_bind(tid, "<Enter>", lambda e: c.itemconfig(self._cancel_bg, fill=BTN_HOVER))
            c.tag_bind(tid, "<Leave>", lambda e: c.itemconfig(self._cancel_bg, fill=BTN_BG))
            c.tag_bind(tid, "<Button-1>", lambda e: self.hide())

    # ── Toggle switch ────────────────────────────────────────────────

    def _draw_toggle(self, c: tk.Canvas, y: int) -> None:
        """Draw a custom on/off toggle switch."""
        # Delete old toggle items
        c.delete("toggle")
        x = self._toggle_x
        w, h = 36, 22
        r = h // 2

        track_fill = GREEN if self._autostart else "#45475a"
        _rr(c, x, y + 1, x + w, y + 1 + h, r, fill=track_fill, outline="", tags="toggle")

        # Knob
        knob_x = (x + w - r - 2) if self._autostart else (x + r + 2)
        knob_r = 8
        c.create_oval(knob_x - knob_r, y + 1 + h // 2 - knob_r,
                       knob_x + knob_r, y + 1 + h // 2 + knob_r,
                       fill="#ffffff", outline="", tags="toggle")

        c.tag_bind("toggle", "<Button-1>", lambda e: self._toggle_autostart())

    def _toggle_autostart(self) -> None:
        self._autostart = not self._autostart
        self._draw_toggle(self._canvas, self._toggle_y)

    # ── Poll interval selector ───────────────────────────────────────

    def _select_poll(self, idx: int) -> None:
        self._poll_idx = idx
        c = self._canvas
        for rid, tid, i in self._seg_items:
            if i == idx:
                c.itemconfig(rid, fill=ACCENT)
                c.itemconfig(tid, fill="#1e1e2e")
            else:
                c.itemconfig(rid, fill=SURFACE)
                c.itemconfig(tid, fill=COLOR_TEXT_DIM)

    # ── Connection test ──────────────────────────────────────────────

    def _poll_queue(self) -> None:
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

    def _test_connection(self) -> None:
        self._canvas.itemconfig(self._test_btn_id, fill=BTN_BG)
        self._canvas.itemconfig(self._test_status_id, text="Testing...", fill=YELLOW)

        def _do():
            try:
                ok, msg = test_connection()
            except Exception as exc:
                ok, msg = False, str(exc)
            self._msg_queue.put({"handler": self._on_test_result,
                                  "kwargs": {"ok": ok, "msg": msg}})

        Thread(target=_do, daemon=True).start()

    def _on_test_result(self, ok: bool, msg: str) -> None:
        color = GREEN if ok else RED
        prefix = "\u2713 " if ok else "\u2717 "
        self._canvas.itemconfig(self._test_status_id, text=prefix + msg, fill=color)

    # ── Save ─────────────────────────────────────────────────────────

    def _save(self) -> None:
        """Save display/startup settings. No credentials stored."""
        s = settings.load()
        s["autostart"] = self._autostart
        s["poll_interval"] = POLL_OPTIONS[self._poll_idx][1]
        settings.save(s)

        from .autostart import set_autostart
        set_autostart(self._autostart)

        # Flash save button green
        c = self._canvas
        c.itemconfig(self._save_bg, fill=GREEN)
        c.itemconfig(self._save_txt, text="\u2713 Saved", fill="#1e3a2a")
        self._win.after(600, self.hide)

        if self._on_settings_changed:
            self._on_settings_changed(s)
