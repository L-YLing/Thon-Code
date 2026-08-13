#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Panel",
    "Path": ".main.libs.gui_libs.widgets.canvas_panel",
    "Entrance": "main.py"
}

"""
Canvas-based collapsible panel widget.

A panel is composed of a clickable title bar (rendered on a tk.Canvas with
a fold/expand arrow indicator and the title text) and a content frame that
hosts child widgets. Clicking the title bar toggles the content area
between expanded and collapsed states. Colors, fonts and arrow glyphs are
sourced from the StyleSystem singleton.
"""

import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable, Optional

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider


class CanvasPanel(BaseWidget, StyleProvider):
    """Collapsible panel with a canvas title bar and content frame.

    The title bar is painted on a tk.Canvas so the fold indicator and
    title text share a single themed surface. The content area is a plain
    tk.Frame returned by :meth:`get_content` into which child widgets can
    be packed or gridded.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the collapsible panel.

        Args:
            parent: Parent Tkinter widget.
            **kwargs: Optional configuration. Recognized keys:
                title (str): Panel title text.
                expanded (bool): Initial expanded state. Defaults to True.
                title_height (int): Title bar height in pixels.
                on_toggle (Callable[[bool], None]): Callback receiving the
                    new expanded state when the panel is toggled.
        """
        self._parent = parent
        self._outer: Optional[tk.Frame] = None
        self._title_canvas: Optional[tk.Canvas] = None
        self._content: Optional[tk.Frame] = None
        self._font: Optional[tkfont.Font] = None

        self._title: str = kwargs.get("title", "")
        self._expanded: bool = bool(kwargs.get("expanded", True))
        self._title_height: int = int(kwargs.get("title_height", 26))
        self._on_toggle: Optional[Callable[[bool], None]] = kwargs.get("on_toggle", None)

        # Style values (populated by _load_style).
        self._bg: str = "#282c34"
        self._bg_alt: str = "#21252b"
        self._fg: str = "#abb2bf"
        self._hover_bg: str = "#3e4451"
        self._border: str = "#3e4451"
        self._accent: str = "#528bff"
        self._font_family: str = "Microsoft YaHei"
        self._font_size: int = 10
        self._expand_indicator: str = "▾"
        self._collapse_indicator: str = "▸"

        self._title_hover: bool = False

        self._style_system = StyleSystem()
        super().__init__(parent)

    # ---- BaseWidget implementation ----

    def create_widget(self) -> tk.Frame:
        """Create the panel layout: title bar above content frame.

        Returns:
            The outer frame containing the title bar and content.
        """
        self._load_style()
        self._font = tkfont.Font(family=self._font_family, size=self._font_size)

        self._outer = tk.Frame(self._parent, bg=self._border, bd=0)
        self._title_canvas = tk.Canvas(
            self._outer,
            height=self._title_height,
            bg=self._bg_alt,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
            cursor="hand2",
        )
        self._title_canvas.pack(side="top", fill="x")

        self._content = tk.Frame(self._outer, bg=self._bg)
        if self._expanded:
            self._content.pack(side="top", fill="both", expand=True)

        self._setup_bindings()
        self._redraw_title()
        return self._outer

    def pack(self, **kwargs: Any) -> None:
        """Pack the panel into its parent.

        Args:
            **kwargs: Pack configuration options.
        """
        if self._outer:
            self._outer.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the panel into its parent.

        Args:
            **kwargs: Grid configuration options.
        """
        if self._outer:
            self._outer.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the panel and release resources."""
        if self._outer and not self._destroyed:
            self._outer.destroy()
            self._destroyed = True

    def get_widget(self) -> Optional[tk.Frame]:
        """Get the outer frame.

        Returns:
            The outer frame, or None if not yet created.
        """
        return self._outer

    def get_content(self) -> Optional[tk.Frame]:
        """Get the content frame for placing child widgets.

        Returns:
            The content frame, or None if not yet created.
        """
        return self._content

    # ---- Style loading ----

    def _load_style(self) -> None:
        """Load panel style values from the StyleSystem singleton."""
        ss = self._style_system
        self._bg = ss.get_value("widget", "bg", "#282c34")
        self._bg_alt = ss.get_value("widget", "bg_alt", "#21252b")
        self._fg = ss.get_value("widget", "fg", "#abb2bf")
        self._hover_bg = ss.get_value("widget", "hover_bg", "#3e4451")
        self._border = ss.get_value("widget", "border", "#3e4451")
        self._accent = ss.get_value("widget", "accent", "#528bff")
        self._font_family = ss.get_value("widget", "font_family", "Microsoft YaHei")
        self._font_size = ss.get_value("widget", "font_size", 10)
        self._expand_indicator = ss.get_value("tree", "expand_indicator", "▾")
        self._collapse_indicator = ss.get_value("tree", "collapse_indicator", "▸")

    # ---- Event handling ----

    def _setup_bindings(self) -> None:
        """Bind title bar hover and click events."""
        if not self._title_canvas:
            return
        self._title_canvas.bind("<Button-1>", self._on_title_click)
        self._title_canvas.bind("<Enter>", self._on_title_enter)
        self._title_canvas.bind("<Leave>", self._on_title_leave)
        self._title_canvas.bind("<Configure>", lambda e: self._redraw_title())

    def _on_title_enter(self, event: tk.Event) -> None:
        """Highlight the title bar on hover.

        Args:
            event: The mouse enter event.
        """
        self._title_hover = True
        self._redraw_title()

    def _on_title_leave(self, event: tk.Event) -> None:
        """Remove the title bar highlight on leave.

        Args:
            event: The mouse leave event.
        """
        self._title_hover = False
        self._redraw_title()

    def _on_title_click(self, event: tk.Event) -> None:
        """Toggle the expanded/collapsed state.

        Args:
            event: The mouse click event.
        """
        self.toggle()

    # ---- Rendering ----

    def _redraw_title(self) -> None:
        """Repaint the title bar with the current indicator and text."""
        if not self._title_canvas:
            return
        canvas = self._title_canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            w = 200
        if h <= 1:
            h = self._title_height

        bg = self._hover_bg if self._title_hover else self._bg_alt
        canvas.configure(bg=bg)
        canvas.create_rectangle(0, 0, w, h, fill=bg, outline="")

        indicator = self._expand_indicator if self._expanded else self._collapse_indicator
        pad_x = 8
        cy = h / 2.0
        canvas.create_text(
            pad_x, cy, text=indicator, anchor="w", font=self._font, fill=self._accent,
        )
        if self._title:
            canvas.create_text(
                pad_x + 18, cy, text=self._title, anchor="w",
                font=self._font, fill=self._fg,
            )

    # ---- Public API ----

    def toggle(self) -> None:
        """Toggle between expanded and collapsed states."""
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        """Set the expanded/collapsed state explicitly.

        Args:
            expanded: True to expand, False to collapse.
        """
        if expanded == self._expanded:
            return
        self._expanded = expanded
        if self._content:
            if expanded:
                self._content.pack(side="top", fill="both", expand=True)
            else:
                self._content.pack_forget()
        self._redraw_title()
        if self._on_toggle:
            try:
                self._on_toggle(expanded)
            except Exception:
                pass

    def is_expanded(self) -> bool:
        """Return whether the panel is currently expanded.

        Returns:
            True if the panel is expanded.
        """
        return self._expanded

    def set_title(self, title: str) -> None:
        """Update the panel title text.

        Args:
            title: New title text.
        """
        self._title = title
        self._redraw_title()

    def set_on_toggle(self, callback: Callable[[bool], None]) -> None:
        """Set the toggle callback.

        Args:
            callback: Function receiving the new expanded state.
        """
        self._on_toggle = callback

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
        """Apply current style colors to the panel sub-widgets."""
        if self._font:
            self._font.configure(family=self._font_family, size=self._font_size)
        if self._outer:
            self._outer.configure(bg=self._border)
        if self._content:
            self._content.configure(bg=self._bg)
        self._redraw_title()
