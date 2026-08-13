#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Status Bar",
    "Path": ".main.libs.gui_libs.widgets.canvas_statusbar",
    "Entrance": "main.py"
}

"""
Canvas-based status bar widget.

Renders a single-row status bar on a tk.Canvas with three text segments
(left, center, right) and subtle separator lines. All colors and fonts are
sourced from the StyleSystem singleton so the status bar matches the rest
of the application window chrome.
"""

import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Dict, Optional

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider


class CanvasStatusBar(BaseWidget, StyleProvider):
    """Multi-segment status bar painted on a tk.Canvas.

    The status bar exposes three named segments: ``left``, ``center`` and
    ``right``. Each segment holds an independent text value and is rendered
    with horizontal alignment matching its position. A thin separator line
    is drawn at the top of the bar and vertical separators divide the
    segments.
    """

    SEGMENT_LEFT = "left"
    SEGMENT_CENTER = "center"
    SEGMENT_RIGHT = "right"

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the status bar.

        Args:
            parent: Parent Tkinter widget.
            **kwargs: Optional configuration. Recognized keys:
                height (int): Bar height in pixels.
                left (str): Initial left segment text.
                center (str): Initial center segment text.
                right (str): Initial right segment text.
                separators (bool): Draw vertical separators between
                    segments. Defaults to True.
        """
        self._parent = parent
        self._canvas: Optional[tk.Canvas] = None
        self._font: Optional[tkfont.Font] = None

        self._height: int = int(kwargs.get("height", 24))
        self._separators: bool = bool(kwargs.get("separators", True))
        self._segments: Dict[str, str] = {
            self.SEGMENT_LEFT: kwargs.get("left", ""),
            self.SEGMENT_CENTER: kwargs.get("center", ""),
            self.SEGMENT_RIGHT: kwargs.get("right", ""),
        }

        # Style values (populated by _load_style).
        self._bg: str = "#007acc"
        self._bg_alt: str = "#1e2127"
        self._fg: str = "#ffffff"
        self._fg_dim: str = "#d4d4d4"
        self._border: str = "#3e4451"
        self._font_family: str = "Microsoft YaHei"
        self._font_size: int = 10

        self._style_system = StyleSystem()
        super().__init__(parent)

    # ---- BaseWidget implementation ----

    def create_widget(self) -> tk.Canvas:
        """Create the canvas and paint the initial status bar.

        Returns:
            The tk.Canvas that hosts the status bar.
        """
        self._load_style()
        self._font = tkfont.Font(family=self._font_family, size=self._font_size)
        self._canvas = tk.Canvas(
            self._parent,
            height=self._height,
            bg=self._bg,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
        )
        self._canvas.bind("<Configure>", lambda e: self._redraw())
        self._redraw()
        return self._canvas

    def pack(self, **kwargs: Any) -> None:
        """Pack the status bar into its parent.

        Args:
            **kwargs: Pack configuration options.
        """
        if self._canvas:
            self._canvas.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the status bar into its parent.

        Args:
            **kwargs: Grid configuration options.
        """
        if self._canvas:
            self._canvas.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the status bar and release resources."""
        if self._canvas and not self._destroyed:
            self._canvas.destroy()
            self._destroyed = True

    def get_widget(self) -> Optional[tk.Canvas]:
        """Get the underlying canvas widget.

        Returns:
            The canvas widget, or None if not yet created.
        """
        return self._canvas

    # ---- Style loading ----

    def _load_style(self) -> None:
        """Load status bar style values from the StyleSystem singleton."""
        ss = self._style_system
        self._bg = ss.get_value("widget", "statusbar_bg", "#007acc")
        self._bg_alt = ss.get_value("widget", "bg_alt", "#1e2127")
        self._fg = ss.get_value("widget", "statusbar_fg", "#ffffff")
        self._fg_dim = ss.get_value("widget", "fg", "#abb2bf")
        self._border = ss.get_value("widget", "border", "#3e4451")
        self._font_family = ss.get_value("widget", "font_family", "Microsoft YaHei")
        self._font_size = ss.get_value("widget", "font_size", 10)

    # ---- Rendering ----

    def _redraw(self) -> None:
        """Repaint the background, separators and segment text."""
        if not self._canvas:
            return
        canvas = self._canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            w = 400
        if h <= 1:
            h = self._height

        canvas.configure(bg=self._bg)
        canvas.create_rectangle(0, 0, w, h, fill=self._bg, outline="")

        # Top border line separating the bar from the content above.
        canvas.create_line(0, 0, w, 0, fill=self._border, width=1)

        pad_x = 8
        cy = h / 2.0

        left_text = self._segments[self.SEGMENT_LEFT]
        center_text = self._segments[self.SEGMENT_CENTER]
        right_text = self._segments[self.SEGMENT_RIGHT]

        # Left segment (left-aligned).
        if left_text:
            canvas.create_text(
                pad_x, cy, text=left_text, anchor="w",
                font=self._font, fill=self._fg,
            )

        # Center segment (horizontally centered).
        if center_text:
            canvas.create_text(
                w / 2.0, cy, text=center_text, anchor="center",
                font=self._font, fill=self._fg,
            )

        # Right segment (right-aligned).
        if right_text:
            canvas.create_text(
                w - pad_x, cy, text=right_text, anchor="e",
                font=self._font, fill=self._fg,
            )

        # Vertical separator lines between populated segments.
        if self._separators:
            third = w / 3.0
            canvas.create_line(third, 4, third, h - 4, fill=self._border, width=1)
            canvas.create_line(
                2 * third, 4, 2 * third, h - 4, fill=self._border, width=1
            )

    # ---- Public API ----

    def set_text(self, segment: str, text: str) -> None:
        """Update the text of a named segment.

        Args:
            segment: One of 'left', 'center', 'right'.
            text: New text for the segment.
        """
        if segment in self._segments:
            self._segments[segment] = text
            self._redraw()

    def get_text(self, segment: str) -> str:
        """Return the text of a named segment.

        Args:
            segment: One of 'left', 'center', 'right'.

        Returns:
            The segment text, or an empty string if the segment is unknown.
        """
        return self._segments.get(segment, "")

    def clear(self) -> None:
        """Clear all three segments."""
        for key in self._segments:
            self._segments[key] = ""
        self._redraw()

    # ---- StyleProvider implementation ----

    def apply_style(self, style_name: str) -> None:
        """Apply a named style registered in the StyleSystem.

        Args:
            style_name: Name of the style to apply.
        """
        if self._style_system.apply_style(style_name):
            self._load_style()
            if self._font:
                self._font.configure(family=self._font_family, size=self._font_size)
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
        if self._font:
            self._font.configure(family=self._font_family, size=self._font_size)
        self._redraw()
