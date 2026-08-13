#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Scrollbar",
    "Path": ".main.libs.gui_libs.widgets.canvas_scrollbar",
    "Entrance": "main.py"
}

"""
Canvas-based custom vertical scrollbar widget.

A self-painted vertical scrollbar drawn on a tk.Canvas with a track, a
draggable slider (thumb), and up/down arrow buttons styled like the
CanvasButton control. The scrollbar mimics the tk.Scrollbar interface so
it can be connected to any scrollable widget through ``command`` and
``set`` without depending on other widget modules.
"""

import tkinter as tk
from typing import Any, Callable, Optional

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider


class CanvasScrollbar(BaseWidget, StyleProvider):
    """Custom vertical scrollbar painted on a tk.Canvas.

    The scrollbar exposes a ``set(first, last)`` method (to be wired to a
    scrollable widget's ``yscrollcommand``) and accepts a ``command``
    callback (typically ``widget.yview``). Arrows scroll by one unit, the
    track pages on click, and the slider can be dragged to reposition the
    view.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the canvas scrollbar.

        Args:
            parent: Parent Tkinter widget.
            **kwargs: Optional configuration. Recognized keys:
                command (Callable): Scroll command, usually widget.yview.
                width (int): Scrollbar width in pixels.
        """
        self._parent = parent
        self._canvas: Optional[tk.Canvas] = None

        self._command: Optional[Callable[..., Any]] = kwargs.get("command", None)
        self._width: int = int(kwargs.get("width", 14))

        # Visible range as reported by the scrollable widget.
        self._first: float = 0.0
        self._last: float = 1.0

        # Drag state for the slider.
        self._dragging: bool = False
        self._drag_start_y: float = 0.0
        self._drag_start_first: float = 0.0

        # Hover/press state for the arrow buttons (CanvasButton style).
        self._arrow_hover: Optional[str] = None
        self._arrow_pressed: Optional[str] = None

        # Style values (populated by _load_style).
        self._bg: str = "#282c34"
        self._track_bg: str = "#21252b"
        self._slider_bg: str = "#4b5263"
        self._slider_hover_bg: str = "#5c6370"
        self._slider_pressed_bg: str = "#6b7280"
        self._arrow_bg: str = "#3e4451"
        self._arrow_hover_bg: str = "#4b5263"
        self._arrow_pressed_bg: str = "#5c6370"
        self._arrow_fg: str = "#abb2bf"
        self._border: str = "#3e4451"

        self._style_system = StyleSystem()
        super().__init__(parent)

    # ---- BaseWidget implementation ----

    def create_widget(self) -> tk.Canvas:
        """Create the canvas and paint the initial scrollbar.

        Returns:
            The tk.Canvas that hosts the scrollbar.
        """
        self._load_style()
        self._canvas = tk.Canvas(
            self._parent,
            width=self._width,
            bg=self._track_bg,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
        )
        self._setup_bindings()
        self._redraw()
        return self._canvas

    def pack(self, **kwargs: Any) -> None:
        """Pack the scrollbar into its parent.

        Args:
            **kwargs: Pack configuration options.
        """
        if self._canvas:
            self._canvas.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the scrollbar into its parent.

        Args:
            **kwargs: Grid configuration options.
        """
        if self._canvas:
            self._canvas.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the scrollbar and release resources."""
        if self._canvas and not self._destroyed:
            self._canvas.destroy()
            self._destroyed = True

    def get_widget(self) -> Optional[tk.Canvas]:
        """Get the underlying canvas widget.

        Returns:
            The canvas widget, or None if not yet created.
        """
        return self._canvas

    def configure(self, **kwargs: Any) -> None:
        """Configure scrollbar options (supports the ``command`` key).

        Args:
            **kwargs: Configuration options. The ``command`` key is
                handled locally; other keys are forwarded to the canvas.
        """
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if kwargs and self._canvas:
            self._canvas.configure(**kwargs)

    # ---- Style loading ----

    def _load_style(self) -> None:
        """Load scrollbar style values from the StyleSystem singleton."""
        ss = self._style_system
        self._bg = ss.get_value("widget", "bg", "#282c34")
        self._track_bg = ss.get_value("widget", "bg_alt", "#21252b")
        self._slider_bg = ss.get_value("widget", "hover_bg", "#4b5263")
        self._slider_hover_bg = ss.get_value("widget", "pressed_bg", "#5c6370")
        self._slider_pressed_bg = ss.get_value("widget", "slider_pressed_bg", "#6b7280")
        self._arrow_bg = ss.get_value("widget", "button_bg", "#3e4451")
        self._arrow_hover_bg = ss.get_value("widget", "hover_bg", "#4b5263")
        self._arrow_pressed_bg = ss.get_value("widget", "pressed_bg", "#5c6370")
        self._arrow_fg = ss.get_value("widget", "fg", "#abb2bf")
        self._border = ss.get_value("widget", "border", "#3e4451")

    # ---- Geometry helpers ----

    def _arrow_height(self) -> int:
        """Return the height of each arrow button.

        Returns:
            Arrow button height in pixels.
        """
        return self._width

    def _track_bounds(self) -> tuple:
        """Return the (top, bottom) y coordinates of the track area.

        Returns:
            Tuple of track top and bottom coordinates.
        """
        if not self._canvas:
            return (0, 0)
        h = self._canvas.winfo_height()
        if h <= 1:
            h = 100
        ah = self._arrow_height()
        return (ah, h - ah)

    def _slider_bounds(self) -> tuple:
        """Return the (top, bottom) y coordinates of the slider.

        Returns:
            Tuple of slider top and bottom coordinates.
        """
        top, bottom = self._track_bounds()
        track_range = bottom - top
        if track_range <= 0:
            return (top, bottom)
        visible = max(0.0, self._last - self._first)
        slider_len = max(track_range * 0.1, track_range * visible)
        slider_top = top + self._first * track_range
        slider_bottom = min(bottom, slider_top + slider_len)
        return (slider_top, slider_bottom)

    # ---- Event handling ----

    def _setup_bindings(self) -> None:
        """Bind mouse events for arrows, track and slider."""
        if not self._canvas:
            return
        self._canvas.bind("<Button-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<Motion>", self._on_hover)
        self._canvas.bind("<Leave>", self._on_leave)
        self._canvas.bind("<Configure>", lambda e: self._redraw())

    def _hit_test(self, y: float) -> str:
        """Identify which scrollbar element is at the given y coordinate.

        Args:
            y: Y coordinate relative to the canvas.

        Returns:
            One of 'up', 'down', 'slider', 'track', or 'none'.
        """
        if not self._canvas:
            return "none"
        h = self._canvas.winfo_height()
        if h <= 1:
            h = 100
        ah = self._arrow_height()
        if y < ah:
            return "up"
        if y > h - ah:
            return "down"
        s_top, s_bot = self._slider_bounds()
        if s_top <= y <= s_bot:
            return "slider"
        return "track"

    def _on_press(self, event: tk.Event) -> None:
        """Handle mouse press on arrows, slider or track.

        Args:
            event: The mouse press event.
        """
        target = self._hit_test(event.y)
        if target == "up":
            self._arrow_pressed = "up"
            self._scroll_by_units(-1)
        elif target == "down":
            self._arrow_pressed = "down"
            self._scroll_by_units(1)
        elif target == "slider":
            self._dragging = True
            self._drag_start_y = event.y
            self._drag_start_first = self._first
        elif target == "track":
            # Page toward the clicked position.
            s_top, _ = self._slider_bounds()
            if event.y < s_top:
                self._scroll_by_pages(-1)
            else:
                self._scroll_by_pages(1)
        self._redraw()

    def _on_motion(self, event: tk.Event) -> None:
        """Handle slider dragging.

        Args:
            event: The mouse motion event.
        """
        if not self._dragging:
            return
        top, bottom = self._track_bounds()
        track_range = bottom - top
        if track_range <= 0:
            return
        visible = max(0.0, self._last - self._first)
        delta = (event.y - self._drag_start_y) / track_range
        new_first = self._drag_start_first + delta
        new_first = max(0.0, min(new_first, 1.0 - visible))
        self._invoke_command("moveto", new_first)

    def _on_release(self, event: tk.Event) -> None:
        """End slider drag and clear arrow press state.

        Args:
            event: The mouse release event.
        """
        self._dragging = False
        self._arrow_pressed = None
        self._redraw()

    def _on_hover(self, event: tk.Event) -> None:
        """Track hover state for arrow and slider highlighting.

        Args:
            event: The mouse motion event.
        """
        target = self._hit_test(event.y)
        new_hover = target if target in ("up", "down") else None
        if new_hover != self._arrow_hover:
            self._arrow_hover = new_hover
            self._redraw()

    def _on_leave(self, event: tk.Event) -> None:
        """Clear hover state when the pointer leaves the scrollbar.

        Args:
            event: The mouse leave event.
        """
        self._arrow_hover = None
        self._redraw()

    # ---- Scrolling actions ----

    def _invoke_command(self, *args: Any) -> None:
        """Forward a scroll command to the connected widget.

        Args:
            *args: Arguments passed to the command (e.g. 'moveto', frac).
        """
        if self._command:
            try:
                self._command(*args)
            except Exception:
                pass

    def _scroll_by_units(self, units: int) -> None:
        """Scroll by a number of units.

        Args:
            units: Number of units to scroll (negative scrolls up).
        """
        self._invoke_command("scroll", units, "units")

    def _scroll_by_pages(self, pages: int) -> None:
        """Scroll by a number of pages.

        Args:
            pages: Number of pages to scroll (negative scrolls up).
        """
        self._invoke_command("scroll", pages, "pages")

    # ---- Rendering ----

    def _redraw(self) -> None:
        """Repaint the entire scrollbar."""
        if not self._canvas:
            return
        canvas = self._canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            w = self._width
        if h <= 1:
            h = 100

        ah = self._arrow_height()
        # Track background.
        canvas.create_rectangle(0, ah, w, h - ah, fill=self._track_bg, outline="")

        # Up arrow button.
        self._draw_arrow(canvas, 0, 0, w, ah, "up")
        # Down arrow button.
        self._draw_arrow(canvas, 0, h - ah, w, h, "down")

        # Slider.
        s_top, s_bot = self._slider_bounds()
        if s_bot - s_top > 2:
            slider_fill = self._slider_pressed_bg if self._dragging else self._slider_bg
            pad = 3
            canvas.create_rectangle(
                pad, s_top, w - pad, s_bot, fill=slider_fill, outline=""
            )

    def _draw_arrow(
        self,
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        direction: str,
    ) -> None:
        """Draw an arrow button with a triangle glyph.

        Args:
            canvas: Target canvas.
            x1: Left coordinate.
            y1: Top coordinate.
            x2: Right coordinate.
            y2: Bottom coordinate.
            direction: 'up' or 'down'.
        """
        hover = self._arrow_hover == direction
        pressed = self._arrow_pressed == direction
        if pressed:
            fill = self._arrow_pressed_bg
        elif hover:
            fill = self._arrow_hover_bg
        else:
            fill = self._arrow_bg

        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        size = min(x2 - x1, y2 - y1) * 0.25
        if direction == "up":
            points = [cx, cy - size, cx - size, cy + size, cx + size, cy + size]
        else:
            points = [cx, cy + size, cx - size, cy - size, cx + size, cy - size]
        canvas.create_polygon(points, fill=self._arrow_fg, outline="")

    # ---- Scrollbar interface ----

    def set(self, first: float, last: float) -> None:
        """Update the visible range and repaint the slider.

        This method is intended to be wired to a scrollable widget's
        ``yscrollcommand``.

        Args:
            first: Top fraction of the visible area (0.0 - 1.0).
            last: Bottom fraction of the visible area (0.0 - 1.0).
        """
        self._first = max(0.0, min(1.0, float(first)))
        self._last = max(0.0, min(1.0, float(last)))
        self._redraw()

    # ---- StyleProvider implementation ----

    def apply_style(self, style_name: str) -> None:
        """Apply a named style registered in the StyleSystem.

        Args:
            style_name: Name of the style to apply.
        """
        if self._style_system.apply_style(style_name):
            self._load_style()
            if self._canvas:
                self._canvas.configure(bg=self._track_bg)
            self._redraw()

    def get_style_value(self, key: str, default: Any = None) -> Any:
        """Get a style value from the 'widget' section.

        Args:
            key: Style property key.
            default: Default value if key is not found.

        Returns:
            The style value or the provided default.
        """
        return self._style_system.get_value("widget", key, default)

    def set_style_value(self, key: str, value: Any) -> None:
        """Set a style value on the 'widget' section and repaint.

        Args:
            key: Style property key.
            value: New value.
        """
        self._style_system.set_style("widget", key, value)
        self._load_style()
        if self._canvas:
            self._canvas.configure(bg=self._track_bg)
        self._redraw()
