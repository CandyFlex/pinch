"""Detail popup window — polished dark theme with rounded progress bars."""

import logging
import tkinter as tk
from datetime import datetime

from .config import (
    COLOR_BAR_BG, COLOR_BG_POPUP, COLOR_BLUE, COLOR_BORDER,
    COLOR_TEXT, COLOR_TEXT_DIM, FONT_FAMILY, FONT_SIZE_POPUP_BODY,
    FONT_SIZE_POPUP_TITLE, POPUP_HEIGHT, POPUP_WIDTH,
    color_for_utilization,
)
from .shared_state import SharedState, UsageData
from .utils import format_reset_time, pct_str

log = logging.getLogger(__name__)

# Popup visual constants
TRANSPARENT_COLOR = "#ff00ff"
POPUP_BG = "#1a1b2e"
POPUP_RADIUS = 14
BAR_HEIGHT = 8
BAR_RADIUS = 4
SECTION_PAD = 14


def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    """Draw a rounded rectangle on a canvas."""
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class PopupView:
    """Polished dark-themed detail popup showing all usage metrics."""

    def __init__(self, root: tk.Tk, state: SharedState) -> None:
        self._root = root
        self._state = state
        self._win: tk.Toplevel | None = None

    @property
    def is_visible(self) -> bool:
        return self._win is not None and self._win.winfo_exists()

    def toggle(self) -> None:
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        if self.is_visible:
            self._win.lift()
            return

        self._win = tk.Toplevel(self._root)
        self._win.title("Pinch — Usage Details")
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self._win.configure(bg=TRANSPARENT_COLOR)

        self._position_popup()
        self._build_ui()

        data = self._state.get()
        self._update(data)

        self._win.bind("<Escape>", lambda e: self.hide())
        self._win.bind("<FocusOut>", self._on_focus_out)
        self._state.on_change(self._on_data_change)
        self._win.focus_set()

    def hide(self) -> None:
        if self._win:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None

    def _on_focus_out(self, event=None) -> None:
        if self._win:
            self._root.after(150, self._check_and_close)

    def _check_and_close(self) -> None:
        if not self._win:
            return
        try:
            focus = self._root.focus_get()
            if focus and str(focus).startswith(str(self._win)):
                return
        except Exception:
            pass
        self.hide()

    def _position_popup(self) -> None:
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - POPUP_WIDTH - 16
        y = screen_h - POPUP_HEIGHT - 64
        self._win.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}+{x}+{y}")

    def _build_ui(self) -> None:
        """Build the popup UI inside a canvas with rounded outer shell."""
        f = self._win

        # Outer canvas for rounded window shape
        self._outer = tk.Canvas(
            f, width=POPUP_WIDTH, height=POPUP_HEIGHT,
            highlightthickness=0, bd=0, bg=TRANSPARENT_COLOR,
        )
        self._outer.pack(fill=tk.BOTH, expand=True)

        # Draw rounded window background — single unified color
        _round_rect(self._outer, 1, 1, POPUP_WIDTH - 2, POPUP_HEIGHT - 2,
                     POPUP_RADIUS, fill=POPUP_BG, outline="#313244", width=1)

        # Title text
        header_h = 44
        self._outer.create_text(
            SECTION_PAD, header_h // 2,
            text="Pinch",
            font=(FONT_FAMILY, FONT_SIZE_POPUP_TITLE, "bold"),
            fill=COLOR_TEXT, anchor="w",
        )

        # Plan label (right of title)
        self._plan_id = self._outer.create_text(
            POPUP_WIDTH // 2, header_h // 2,
            text="",
            font=(FONT_FAMILY, 8),
            fill=COLOR_TEXT_DIM, anchor="center",
        )

        # Close button
        close_id = self._outer.create_text(
            POPUP_WIDTH - SECTION_PAD, header_h // 2,
            text="\u2715",
            font=(FONT_FAMILY, 10),
            fill="#585b70", anchor="e",
        )
        self._outer.tag_bind(close_id, "<Button-1>", lambda e: self.hide())

        # Thin separator line below title
        sep_y = header_h + 1
        self._outer.create_line(
            SECTION_PAD, sep_y, POPUP_WIDTH - SECTION_PAD, sep_y,
            fill="#313244", width=1,
        )

        # Content starts below separator
        y_cursor = header_h + 12

        # --- 5-Hour Rolling ---
        self._five_widgets = self._draw_metric_section(
            y_cursor, "5-Hour Rolling", "--", "--"
        )
        y_cursor += 52

        # --- 7-Day Opus ---
        self._week_widgets = self._draw_metric_section(
            y_cursor, "7-Day (Opus)", "--", "--"
        )
        y_cursor += 52

        # --- 7-Day Sonnet ---
        self._sonnet_widgets = self._draw_metric_section(
            y_cursor, "7-Day (Sonnet)", "--", "--"
        )
        y_cursor += 52

        # Separator
        self._outer.create_line(
            SECTION_PAD, y_cursor, POPUP_WIDTH - SECTION_PAD, y_cursor,
            fill="#313244", width=1,
        )
        y_cursor += 10

        # --- Extra Usage ---
        self._extra_widgets = self._draw_metric_section(
            y_cursor, "Extra Usage", "--", "--", bar_color=COLOR_BLUE
        )
        y_cursor += 52

        # Last updated
        self._updated_id = self._outer.create_text(
            POPUP_WIDTH - SECTION_PAD, POPUP_HEIGHT - 14,
            text="",
            font=(FONT_FAMILY, 7),
            fill="#45475a", anchor="e",
        )

    def _draw_metric_section(self, y: int, label: str, pct_text: str,
                              reset_text: str, bar_color: str | None = None) -> dict:
        """Draw a metric section: label, pct, reset time, progress bar."""
        c = self._outer
        lx = SECTION_PAD
        rx = POPUP_WIDTH - SECTION_PAD
        bar_w = rx - lx

        # Row 1: label (left) + pct (right)
        label_id = c.create_text(
            lx, y, text=label,
            font=(FONT_FAMILY, FONT_SIZE_POPUP_BODY, "bold"),
            fill=COLOR_TEXT, anchor="nw",
        )
        pct_id = c.create_text(
            rx, y, text=pct_text,
            font=(FONT_FAMILY, FONT_SIZE_POPUP_BODY, "bold"),
            fill=COLOR_TEXT_DIM, anchor="ne",
        )

        # Row 2: reset time
        reset_id = c.create_text(
            lx, y + 16, text=f"Resets {reset_text}",
            font=(FONT_FAMILY, 8),
            fill="#585b70", anchor="nw",
        )

        # Row 3: progress bar (rounded)
        bar_y = y + 30
        # Background bar
        _round_rect(c, lx, bar_y, rx, bar_y + BAR_HEIGHT,
                     BAR_RADIUS, fill=COLOR_BAR_BG, outline="")
        # Fill bar (placeholder, 0 width)
        fill_id = _round_rect(c, lx, bar_y, lx + 1, bar_y + BAR_HEIGHT,
                               BAR_RADIUS, fill=bar_color or COLOR_TEXT_DIM, outline="")

        return {
            "pct_id": pct_id,
            "reset_id": reset_id,
            "fill_id": fill_id,
            "bar_y": bar_y,
            "bar_w": bar_w,
            "bar_color": bar_color,
            "lx": lx,
        }

    def _update_bar(self, widgets: dict, pct: float, color: str) -> None:
        """Redraw a progress bar fill to match the new percentage."""
        c = self._outer
        c.delete(widgets["fill_id"])

        lx = widgets["lx"]
        bar_y = widgets["bar_y"]
        bar_w = widgets["bar_w"]
        fill_w = max(BAR_RADIUS * 2, int(bar_w * pct / 100)) if pct > 0 else 0

        if fill_w > 0:
            widgets["fill_id"] = _round_rect(
                c, lx, bar_y, lx + fill_w, bar_y + BAR_HEIGHT,
                BAR_RADIUS, fill=color, outline="",
            )
        else:
            # Invisible placeholder
            widgets["fill_id"] = _round_rect(
                c, lx, bar_y, lx + 1, bar_y + BAR_HEIGHT,
                BAR_RADIUS, fill=color, outline="",
            )

    def _on_data_change(self, data: UsageData) -> None:
        if self._win and self._win.winfo_exists():
            self._root.after(0, self._update, data)

    def _update(self, data: UsageData) -> None:
        if not self._win or not self._win.winfo_exists():
            return

        c = self._outer

        if data.error:
            for w in (self._five_widgets, self._week_widgets, self._sonnet_widgets):
                c.itemconfig(w["pct_id"], text="ERR", fill="#f38ba8")
                c.itemconfig(w["reset_id"], text=f"Error: {data.error}")
            return

        # 5-hour
        five = data.five_hour
        five_color = color_for_utilization(five.utilization)
        c.itemconfig(self._five_widgets["pct_id"],
                     text=pct_str(five.utilization), fill=five_color)
        c.itemconfig(self._five_widgets["reset_id"],
                     text=f"Resets {format_reset_time(five.resets_at)}")
        self._update_bar(self._five_widgets, five.utilization, five_color)

        # 7-day
        week = data.seven_day
        week_color = color_for_utilization(week.utilization)
        c.itemconfig(self._week_widgets["pct_id"],
                     text=pct_str(week.utilization), fill=week_color)
        c.itemconfig(self._week_widgets["reset_id"],
                     text=f"Resets {format_reset_time(week.resets_at)}")
        self._update_bar(self._week_widgets, week.utilization, week_color)

        # Sonnet
        sonnet = data.seven_day_sonnet
        sonnet_color = color_for_utilization(sonnet.utilization)
        c.itemconfig(self._sonnet_widgets["pct_id"],
                     text=pct_str(sonnet.utilization), fill=sonnet_color)
        c.itemconfig(self._sonnet_widgets["reset_id"],
                     text=f"Resets {format_reset_time(sonnet.resets_at)}")
        self._update_bar(self._sonnet_widgets, sonnet.utilization, sonnet_color)

        # Extra usage
        extra = data.extra_usage
        if extra.is_enabled:
            c.itemconfig(self._extra_widgets["pct_id"],
                         text=f"${extra.used_credits:.2f} / ${extra.monthly_limit:.2f}",
                         fill=COLOR_BLUE)
            c.itemconfig(self._extra_widgets["reset_id"],
                         text=f"{pct_str(extra.utilization)} of monthly limit")
            self._update_bar(self._extra_widgets, extra.utilization, COLOR_BLUE)
        else:
            c.itemconfig(self._extra_widgets["pct_id"], text="Disabled", fill="#585b70")
            c.itemconfig(self._extra_widgets["reset_id"], text="")

        # Last updated
        if data.last_updated:
            try:
                dt = datetime.fromisoformat(data.last_updated)
                local_dt = dt.astimezone()
                c.itemconfig(self._updated_id,
                             text=f"Updated {local_dt.strftime('%H:%M:%S')}")
            except ValueError:
                pass
