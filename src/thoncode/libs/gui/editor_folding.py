#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.gui.editor_folding",
    "Entrance": "main.py"
}

from libs.gui_libs.style_system import StyleSystem


class EditorFolding:
    """Editor code folding handler

    Uses tk.Text's elide tag to implement real text hiding,
    fold state is stored uniformly in parent._folded_lines to avoid dual dictionary desync.
    Fold indicators are sourced from StyleSystem for consistent configurable display.
    """

    # Elide tag name used for fold regions
    FOLD_TAG = "fold_elided"

    def __init__(self, parent):
        """Initialize folding handler

        Args:
            parent: CodeEditor instance, provides _textbox, language, tab_size, etc.
        """
        self.parent = parent
        self._style_system = StyleSystem()
        self._style_system.sync_from_theme()
        # Fold state uses parent._folded_lines uniformly, no longer maintains independent dictionary

    @property
    def _collapse_indicator(self) -> str:
        """Get the collapse indicator character from style system.

        Returns:
            str: Character used to indicate collapsible (expanded) state
        """
        return self._style_system.get_value("tree", "expand_indicator", "▾")

    @property
    def _expand_indicator(self) -> str:
        """Get the expand indicator character from style system.

        Returns:
            str: Character used to indicate folded (collapsed) state
        """
        return self._style_system.get_value("tree", "collapse_indicator", "▸")

    def _ensure_fold_tag(self):
        """Ensure elide tag is configured, needs to be recreated after highlight_all clears tags"""
        tb = self.parent._textbox
        # elide=True makes tagged text hidden and non-editable
        tb.tag_config(self.FOLD_TAG, elide=True)

    def _get_foldable_regions(self):
        """Scan full text, return list of foldable regions

        Returns:
            list[tuple[int, int]]: Each element is (start line number, end line number), line numbers start from 1;
            start line is the def/class definition line, end line is the line number of the last line of the block
        """
        if self.parent.language != "python":
            return []

        content = self.parent._textbox.get("1.0", "end-1c")
        lines = content.splitlines()
        fold_regions = []
        tab_size = getattr(self.parent, 'tab_size', 4)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not (stripped.startswith('def ') or
                    stripped.startswith('async def ') or
                    stripped.startswith('class ')):
                continue

            # Current line indentation
            base_indent = len(line) - len(line.lstrip(' '))
            # Child block indent threshold: at least one tab_size more than the definition line
            min_child_indent = base_indent + tab_size
            # _find_block_end uses 0-indexed line numbers
            end_line_idx = self._find_block_end(lines, i, min_child_indent)
            # Convert to 1-indexed line numbers: end_line_idx is 0-indexed "first line after block" or end of file
            # Last line of block is end_line_idx - 1 (0-indexed) = end_line_idx (1-indexed)
            end_line_1based = end_line_idx  # 0-index+1-1 = 0-index, but we want the last line in 1-index
            # _find_block_end returns the first line not belonging to the child block (0-indexed), last line of block is that value - 1 (0-indexed) = that value (1-indexed)
            # If it returns len(lines), the last line of the block is len(lines) (1-indexed)
            if end_line_idx > i + 1:
                fold_regions.append((i + 1, end_line_idx))

        return fold_regions

    def _find_block_end(self, lines, start_idx, min_indent):
        """Find the end position of a code block

        Args:
            lines: Full text line list (0-indexed)
            start_idx: 0-indexed position of definition line in lines
            min_indent: Minimum indentation columns required for child block
        Returns:
            int: 0-index of the first line not belonging to the child block (i.e., the line after the last line of the block);
            returns len(lines) if end of file is reached
        """
        # Start scanning from the line after the definition line
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                # Skip empty lines, do not interrupt the block
                continue
            indent = len(line) - len(line.lstrip(' '))
            if indent < min_indent:
                # Encounter a line with smaller indentation, block ends before this line
                return i
        return len(lines)

    def toggle_fold(self, line_num):
        """Toggle fold/unfold state of the specified line

        Args:
            line_num: 1-indexed line number, should be a def/class definition line
        """
        folded = self.parent._folded_lines

        if line_num in folded:
            # Folded → unfold
            self._unfold(line_num)
        else:
            # Not folded → attempt fold
            fold_regions = self._get_foldable_regions()
            for start, end in fold_regions:
                if start == line_num and end > start:
                    self._fold(start, end)
                    break

        # Refresh display
        self.parent.highlight_all()
        self.parent._update_line_numbers()

    def _fold(self, start_line, end_line):
        """Fold lines from start_line+1 to end_line (keep definition line visible)

        Args:
            start_line: Definition line (1-indexed)
            end_line: Last line of block (1-indexed)
        """
        self.parent._folded_lines[start_line] = end_line
        self._apply_fold(start_line, end_line)

    def _unfold(self, start_line):
        """Unfold the fold region starting at the specified line

        Args:
            start_line: Definition line (1-indexed)
        """
        end_line = self.parent._folded_lines.pop(start_line, None)
        if end_line is None:
            return
        self._apply_fold(start_line, end_line)

    def _apply_fold(self, start_line, end_line):
        """Apply elide tag to a single fold region

        Args:
            start_line: Definition line (1-indexed)
            end_line: Last line of block (1-indexed)
        """
        tb = self.parent._textbox
        self._ensure_fold_tag()
        # First clear existing fold tags in this region (avoid duplicates)
        tb.tag_remove(self.FOLD_TAG, f"{start_line + 1}.0", f"{end_line}.end")

        if start_line in self.parent._folded_lines:
            # Fold: hide content after the definition line to the end of the block
            tb.tag_add(self.FOLD_TAG, f"{start_line + 1}.0", f"{end_line}.end")

    def apply_all_folds(self):
        """Reapply all recorded fold states

        Called after highlight_all clears tags to restore fold display.
        """
        self._ensure_fold_tag()
        for start_line, end_line in list(self.parent._folded_lines.items()):
            self._apply_fold(start_line, end_line)

    def is_folded(self, line_num):
        """Determine if the specified line is in a folded state

        Args:
            line_num: 1-indexed line number
        Returns:
            bool: True indicates the line is the start of a fold region
        """
        return line_num in self.parent._folded_lines

    def get_fold_marker(self, line_num):
        """Get the fold marker character for the specified line

        Args:
            line_num: 1-indexed line number
        Returns:
            str: Collapse indicator means foldable (expanded),
                 Expand indicator means folded, '' means not foldable
        """
        if line_num in self.parent._folded_lines:
            return self._expand_indicator  # Folded, click to unfold
        # Check if it is the start of a foldable region
        for start, end in self._get_foldable_regions():
            if start == line_num and end > start:
                return self._collapse_indicator  # Foldable, click to fold
        return ''
