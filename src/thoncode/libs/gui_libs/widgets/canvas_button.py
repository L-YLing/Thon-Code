#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Button",
    "Path": ".main.libs.gui_libs.widgets.canvas_button",
    "Entrance": "main.py"
}

"""
Canvas-based themed button widget.

Draws a fully self-painted button on a tk.Canvas with four visual states
(normal, hover, pressed, disabled), rounded-rectangle background, centered
text, and a command callback. All colors and fonts are sourced from the
StyleSystem singleton so the control stays consistent with the rest of the
application window chrome.
"""

import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable, List, Optional

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider


def create_rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    fill: str,
    outline: str = "",
) -> List[int]:
    """Draw a filled rounded rectangle on a canvas.

    The shape is composed of two overlapping center rectangles plus four
    quarter-circle pie slices in the corners. The radius is clamped so it
    can never exceed half of the smaller dimension, which keeps the corners
    from collapsing or drawing out of bounds.

    Args:
        canvas: Target canvas widget.
        x1: Left coordinate.
        y1: Top coordinate.
        x2: Right coordinate.
        y2: Bottom coordinate.
        radius: Corner radius in pixels.
        fill: Fill color.
        outline: Outline color (empty string for no outline).

    Returns:
        List of canvas item ids that form the rounded rectangle.
    """
    width = x2 - x1
    height = y2 - y1
    r = max(0.0, min(radius, width / 2.0, height / 2.0))
    if r < 1.0:
        return [canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline)]

    items: List[int] = []
    # Center horizontal band (full height, inset by the corner radius).
    items.append(
        canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
    )
    # Center vertical band (full width, inset by the corner radius).
    items.append(
        canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
    )
    # Four corner pie slices forming the rounded corners.
    items.append(
        canvas.create_arc(
            x1, y1, x1 + 2 * r, y1 + 2 * r,
            start=90, extent=90, style=tk.PIESLICE, fill=fill, outline="",
        )
    )
    items.append(
        canvas.create_arc(
            x2 - 2 * r, y1, x2, y1 + 2 * r,
            start=0, extent=90, style=tk.PIESLICE, fill=fill, outline="",
        )
    )
    items.append(
        canvas.create_arc(
            x1, y2 - 2 * r, x1 + 2 * r, y2,
            start=180, extent=90, style=tk.PIESLICE, fill=fill, outline="",
        )
    )
    items.append(
        canvas.create_arc(
            x2 - 2 * r, y2 - 2 * r, x2, y2,
            start=270, extent=90, style=tk.PIESLICE, fill=fill, outline="",
        )
    )
    return items


