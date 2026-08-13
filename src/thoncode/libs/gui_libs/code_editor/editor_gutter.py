#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Editor Gutter",
    "Path": ".main.libs.gui_libs.code_editor.editor_gutter",
    "Entrance": "main.py"
}

"""
Canvas-based editor gutter for line numbers and fold indicators.

Provides a customizable gutter component that renders line numbers
and fold state indicators on a tkinter Canvas, supporting dynamic
updates, click interactions, and theme-based styling.

Rendering is virtualized: only the line numbers intersecting the
current viewport are materialized as Canvas items, and existing items
are reused across scrolls so a 1-pixel scroll only touches the few
lines that entered or left the viewport instead of rebuilding all of
them.
"""

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable, Dict, List, Optional, Set, Tuple

from libs.gui_libs.style_system import StyleSystem


class EditorGutter(tk.Canvas):
    """Canvas-based gutter widget displaying line numbers and fold markers.

    Features:
    - Line numbers with configurable width and styling
    - Fold indicators (expand/collapse) for code blocks
    - Synchronized scrolling with the main text widget
    - Click handling for fold toggling and jump-to-line
    - Theme-aware color and font configuration
    - Virtualized rendering with Canvas item reuse
    """

    FOLD_EXPAND = "\u25BE"    # ▾ expanded (click to collapse) indicator
    FOLD_COLLAPSE = "\u25B8"  # ▸ collapsed (click to expand) indicator

    def __init__(self, parent: tk.Misc, text_widget: tk.Text, **kwargs) -> None:
        """Initialize the editor gutter.

        Args:
            parent: Parent widget for the canvas
            text_widget: Main text widget to synchronize with
            **kwargs: Additional Canvas configuration options
        """
        self.style_system = StyleSystem()
        self._text_widget = text_widget
        self._folded_lines: Dict[int, int] = {}
        self._foldable_starts: Set[int] = set()
        self._line_count: int = 0
        self._font_family: str = "Consolas"
        self._font_size: int = 12
        self._line_height: int = 20
        self._line_number_width: int = 50
        self._fold_gutter_width: int = 20
        self._total_width: int = self._line_number_width + self._fold_gutter_width
        self._bg_color: str = "#282c34"
        self._fg_color: str = "#5c6370"
        self._fg_dim_color: str = "#4b5263"
        self._font: Optional[tkfont.Font] = None
        # Fold indicator glyphs sourced from StyleSystem (with constant fallback).
        self._fold_expand_char: str = self.FOLD_EXPAND
        self._fold_collapse_char: str = self.FOLD_COLLAPSE
        # Canvas item cache: line_num -> item id. Only visible lines have an
        # entry, so off-screen lines cost nothing to maintain.
        self._line_items: Dict[int, int] = {}
        self._fold_items: Dict[int, int] = {}
        self._on_line_click: Optional[Callable[[int], None]] = None
        self._on_fold_click: Optional[Callable[[int], None]] = None

        self._load_style()

        super().__init__(
            parent,
            width=self._total_width,
            bg=self._bg_color,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
            **kwargs
        )

        self._setup_font()
        self._setup_bindings()
        self._refresh()

    def _load_style(self) -> None:
        """Load gutter style configuration from StyleSystem."""
        self._font_family = self.style_system.get_value("editor", "font_family", "Consolas")
        self._font_size = self.style_system.get_value("editor", "font_size", 12)
        self._line_height = self.style_system.get_value("editor", "line_height", 20)
        self._line_number_width = self.style_system.get_value("editor", "line_number_width", 50)
        self._fold_gutter_width = self.style_system.get_value("editor", "fold_gutter_width", 20)
        self._bg_color = self.style_system.get_value("editor", "line_number_bg", "#282c34")
        self._fg_color = self.style_system.get_value("editor", "line_number_fg", "#5c6370")
        # Fold indicator glyphs are theme-configurable via StyleSystem but
        # fall back to the canonical ▾/▸ constants to preserve prior behavior.
        self._fold_expand_char = self.style_system.get_value(
            "editor", "fold_expand_indicator", self.FOLD_EXPAND
        )
        self._fold_collapse_char = self.style_system.get_value(
            "editor", "fold_collapse_indicator", self.FOLD_COLLAPSE
        )

    def _setup_font(self) -> None:
        """Configure the gutter font and derive the real line height.

        The line height is taken from the font linespace so gutter rows align
        with the text-widget lines (both share the same font family/size and
        the editor uses wrap='none', so every line shares one height).
        """
        self._font = tkfont.Font(
            family=self._font_family,
            size=self._font_size
        )
        try:
            linespace = self._font.metrics("linespace")
            if linespace > 0:
                self._line_height = linespace
        except Exception:
            pass  # fall back to the StyleSystem line_height

    def _setup_bindings(self) -> None:
        """Setup mouse and scroll event bindings."""
        self.bind("<Button-1>", self._on_click)
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self._scroll_vertical(-1))
        self.bind("<Button-5>", lambda e: self._scroll_vertical(1))
        self.bind("<Configure>", lambda e: self._refresh())

    def set_on_line_click(self, callback: Callable[[int], None]) -> None:
        """Set callback for line number clicks.

        Args:
            callback: Function receiving line number on click
        """
        self._on_line_click = callback

    def set_on_fold_click(self, callback: Callable[[int], None]) -> None:
        """Set callback for fold indicator clicks.

        Args:
            callback: Function receiving line number on fold toggle
        """
        self._on_fold_click = callback

    def set_foldable_regions(self, regions: List[Tuple[int, int]]) -> None:
        """Set foldable regions for display.

        Args:
            regions: List of (start_line, end_line) tuples
        """
        self._foldable_starts = {start for start, _ in regions}
        self._refresh()

    def set_folded_lines(self, folded: Dict[int, int]) -> None:
        """Set current folded lines state.

        Args:
            folded: Dict mapping start_line to end_line
        """
        self._folded_lines = dict(folded)
        self._refresh()

    def get_folded_lines(self) -> Dict[int, int]:
        """Get current folded lines state.

        Returns:
            Dict mapping start_line to end_line
        """
        return dict(self._folded_lines)

    def _count_lines(self) -> int:
        """Count total lines in the text widget.

        Returns:
            Number of lines
        """
        try:
            return int(self._text_widget.index("end-1c").split(".")[0])
        except Exception:
            return 1

    def _compute_viewport(self) -> Tuple[int, int, float]:
        """Compute the visible line range and pixel y-offset.

        Maps the text-widget fractional yview to concrete line numbers using
        the uniform line height (the editor uses wrap='none' so every line
        shares the same height). Returns (first_line, last_line, y_offset)
        where y_offset is the pixel offset of the virtual content top within
        the canvas coordinate space.
        """
        total = max(1, self._line_count)
        try:
            yview = self._text_widget.yview()
        except Exception:
            yview = (0.0, 1.0)
        top_frac = yview[0] if yview else 0.0
        y_offset = top_frac * total * self._line_height
        canvas_h = max(1, self.winfo_height())
        first_line = max(1, int(y_offset // self._line_height) + 1)
        last_line = min(total, int((y_offset + canvas_h) // self._line_height) + 1)
        # One-line overscan covers partially visible lines at both edges.
        first_line = max(1, first_line - 1)
        last_line = min(total, last_line + 1)
        return first_line, last_line, y_offset

    def _refresh(self) -> None:
        """Redraw visible line numbers and fold indicators (virtualized).

        Only the lines currently intersecting the canvas viewport are
        materialized as Canvas items; off-screen lines are neither created nor
        drawn. Existing items are reused via coords/itemconfigure, and items
        that leave the viewport (or whose fold state changed) are deleted, so
        a small scroll only touches the few lines that changed instead of
        rebuilding the whole gutter.
        """
        if self._font is None:
            return

        self._line_count = self._count_lines()
        first_line, last_line, y_offset = self._compute_viewport()

        # Drop line-number items that scrolled out of the visible window.
        for line_num in list(self._line_items.keys()):
            if line_num < first_line or line_num > last_line:
                self.delete(self._line_items.pop(line_num))

        # Drop fold-indicator items that left the viewport or are no longer
        # foldable start lines.
        for line_num in list(self._fold_items.keys()):
            if (line_num < first_line or line_num > last_line
                    or line_num not in self._foldable_starts):
                self.delete(self._fold_items.pop(line_num))

        number_x = self._line_number_width - 6
        fold_x = self._line_number_width + self._fold_gutter_width // 2

        # (Re)build / reposition items for every visible line.
        for line_num in range(first_line, last_line + 1):
            y1 = (line_num - 1) * self._line_height - y_offset
            display_y = y1 + self._line_height // 2
            text = str(line_num)

            item = self._line_items.get(line_num)
            if item is None:
                item = self.create_text(
                    number_x,
                    display_y,
                    text=text,
                    anchor="e",
                    font=self._font,
                    fill=self._fg_color,
                    tags=("line_number", f"line_{line_num}")
                )
                self._line_items[line_num] = item
            else:
                self.coords(item, number_x, display_y)
                self.itemconfigure(item, text=text, fill=self._fg_color,
                                   font=self._font)

            # Fold indicator only on foldable start lines.
            if line_num in self._foldable_starts:
                if line_num in self._folded_lines:
                    indicator = self._fold_expand_char
                else:
                    indicator = self._fold_collapse_char
                fill = self._fg_color

                fitem = self._fold_items.get(line_num)
                if fitem is None:
                    fitem = self.create_text(
                        fold_x,
                        display_y,
                        text=indicator,
                        anchor="center",
                        font=self._font,
                        fill=fill,
                        tags=("fold_indicator", f"fold_{line_num}")
                    )
                    self._fold_items[line_num] = fitem
                else:
                    self.coords(fitem, fold_x, display_y)
                    self.itemconfigure(fitem, text=indicator, fill=fill,
                                       font=self._font)

    def _on_click(self, event: tk.Event) -> None:
        """Handle click events on the gutter.

        Args:
            event: The mouse click event
        """
        x = event.x
        y = event.y

        total = self._count_lines()
        try:
            yview = self._text_widget.yview()
        except Exception:
            yview = (0.0, 1.0)
        top_frac = yview[0] if yview else 0.0
        y_offset = top_frac * total * self._line_height
        line_num = int((y + y_offset) // self._line_height) + 1

        if x > self._line_number_width:
            if self._on_fold_click and line_num in self._foldable_starts:
                self._on_fold_click(line_num)
        else:
            if self._on_line_click:
                self._on_line_click(line_num)

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel scrolling.

        Args:
            event: The mouse wheel event
        """
        delta = -1 * (event.delta / 120)
        self._scroll_vertical(int(delta))

    def _scroll_vertical(self, direction: int) -> None:
        """Synchronized vertical scrolling.

        Args:
            direction: Scroll direction (-1 up, 1 down)
        """
        self._text_widget.yview_scroll(direction, "units")
        self._refresh()

    def sync_scroll(self) -> None:
        """Synchronize gutter scroll with text widget scroll."""
        self._refresh()

    def get_line_at_y(self, y: int) -> int:
        """Get line number at a given y coordinate.

        Args:
            y: Y coordinate in canvas units

        Returns:
            Line number at the coordinate
        """
        total = self._count_lines()
        try:
            yview = self._text_widget.yview()
        except Exception:
            yview = (0.0, 1.0)
        top_frac = yview[0] if yview else 0.0
        y_offset = top_frac * total * self._line_height
        return max(1, int((y + y_offset) // self._line_height) + 1)

    def redraw(self) -> None:
        """Force a full redraw of the gutter."""
        self._refresh()
