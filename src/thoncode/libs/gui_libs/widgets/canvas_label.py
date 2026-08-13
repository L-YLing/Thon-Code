#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Label",
    "Path": ".main.libs.gui_libs.widgets.canvas_label",
    "Entrance": "main.py"
}

"""
Canvas-based themed label widget.

Renders text (and an optional leading icon glyph) on a tk.Canvas with
colors and fonts sourced from the StyleSystem singleton. The label keeps
the same dark-theme defaults as the rest of the widget library so window
chrome stays visually consistent.
"""

import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Optional

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider


class CanvasLabel(BaseWidget, StyleProvider):
    """Canvas-painted label with optional icon and alignment.

    The label can render an optional leading icon (an emoji or short text
    glyph) followed by the label text. Colors and fonts are read from the
    StyleSystem so the control matches the surrounding UI.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the canvas label.

        Args:
            parent: Parent Tkinter widget.
            **kwargs: Optional configuration. Recognized keys:
                text (str): Label text.
                icon (str): Optional leading icon glyph.
                align (str): Horizontal alignment: 'left', 'center',
                    'right'. Defaults to 'left'.
                width (int): Canvas width in pixels.
                height (int): Canvas height in pixels.
        """
        self._parent = parent
        self._canvas: Optional[tk.Canvas] = None
        self._font: Optional[tkfont.Font] = None

        self._text: str = kwargs.get("text", "")
        self._icon: str = kwargs.get("icon", "")
        self._align: str = kwargs.get("align", "left")
        self._width: int = int(kwargs.get("width", 120))
        self._height: int = int(kwargs.get("height", 24))

        # Style values (populated by _load_style).
        self._bg: str = "#282c34"
        self._fg: str = "#abb2bf"
        self._fg_dim: str = "#5c6370"
        self._font_family: str = "Microsoft YaHei"
        self._font_size: int = 10
        self._icon_gap: int = 6

        self._style_system = StyleSystem()
        super().__init__(parent)

    # ---- BaseWidget implementation ----

    def create_widget(self) -> tk.Canvas:
        """Create the canvas and paint the initial label.

        Returns:
            The tk.Canvas that hosts the label.
        """
        self._load_style()
        self._font = tkfont.Font(family=self._font_family, size=self._font_size)
        self._canvas = tk.Canvas(
            self._parent,
            width=self._width,
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
        """Pack the label into its parent.

        Args:
            **kwargs: Pack configuration options.
        """
        if self._canvas:
            self._canvas.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the label into its parent.

        Args:
            **kwargs: Grid configuration options.
        """
        if self._canvas:
            self._canvas.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the label and release resources."""
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
        """Load label style values from the StyleSystem singleton."""
        ss = self._style_system
        self._bg = ss.get_value("widget", "bg", "#282c34")
        self._fg = ss.get_value("widget", "fg", "#abb2bf")
        self._fg_dim = ss.get_value("widget", "disabled_fg", "#5c6370")
        self._font_family = ss.get_value("widget", "font_family", "Microsoft YaHei")
        self._font_size = ss.get_value("widget", "font_size", 10)

    # ---- Rendering ----

    def _redraw(self) -> None:
        """Repaint the icon and text on the canvas."""
        if not self._canvas:
            return
        self._canvas.delete("all")
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w <= 1:
            w = self._width
        if h <= 1:
            h = self._height

        pad_x = 4
        cy = h / 2.0

        # Compute total content width to support alignment.
        text_w = self._font.measure(self._text) if self._text else 0
        icon_w = self._font.measure(self._icon) if self._icon else 0
        gap = self._icon_gap if (self._icon and self._text) else 0
        total_w = icon_w + gap + text_w

        if self._align == "center":
            start_x = max(pad_x, (w - total_w) / 2.0)
        elif self._align == "right":
            start_x = max(pad_x, w - total_w - pad_x)
        else:
            start_x = pad_x

        cursor_x = start_x
        if self._icon:
            self._canvas.create_text(
                cursor_x, cy, text=self._icon, anchor="w",
                font=self._font, fill=self._fg,
            )
            cursor_x += icon_w + gap

        if self._text:
            self._canvas.create_text(
                cursor_x, cy, text=self._text, anchor="w",
                font=self._font, fill=self._fg,
            )

    # ---- Public API ----

    def set_text(self, text: str) -> None:
        """Update the label text and repaint.

        Args:
            text: New label text.
        """
        self._text = text
        self._redraw()

    def set_icon(self, icon: str) -> None:
        """Update the leading icon glyph and repaint.

        Args:
            icon: New icon string (emoji or short text).
        """
        self._icon = icon
        self._redraw()

    def set_alignment(self, align: str) -> None:
        """Update the horizontal alignment and repaint.

        Args:
            align: One of 'left', 'center', 'right'.
        """
        self._align = align
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
            self._canvas.configure(bg=self._bg)
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
        if self._canvas:
            self._canvas.configure(bg=self._bg)
        self._redraw()