class CanvasButton(BaseWidget, StyleProvider):
    """Canvas-painted button with theme-aware states and rounded corners.

    The button supports four visual states (normal, hover, pressed,
    disabled) and renders a rounded-rectangle background with centered
    text. Colors, fonts, corner radius and padding are read from the
    StyleSystem singleton so the control blends with the rest of the UI.

    Attributes:
        STATE_NORMAL: Identifier for the normal state.
        STATE_HOVER: Identifier for the hover state.
        STATE_PRESSED: Identifier for the pressed state.
        STATE_DISABLED: Identifier for the disabled state.
    """

    STATE_NORMAL = "normal"
    STATE_HOVER = "hover"
    STATE_PRESSED = "pressed"
    STATE_DISABLED = "disabled"

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the canvas button.

        Args:
            parent: Parent Tkinter widget.
            **kwargs: Optional configuration. Recognized keys:
                text (str): Button label text.
                command (Callable): Callback invoked on click.
                width (int): Button width in pixels.
                height (int): Button height in pixels.
                radius (int): Corner radius in pixels.
                accent (bool): Use the accent color for the normal fill.
                enabled (bool): Initial enabled state.
        """
        self._parent = parent
        self._canvas: Optional[tk.Canvas] = None
        self._font: Optional[tkfont.Font] = None

        self._text: str = kwargs.get("text", "")
        self._command: Optional[Callable[[], None]] = kwargs.get("command", None)
        self._width: int = int(kwargs.get("width", 80))
        self._height: int = int(kwargs.get("height", 30))
        self._radius: int = int(kwargs.get("radius", 6))
        self._accent: bool = bool(kwargs.get("accent", False))
        self._enabled: bool = bool(kwargs.get("enabled", True))

        self._state: str = self.STATE_NORMAL
        if not self._enabled:
            self._state = self.STATE_DISABLED

        # Style values (populated by _load_style).
        self._bg: str = "#282c34"
        self._button_bg: str = "#3e4451"
        self._fg: str = "#abb2bf"
        self._hover_bg: str = "#4b5263"
        self._pressed_bg: str = "#5c6370"
        self._disabled_bg: str = "#2c313c"
        self._disabled_fg: str = "#5c6370"
        self._accent_color: str = "#528bff"
        self._accent_fg: str = "#ffffff"
        self._font_family: str = "Microsoft YaHei"
        self._font_size: int = 10

        self._style_system = StyleSystem()
        super().__init__(parent)

    # ---- BaseWidget implementation ----

    def create_widget(self) -> tk.Canvas:
        """Create the canvas and paint the initial button.

        Returns:
            The tk.Canvas that hosts the button.
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
        self._setup_bindings()
        self._redraw()
        return self._canvas

    def pack(self, **kwargs: Any) -> None:
        """Pack the button into its parent.

        Args:
            **kwargs: Pack configuration options.
        """
        if self._canvas:
            self._canvas.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the button into its parent.

        Args:
            **kwargs: Grid configuration options.
        """
        if self._canvas:
            self._canvas.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the button and release resources."""
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
        """Load button style values from the StyleSystem singleton."""
        ss = self._style_system
        self._bg = ss.get_value("widget", "bg", "#282c34")
        self._button_bg = ss.get_value("widget", "button_bg", "#3e4451")
        self._fg = ss.get_value("widget", "fg", "#abb2bf")
        self._hover_bg = ss.get_value("widget", "hover_bg", "#4b5263")
        self._pressed_bg = ss.get_value("widget", "pressed_bg", "#5c6370")
        self._disabled_bg = ss.get_value("widget", "disabled_bg", "#2c313c")
        self._disabled_fg = ss.get_value("widget", "disabled_fg", "#5c6370")
        self._accent_color = ss.get_value("widget", "accent", "#528bff")
        self._accent_fg = ss.get_value("widget", "accent_fg", "#ffffff")
        self._font_family = ss.get_value("widget", "font_family", "Microsoft YaHei")
        self._font_size = ss.get_value("widget", "font_size", 10)
        self._radius = ss.get_value("widget", "radius", 6)

    # ---- Event handling ----

    def _setup_bindings(self) -> None:
        """Bind mouse events that drive the button state machine."""
        canvas = self._canvas
        canvas.bind("<Enter>", self._on_enter)
        canvas.bind("<Leave>", self._on_leave)
        canvas.bind("<Button-1>", self._on_press)
        canvas.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event: tk.Event) -> None:
        """Switch to the hover state when the pointer enters the button.

        Args:
            event: The mouse enter event.
        """
        if self._enabled:
            self._set_state(self.STATE_HOVER)

    def _on_leave(self, event: tk.Event) -> None:
        """Return to the normal state when the pointer leaves the button.

        Args:
            event: The mouse leave event.
        """
        if self._enabled:
            self._set_state(self.STATE_NORMAL)

    def _on_press(self, event: tk.Event) -> None:
        """Switch to the pressed state on left mouse button down.

        Args:
            event: The mouse press event.
        """
        if self._enabled:
            self._set_state(self.STATE_PRESSED)

    def _on_release(self, event: tk.Event) -> None:
        """Restore hover state and fire the command on left button release.

        Args:
            event: The mouse release event.
        """
        if not self._enabled:
            return
        # Only fire the command when the release happens inside the button.
        if self._state == self.STATE_PRESSED:
            self._set_state(self.STATE_HOVER)
            if self._command:
                try:
                    self._command()
                except Exception:
                    pass

    # ---- Rendering ----

    def _set_state(self, state: str) -> None:
        """Update the visual state and repaint.

        Args:
            state: One of the STATE_* constants.
        """
        if self._state == state:
            return
        self._state = state
        self._redraw()

    def _current_fill(self) -> str:
        """Resolve the background color for the current state.

        Returns:
            The fill color string.
        """
        if self._state == self.STATE_DISABLED:
            return self._disabled_bg
        if self._accent:
            return self._accent_color
        if self._state == self.STATE_HOVER:
            return self._hover_bg
        if self._state == self.STATE_PRESSED:
            return self._pressed_bg
        return self._button_bg

    def _current_fg(self) -> str:
        """Resolve the text color for the current state.

        Returns:
            The foreground color string.
        """
        if self._state == self.STATE_DISABLED:
            return self._disabled_fg
        if self._accent:
            return self._accent_fg
        return self._fg

    def _redraw(self) -> None:
        """Repaint the entire button on the canvas."""
        if not self._canvas:
            return
        self._canvas.delete("all")
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        # Fall back to requested size before the canvas has been mapped.
        if w <= 1:
            w = self._width
        if h <= 1:
            h = self._height

        fill = self._current_fill()
        create_rounded_rect(
            self._canvas, 0, 0, w, h, self._radius, fill=fill
        )

        if self._text:
            self._canvas.create_text(
                w / 2.0,
                h / 2.0,
                text=self._text,
                fill=self._current_fg(),
                font=self._font,
            )

    # ---- Public API ----

    def set_text(self, text: str) -> None:
        """Update the button label text and repaint.

        Args:
            text: New label text.
        """
        self._text = text
        self._redraw()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the button.

        Args:
            enabled: True to enable, False to disable.
        """
        self._enabled = enabled
        self._state = self.STATE_NORMAL if enabled else self.STATE_DISABLED
        self._redraw()

    def set_command(self, command: Callable[[], None]) -> None:
        """Set the click callback.

        Args:
            command: Callable invoked when the button is released.
        """
        self._command = command

    def configure_style(self, **kwargs: Any) -> None:
        """Override one or more style values and repaint.

        Args:
            **kwargs: Style keys to override on the StyleSystem 'widget'
                section (e.g. button_bg, fg, radius).
        """
        for key, value in kwargs.items():
            self._style_system.set_style("widget", key, value)
        self._load_style()
        if self._font:
            self._font.configure(family=self._font_family, size=self._font_size)
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
