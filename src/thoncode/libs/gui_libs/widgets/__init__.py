#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Widgets Package",
    "Path": ".main.libs.gui_libs.widgets",
    "Entrance": "main.py"
}

"""
Canvas-based themed widget package for gui_libs.

Provides a set of self-painted, theme-aware controls built on tk.Canvas.
Every widget sources its colors and fonts from the StyleSystem singleton
so the application window chrome stays visually consistent across themes.

Components:
- canvas_button: Rounded button with normal/hover/pressed/disabled states.
- canvas_label: Text label with optional icon and alignment.
- canvas_frame: Themed container with optional rounded background.
- canvas_entry: Single-line entry with focus highlight and placeholder.
- canvas_panel: Collapsible panel with a clickable title bar.
- canvas_scrollbar: Custom vertical scrollbar with arrows and slider.
- canvas_statusbar: Multi-segment status bar with separators.
"""

from libs.gui_libs.widgets.canvas_button import CanvasButton, create_rounded_rect
from libs.gui_libs.widgets.canvas_label import CanvasLabel
from libs.gui_libs.widgets.canvas_frame import CanvasFrame
from libs.gui_libs.widgets.canvas_entry import CanvasEntry
from libs.gui_libs.widgets.canvas_panel import CanvasPanel
from libs.gui_libs.widgets.canvas_scrollbar import CanvasScrollbar
from libs.gui_libs.widgets.canvas_statusbar import CanvasStatusBar

__all__ = [
    "CanvasButton",
    "CanvasLabel",
    "CanvasFrame",
    "CanvasEntry",
    "CanvasPanel",
    "CanvasScrollbar",
    "CanvasStatusBar",
    "create_rounded_rect",
]
