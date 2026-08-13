#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Frame",
    "Path": ".main.libs.gui_libs.widgets.canvas_frame",
    "Entrance": "main.py"
}

"""
Canvas-based themed container frame.

Wraps a tk.Frame and injects a unified background color sourced from the
StyleSystem singleton. When rounded corners are requested, a tk.Canvas is
used as the background layer and an inner content frame is exposed for
placing child widgets, keeping the window chrome visually consistent.
"""

import tkinter as tk
from typing import Any, List, Optional

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider
from libs.gui_libs.widgets.canvas_button import create_rounded_rect


class CanvasFrame(BaseWidget, StyleProvider):
    """Themed container frame with optional rounded corners.

    By default the frame is a plain tk.Frame whose background is sourced
    from the StyleSystem. When ``rounded=True`` the outer widget becomes a
    tk.Canvas that paints a rounded background, and child widgets should be
    added to the inner content frame returned by :meth:`get_content`.

    Attributes:
        DEFAULT_RADIUS: Default corner radius when rounding is enabled.
    """

    DEFAULT_RADIUS = 8

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the canvas frame.

        Args:
            parent: Parent Tkinter widget.
            **kwargs: Optional configuration. Recognized keys:
                rounded (bool): Paint a rounded background canvas.
                radius (int): Corner radius when rounded is enabled.
                bg (str): Override the background color.
                border (str): Override the border color.
                border_width (int): Outer border width when rounded.
                padx (int): Inner horizontal padding for content.
                pady (int): Inner vertical padding for content.
        """
        self._parent = parent
        self._outer: Optional[tk.Misc] = None
        self._content: Optional[tk.Frame] = None

        self._rounded: bool = bool(kwargs.get("rounded", False))
        self._radius: int = int(kwargs.get("radius", self.DEFAULT_RADIUS))
        self._padx: int = int(kwargs.get("padx", 0))
        self._pady: int = int(kwargs.get("pady", 0))
        self._border_width: int = int(kwargs.get("border_width", 0))
        self._bg_override: Optional[str] = kwargs.get("bg", None)
        self._border_override: Optional[str] = kwargs.get("border", None)

        # Style values (populated by _load_style).
        self._bg: str = "#282c34"
        self._border: str = "#3e4451"
        self._container_bg: str = "#282c34"

        # Canvas item handles for the rounded variant.
        self._content_id: Optional[int] = None
        self._bg_items: List[int] = []

        self._style_system = StyleSystem()
        super().__init__(parent)

    # ---- BaseWidget implementation ----

    def create_widget(self) -> tk.Misc:
        """Create the frame (and optional canvas background).

        Returns:
            The outermost widget (tk.Canvas if rounded, else tk.Frame).
        """
        self._load_style()
        bg = self._bg_override or self._bg

        if self._rounded:
            self._outer = tk.Canvas(
                self._parent,
                bg=self._container_bg,
                highlightthickness=0,
                borderwidth=0,
                bd=0,
            )
            self._outer.bind("<Configure>", lambda e: self._redraw_background())
            # Inner content frame placed inside the canvas via create_window.
            self._content = tk.Frame(self._outer, bg=bg)
            self._content_id = self._outer.create_window(
                self._padx, self._pady, window=self._content, anchor="nw"
            )
            self._redraw_background()
            # Keep the content frame stacked above the background items.
            self._outer.tag_raise(self._content_id)
        else:
            self._outer = tk.Frame(
                self._parent,
                bg=bg,
                highlightthickness=0,
                borderwidth=0,
                bd=0,
            )
            self._content = self._outer

        return self._outer

    def pack(self, **kwargs: Any) -> None:
        """Pack the frame into its parent.

        Args:
            **kwargs: Pack configuration options.
        """
        if self._outer:
            self._outer.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the frame into its parent.

        Args:
            **kwargs: Grid configuration options.
        """
        if self._outer:
            self._outer.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the frame and release resources."""
        if self._outer and not self._destroyed:
            self._outer.destroy()
            self._destroyed = True

    def get_widget(self) -> Optional[tk.Misc]:
        """Get the outermost widget.

        Returns:
            The outer widget, or None if not yet created.
        """
        return self._outer

    def get_content(self) -> Optional[tk.Frame]:
        """Get the content frame where child widgets should be placed.

        For non-rounded frames this is the same as the outer widget. For
        rounded frames it is the inner frame layered above the canvas.

        Returns:
            The content frame, or None if not yet created.
        """
        return self._content

    # ---- Style loading ----

    def _load_style(self) -> None:
        """Load frame style values from the StyleSystem singleton."""
        ss = self._style_system
        self._bg = ss.get_value("widget", "bg", "#282c34")
        self._container_bg = ss.get_value("widget", "container_bg", self._bg)
        self._border = ss.get_value("widget", "border", "#3e4451")

    # ---- Rendering ----

    def _redraw_background(self) -> None:
        """Repaint the rounded background and resize the content window.

        Only the background canvas items are removed and redrawn; the
        content window item is preserved and repositioned in place so its
        child widgets keep their state across resize events.
        """
        if not self._rounded or not self._outer or not self._content:
            return
        canvas = self._outer
        # Remove previous background items only (keep the content window).
        for item_id in self._bg_items:
            canvas.delete(item_id)
        self._bg_items = []

        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        bg = self._bg_override or self._bg
        border = self._border_override or self._border
        bw = self._border_width

        # Optional outer border ring drawn first.
        if bw > 0:
            self._bg_items.extend(
                create_rounded_rect(canvas, 0, 0, w, h, self._radius, fill=border)
            )
            self._bg_items.extend(
                create_rounded_rect(
                    canvas, bw, bw, w - bw, h - bw,
                    max(0, self._radius - bw), fill=bg,
                )
            )
        else:
            self._bg_items.extend(
                create_rounded_rect(canvas, 0, 0, w, h, self._radius, fill=bg)
            )

        # Resize and reposition the content window in place.
        if self._content_id is not None:
            canvas.coords(self._content_id, self._padx, self._pady)
            canvas.itemconfigure(
                self._content_id,
                width=max(0, w - 2 * self._padx),
                height=max(0, h - 2 * self._pady),
            )
            canvas.tag_raise(self._content_id)

    # ---- StyleProvider implementation ----

    def apply_style(self, style_name: str) -> None:
        """Apply a named style registered in the StyleSystem.

        Args:
            style_name: Name of the style to apply.
        """
        if self._style_system.apply_style(style_name):
            self._load_style()
            self._refresh_colors()

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
        """Set a style value on the 'widget' section and refresh.

        Args:
            key: Style property key.
            value: New value.
        """
        self._style_system.set_style("widget", key, value)
        self._load_style()
        self._refresh_colors()

    def _refresh_colors(self) -> None:
        """Apply current style colors to the underlying widgets."""
        bg = self._bg_override or self._bg
        if self._content:
            self._content.configure(bg=bg)
        if self._rounded and self._outer:
            self._outer.configure(bg=self._container_bg)
            self._redraw_background()
