#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor Highlight",
    "Path": ".main.libs.gui.editor_highlight",
    "Entrance": "main.py"
}

from libs.gui_libs.style_system import StyleSystem


class EditorHighlight:
    """Handles syntax highlighting and bracket matching for the code editor.

    Performance-oriented design:
    - Word index (dict) for O(1) keyword lookup instead of linear group scan.
    - Cached tag_config calls (re-run only when groups change).
    - Viewport highlighting for large files: only the visible region plus a
      buffer is re-tagged, so multi-thousand-line files stay responsive.
    - Debounced highlight scheduling merges rapid keystrokes into one pass.
    - Bracket matching scans locally around the cursor instead of the whole
      document.

    Colors are sourced from StyleSystem singleton for theme consistency.
    """

    # Large-file threshold: files with at least this many lines use viewport
    # highlighting instead of full-document highlighting.
    LARGE_FILE_THRESHOLD = 1500
    # Extra lines highlighted above/below the visible viewport so scrolling
    # does not flash unhighlighted text.
    VIEWPORT_BUFFER = 300
    # Debounce window for key-release triggered highlighting.
    HIGHLIGHT_DEBOUNCE_MS = 80
    # Maximum characters scanned around the cursor for bracket matching.
    BRACKET_SCAN_RADIUS = 20000

    def __init__(self, parent):
        """Initialize the highlight handler.

        Args:
            parent: CodeEditor instance that owns this handler
        """
        self.parent = parent
        self.bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        self._style_system = StyleSystem()
        self._style_system.sync_from_theme()

        # Word -> tag name index for O(1) lookup, rebuilt on groups change.
        self._word_index = {}
        self._index_signature = None
        # Whether tag_config has been applied for the current groups.
        self._tags_configured = False
        # Debounce handle for scheduled highlight passes.
        self._highlight_after_id = None
        # Multiline-comment state cache: (text_version, line, state).
        self._ml_state_cache = (None, 0, False)
        # Tag names managed by this highlighter (for selective clearing).
        self._managed_tags = ("comment", "string", "number", "function", "classname")

    # ------------------------------------------------------------------
    # Index / tag configuration
    # ------------------------------------------------------------------
    def _groups_signature(self):
        """Build a cheap signature of the current groups for cache invalidation.

        Returns:
            A tuple capturing group names, colors and word counts.
        """
        return tuple((g.get("name"), g.get("color"), len(g.get("words", []))) for g in self.parent.groups)

    def _build_word_index(self):
        """Rebuild the word -> tag name lookup dict when groups change.

        Converts the linear `for g in groups: if word in g["words"]` scan
        into a single dict lookup during highlighting.
        """
        index = {}
        for g in self.parent.groups:
            tag = f"kw_{g['name']}"
            for word in g.get("words", []):
                # First group wins, mirroring original break-on-match behavior.
                if word not in index:
                    index[word] = tag
        self._word_index = index
        self._index_signature = self._groups_signature()

    def _ensure_word_index(self):
        """Rebuild the word index if the groups signature has changed."""
        sig = self._groups_signature()
        if sig != self._index_signature:
            self._build_word_index()
            # Groups changed, tag configs need to be refreshed too.
            self._tags_configured = False

    def _ensure_tag_configs(self, text_widget):
        """Apply tag_config once per groups change instead of on every pass.

        Args:
            text_widget: The text widget to configure tags on
        """
        if self._tags_configured:
            return
        for g in self.parent.groups:
            text_widget.tag_config(f"kw_{g['name']}", foreground=g["color"])
        text_widget.tag_config("comment", foreground=self._style_system.get_value("highlight", "comment", "#5C6370"))
        text_widget.tag_config("string", foreground=self._style_system.get_value("highlight", "string", "#98C379"))
        text_widget.tag_config("number", foreground=self._style_system.get_value("highlight", "number", "#D19A66"))
        text_widget.tag_config("function", foreground=self._style_system.get_value("highlight", "function", "#61AFEF"))
        text_widget.tag_config("classname", foreground=self._style_system.get_value("highlight", "classname", "#E5C07B"))
        self._tags_configured = True

    def _invalidate(self):
        """Invalidate caches when the text content or groups change."""
        self._ml_state_cache = (None, 0, False)
        self._tags_configured = False

    # ------------------------------------------------------------------
    # Public highlight API
    # ------------------------------------------------------------------
    def highlight_all(self, event=None):
        """Apply syntax highlighting to the entire document.

        Used for small files and explicit full-refresh requests. For large
        files prefer highlight_visible / schedule_highlight.

        Args:
            event: Optional event that triggered highlighting
        """
        text_widget = self.parent._textbox
        content = text_widget.get("1.0", "end-1c")
        if not content.strip():
            for tag in text_widget.tag_names():
                if tag.startswith("kw_") or tag in self._managed_tags:
                    text_widget.tag_delete(tag)
            self._tags_configured = False
            self._invalidate()
            return

        self._ensure_word_index()
        self._ensure_tag_configs(text_widget)

        lines = content.splitlines(keepends=True)
        line_num = 1
        in_multiline_comment = False
        for line in lines:
            in_multiline_comment = self._highlight_line(text_widget, line_num, line, in_multiline_comment)
            line_num += 1
        # Cache the end-of-document multiline state.
        self._ml_state_cache = (self._text_version(), len(lines) + 1, in_multiline_comment)

    def highlight_visible(self):
        """Highlight only the visible viewport plus a buffer.

        Used for large files. Multiline-comment state is scanned from the
        document start up to the viewport top (cheap state-only scan), then
        the visible region is tagged normally.
        """
        text_widget = self.parent._textbox
        content = text_widget.get("1.0", "end-1c")
        if not content.strip():
            return

        self._ensure_word_index()
        self._ensure_tag_configs(text_widget)

        try:
            total_lines = int(text_widget.index('end-1c').split('.')[0])
        except Exception:
            total_lines = 1

        yview = text_widget.yview()
        first_visible = max(1, int(yview[0] * total_lines))
        last_visible = max(1, int(yview[1] * total_lines))

        start_line = max(1, first_visible - self.VIEWPORT_BUFFER)
        end_line = min(total_lines, last_visible + self.VIEWPORT_BUFFER)

        # Determine multiline-comment state at the viewport start.
        in_multiline_comment = self._multiline_state_before(start_line, content)

        # Clear existing managed tags only within the viewport range.
        for tag in self._managed_tags:
            text_widget.tag_remove(tag, f"{start_line}.0", f"{end_line}.end")
        for g in self.parent.groups:
            text_widget.tag_remove(f"kw_{g['name']}", f"{start_line}.0", f"{end_line}.end")

        lines = content.splitlines(keepends=True)
        for i in range(start_line - 1, min(end_line, len(lines))):
            in_multiline_comment = self._highlight_line(text_widget, i + 1, lines[i], in_multiline_comment)

    def schedule_highlight(self):
        """Debounce highlight requests triggered by rapid keystrokes.

        Selects full vs viewport highlighting based on document size so
        repeated key releases merge into a single pass.
        """
        if self._highlight_after_id is not None:
            try:
                self.parent.master.after_cancel(self._highlight_after_id)
            except Exception:
                pass
        self._highlight_after_id = self.parent.master.after(
            self.HIGHLIGHT_DEBOUNCE_MS, self._run_scheduled_highlight
        )

    def _run_scheduled_highlight(self):
        """Execute the deferred highlight pass chosen by document size."""
        self._highlight_after_id = None
        try:
            total_lines = int(self.parent._textbox.index('end-1c').split('.')[0])
        except Exception:
            total_lines = 1
        if total_lines >= self.LARGE_FILE_THRESHOLD:
            self.highlight_visible()
        else:
            self.highlight_all()
        if self.parent.folding:
            self.parent.folding.apply_all_folds()

    # ------------------------------------------------------------------
    # Line-level highlighting state machine
    # ------------------------------------------------------------------
    def _highlight_line(self, text_widget, line_num, line_text, in_multiline_comment):
        """Highlight syntax elements in a single line of code.

        Args:
            text_widget: The text widget to apply tags to
            line_num: Line number being processed
            line_text: Text content of the line
            in_multiline_comment: Whether we are inside a multi-line comment

        Returns:
            bool: True if the line ends inside a multi-line comment
        """
        n = len(line_text)
        i = 0
        in_string = False
        string_char = None
        in_comment = False
        word_index = self._word_index

        if in_multiline_comment:
            end_idx = line_text.find('"""')
            if end_idx == -1:
                text_widget.tag_add("comment", f"{line_num}.0", f"{line_num}.end")
                return True
            else:
                text_widget.tag_add("comment", f"{line_num}.0", f"{line_num}.{end_idx+3}")
                i = end_idx + 3
                in_multiline_comment = False

        while i < n:
            ch = line_text[i]

            if not in_string and not in_comment and line_text[i:i+3] == '"""':
                start_comment = i
                end_comment = line_text.find('"""', i+3)
                if end_comment == -1:
                    text_widget.tag_add("comment", f"{line_num}.{start_comment}", f"{line_num}.end")
                    return True
                else:
                    text_widget.tag_add("comment", f"{line_num}.{start_comment}", f"{line_num}.{end_comment+3}")
                    i = end_comment + 3
                    continue

            if not in_comment and ch in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = ch
                    start_str = i
                    i += 1
                    continue
                elif ch == string_char:
                    if i > 0 and line_text[i-1] == '\\':
                        i += 1
                        continue
                    else:
                        text_widget.tag_add("string", f"{line_num}.{start_str}", f"{line_num}.{i+1}")
                        in_string = False
                        i += 1
                        continue

            if not in_string and not in_comment and ch == '#':
                in_comment = True
                start_comment = i
                i += 1
                continue

            if in_string:
                i += 1
                continue
            if in_comment:
                text_widget.tag_add("comment", f"{line_num}.{start_comment}", f"{line_num}.end")
                break

            if ch.isdigit() or (ch == '.' and i+1 < n and line_text[i+1].isdigit()):
                start = i
                while i < n and (line_text[i].isdigit() or line_text[i] == '.'):
                    i += 1
                text_widget.tag_add("number", f"{line_num}.{start}", f"{line_num}.{i}")
                continue

            if ch.isalnum() or ch == '_':
                start = i
                while i < n and (line_text[i].isalnum() or line_text[i] == '_'):
                    i += 1
                word = line_text[start:i]
                # O(1) dict lookup replaces the original linear group scan.
                tag = word_index.get(word)
                if tag is not None:
                    text_widget.tag_add(tag, f"{line_num}.{start}", f"{line_num}.{i}")
                else:
                    j = i
                    while j < n and line_text[j].isspace():
                        j += 1
                    if j < n and line_text[j] == '(':
                        text_widget.tag_add("function", f"{line_num}.{start}", f"{line_num}.{i}")
                    prev_word = line_text[:start].strip().split()[-1] if line_text[:start].strip() else ""
                    if prev_word == "class":
                        text_widget.tag_add("classname", f"{line_num}.{start}", f"{line_num}.{i}")
                continue
            else:
                i += 1
        return False

    # ------------------------------------------------------------------
    # Multiline state scanning
    # ------------------------------------------------------------------
    def _text_version(self):
        """Get a cheap content version marker for cache invalidation.

        Returns:
            A tuple of (total chars, last modified flag) used to detect change.
        """
        try:
            tb = self.parent._textbox
            return (tb.index('end-1c'),)
        except Exception:
            return None

    def _multiline_state_before(self, target_line, content):
        """Determine the in-multiline-comment state at the start of target_line.

        Uses a cached state checkpoint so repeated viewport highlights during
        scrolling only scan the newly exposed delta region.

        Args:
            target_line: 1-indexed line whose starting state is needed
            content: Full document content string

        Returns:
            bool: True if target_line starts inside a multi-line comment
        """
        version = self._text_version()
        cached_version, cached_line, cached_state = self._ml_state_cache

        # Fast path: same document and same target line.
        if version == cached_version and target_line == cached_line:
            return cached_state

        lines = content.splitlines(keepends=True)
        if target_line <= 1:
            state = False
            self._ml_state_cache = (version, 1, state)
            return state

        start_idx = 0
        start_state = False
        # Reuse a cached checkpoint when the document is unchanged and the
        # checkpoint is at or before the target line.
        if version == cached_version and 0 < cached_line <= target_line:
            start_idx = cached_line - 1
            start_state = cached_state

        in_ml = start_state
        for i in range(start_idx, min(target_line - 1, len(lines))):
            in_ml = self._scan_line_multiline(lines[i], in_ml)

        self._ml_state_cache = (version, target_line, in_ml)
        return in_ml

    @staticmethod
    def _scan_line_multiline(line_text, in_ml):
        """Track multi-line comment state across a line without tagging.

        Args:
            line_text: Text content of the line
            in_ml: Whether the line starts inside a multi-line comment

        Returns:
            bool: True if the line ends inside a multi-line comment
        """
        if in_ml:
            end_idx = line_text.find('"""')
            if end_idx == -1:
                return True
            i = end_idx + 3
            in_ml = False
        else:
            i = 0
        n = len(line_text)
        in_string = False
        string_char = None
        while i < n:
            ch = line_text[i]
            if not in_string and line_text[i:i+3] == '"""':
                start_comment = i
                end_comment = line_text.find('"""', i+3)
                if end_comment == -1:
                    return True
                i = end_comment + 3
                continue
            if ch in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = ch
                elif ch == string_char:
                    if i > 0 and line_text[i-1] == '\\':
                        pass
                    else:
                        in_string = False
            i += 1
        return False

    # ------------------------------------------------------------------
    # Bracket matching
    # ------------------------------------------------------------------
    def highlight_matching_bracket(self):
        """Highlight matching brackets at the cursor position."""
        text_widget = self.parent._textbox
        try:
            text_widget.tag_remove("bracket_match", "1.0", "end")
        except Exception:
            pass
        cursor_index = text_widget.index("insert")
        char = text_widget.get(cursor_index, f"{cursor_index}+1c")
        if char in self.bracket_pairs:
            open_char = char
            close_char = self.bracket_pairs[open_char]
            match_pos = self.find_matching_bracket(text_widget, cursor_index, open_char, close_char)
            if match_pos:
                text_widget.tag_add("bracket_match", cursor_index, f"{cursor_index}+1c")
                text_widget.tag_add("bracket_match", match_pos, f"{match_pos}+1c")
                text_widget.tag_config("bracket_match", background=self._style_system.get_value("highlight", "bracket_match_bg", "#FFFF00"))

    def find_matching_bracket(self, text_widget, start_idx, open_ch, close_ch):
        """Find a matching bracket character using a local bidirectional scan.

        Scans a bounded window around the cursor instead of extracting and
        scanning the entire document, keeping cursor-move bracket matching
        constant-time for large files.

        Args:
            text_widget: The text widget to search in
            start_idx: Starting index position
            open_ch: Opening bracket character
            close_ch: Closing bracket character

        Returns:
            Index of the matching bracket, or None if not found
        """
        # Convert cursor index to a flat character offset from "1.0".
        try:
            cursor_line, cursor_col = map(int, start_idx.split('.'))
            # Estimate the flat offset by fetching the text before the cursor.
            # For an opening bracket the match is forward, so fetch a window
            # forward; the before-text is only needed for the offset.
            if open_ch in self.bracket_pairs:
                # Forward search: take a window after the cursor.
                window = text_widget.get(start_idx, f"{start_idx}+{self.BRACKET_SCAN_RADIUS}c")
                stack = []
                for offset, ch in enumerate(window):
                    if ch == open_ch:
                        stack.append(offset)
                    elif ch == close_ch:
                        if stack:
                            popped = stack.pop()
                            if popped == 0:
                                return text_widget.index(f"{start_idx}+{offset}c")
                return None
        except Exception:
            pass
        return None
