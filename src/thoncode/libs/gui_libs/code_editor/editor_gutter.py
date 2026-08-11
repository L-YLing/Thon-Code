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
"""

import tkinter as tk
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
    """

    FOLD_EXPAND = "\u25BE"    # ▸ collapsed indicator
    FOLD_COLLAPSE = "\u25B8"  # ▾ expanded indicator

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
        self._font: Optional[tk.font.Font] = None
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

    def _setup_font(self) -> None:
        """Configure the gutter font based on style settings."""
        self._font = tk.font.Font(
            family=self._font_family,
            size=self._font_size
        )

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

    def _refresh(self) -> None:
        """Redraw the gutter with current line numbers and fold indicators."""
        self.delete("all")
        self._line_count = self._count_lines()

        yview = self._text_widget.yview()
        y_offset = yview[0] * self._line_count * self._line_height

        for line_num in range(1, self._line_count + 1):
            y1 = (line_num - 1) * self._line_height - y_offset
            y2 = y1 + self._line_height

            if y2 < 0 or y1 > self.winfo_height():
                continue

            display_y = y1 + self._line_height // 2

            # Draw line number
            self.create_text(
                self._line_number_width - 6,
                display_y,
                text=str(line_num),
                anchor="e",
                font=self._font,
                fill=self._fg_color,
                tags=("line_number", f"line_{line_num}")
            )

            # Draw fold indicator
            if line_num in self._foldable_starts:
                if line_num in self._folded_lines:
                    indicator = self.FOLD_EXPAND
                    fill = self._fg_color
                else:
                    indicator = self.FOLD_COLLAPSE
                    fill = self._fg_color

                self.create_text(
                    self._line_number_width + self._fold_gutter_width // 2,
                    display_y,
                    text=indicator,
                    anchor="center",
                    font=self._font,
                    fill=fill,
                    tags=("fold_indicator", f"fold_{line_num}")
                )

    def _on_click(self, event: tk.Event) -> None:
        """Handle click events on the gutter.

        Args:
            event: The mouse click event
        """
        x = event.x
        y = event.y

        yview = self._text_widget.yview()
        y_offset = yview[0] * self._line_count * self._line_height
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
        yview = self._text_widget.yview()
        y_offset = yview[0] * self._line_count * self._line_height
        return max(1, int((y + y_offset) // self._line_height) + 1)

    def redraw(self) -> None:
        """Force a full redraw of the gutter."""
        self._refresh()