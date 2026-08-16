#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.gui.editor_folding",
    "Entrance": "main.py"
}

from libs.gui_libs.style_system import StyleSystem


class EditorFolding:
    """Editor code folding handler.

    Uses tk.Text's elide tag to implement real text hiding,
    fold state is stored uniformly in parent._folded_lines to avoid dual dictionary desync.
    Fold indicators are drawn by the Canvas gutter (EditorGutter).

    Supports two folding strategies:
    - Indentation-based (Python): blocks defined by increased indent after def/class
    - Brace-based (Java, Rust, C/C++, JS/TS, Go, etc.): blocks defined by { } pairs

    Performance: foldable regions are cached and invalidated by a content
    version marker, so get_fold_marker / _get_foldable_regions no longer
    re-scan the whole document on every line-number refresh.
    """

    # Elide tag name used for fold regions
    FOLD_TAG = "fold_elided"

    # Languages that use brace-based folding
    BRACE_LANGUAGES = frozenset({
        "java", "rust", "c", "cpp", "javascript", "typescript",
        "go", "php", "ruby", "csharp", "kotlin", "swift", "scala",
    })

    def __init__(self, parent):
        """Initialize folding handler.

        Args:
            parent: CodeEditor instance, provides _textbox, language, tab_size, etc.
        """
        self.parent = parent
        self._style_system = StyleSystem()
        self._style_system.sync_from_theme()
        # Fold state uses parent._folded_lines uniformly.
        # Cached foldable regions: (version, regions, foldable_starts_set).
        self._regions_cache = (None, [], set())

    @property
    def _collapse_indicator(self) -> str:
        """Get the collapse indicator character from style system."""
        return self._style_system.get_value("tree", "expand_indicator", "\u25BE")

    @property
    def _expand_indicator(self) -> str:
        """Get the expand indicator character from style system."""
        return self._style_system.get_value("tree", "collapse_indicator", "\u25B8")

    def _ensure_fold_tag(self):
        """Ensure elide tag is configured, needs to be recreated after highlight_all clears tags"""
        tb = self.parent._textbox
        tb.tag_config(self.FOLD_TAG, elide=True)

    def _content_version(self):
        """Get a cheap content version marker for cache invalidation."""
        try:
            return self.parent._textbox.index('end-1c')
        except Exception:
            return None

    def _invalidate_regions_cache(self):
        """Invalidate the cached foldable regions."""
        self._regions_cache = (None, [], set())

    def _get_foldable_regions(self):
        """Scan full text, return list of foldable regions.

        Dispatches to language-specific strategies. Results are cached per
        content version so repeated calls during gutter refreshes do not
        re-scan the whole document.

        Returns:
            list[tuple[int, int]]: Each element is (start_line, end_line),
            1-indexed; start line is the definition/opening-brace line,
            end line is the last line of the block.
        """
        language = self.parent.language

        if language == "python":
            return self._get_python_foldable_regions()
        elif language in self.BRACE_LANGUAGES:
            return self._get_brace_foldable_regions()
        else:
            self._regions_cache = (None, [], set())
            return []

    def _get_python_foldable_regions(self):
        """Find foldable regions in Python using indentation rules.

        Returns:
            list[tuple[int, int]]: (start_line, end_line) pairs
        """
        version = self._content_version()
        cached_version, cached_regions, cached_starts = self._regions_cache
        if version == cached_version:
            return cached_regions

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

            base_indent = len(line) - len(line.lstrip(' '))
            min_child_indent = base_indent + tab_size
            end_line_idx = self._find_block_end(lines, i, min_child_indent)
            if end_line_idx > i + 1:
                fold_regions.append((i + 1, end_line_idx))

        foldable_starts = {start for start, _ in fold_regions}
        self._regions_cache = (version, fold_regions, foldable_starts)
        return fold_regions

    def _get_brace_foldable_regions(self):
        """Find foldable regions in brace-based languages.

        Tracks { } pairs while skipping string literals and comments to
        identify multi-line blocks that can be folded.

        Returns:
            list[tuple[int, int]]: (start_line, end_line) pairs
        """
        version = self._content_version()
        cached_version, cached_regions, cached_starts = self._regions_cache
        if version == cached_version:
            return cached_regions

        content = self.parent._textbox.get("1.0", "end-1c")
        lines = content.splitlines()
        fold_regions = []

        stack = []  # Stack of line_num (1-indexed) for open braces
        in_block_comment = False

        for line_idx, line in enumerate(lines):
            line_num = line_idx + 1
            in_string = None
            i = 0
            while i < len(line):
                ch = line[i]
                # Handle string literals
                if in_string:
                    if ch == '\\' and i + 1 < len(line):
                        i += 1  # Skip escaped char
                    elif ch == in_string:
                        in_string = None
                elif in_block_comment:
                    if i < len(line) - 1 and ch == '*' and line[i + 1] == '/':
                        in_block_comment = False
                        i += 1
                elif i < len(line) - 1 and ch == '/' and line[i + 1] == '/':
                    break  # Line comment — rest of line ignored
                elif i < len(line) - 1 and ch == '/' and line[i + 1] == '*':
                    in_block_comment = True
                    i += 1
                elif ch in ('"', "'", '`'):
                    in_string = ch
                elif ch == '{':
                    stack.append(line_num)
                elif ch == '}':
                    if stack:
                        start = stack.pop()
                        if start != line_num:
                            fold_regions.append((start, line_num))
                i += 1

        foldable_starts = {start for start, _ in fold_regions}
        self._regions_cache = (version, fold_regions, foldable_starts)
        return fold_regions

    def _get_foldable_starts(self):
        """Return the cached set of foldable start line numbers.

        Returns:
            set[int]: 1-indexed line numbers that begin a foldable region
        """
        self._get_foldable_regions()
        return self._regions_cache[2]

    def _find_block_end(self, lines, start_idx, min_indent):
        """Find the end position of a code block (Python indentation-based).

        Args:
            lines: Full text line list (0-indexed)
            start_idx: 0-indexed position of definition line in lines
            min_indent: Minimum indentation columns required for child block
        Returns:
            int: 0-index of the first line not belonging to the child block
        """
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(' '))
            if indent < min_indent:
                return i
        return len(lines)

    def toggle_fold(self, line_num):
        """Toggle fold/unfold state of the specified line

        Args:
            line_num: 1-indexed line number, should be a foldable start line
        """
        folded = self.parent._folded_lines

        if line_num in folded:
            self._unfold(line_num)
        else:
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
        tb.tag_remove(self.FOLD_TAG, f"{start_line + 1}.0", f"{end_line}.end")

        if start_line in self.parent._folded_lines:
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

        Uses the cached foldable starts set for O(1) lookup instead of
        re-scanning the whole document on every call.

        Args:
            line_num: 1-indexed line number
        Returns:
            str: Collapse indicator means foldable (expanded),
                 Expand indicator means folded, '' means not foldable
        """
        if line_num in self.parent._folded_lines:
            return self._expand_indicator
        if line_num in self._get_foldable_starts():
            return self._collapse_indicator
        return ''
