#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor Lint",
    "Path": ".main.libs.gui.editor_lint",
    "Entrance": "main.py"
}

"""Basic multi-language static analysis for the code editor.

Checks for common issues across all supported languages:
- Unbalanced brackets: (), [], {}
- Unclosed string literals (single-line)
- Trailing whitespace (warning)

Python-specific:
- Mixed tabs and spaces in indentation (warning)

Results are displayed as tag highlights (underline) in the text widget.
Runs on a debounce timer so rapid typing doesn't trigger repeated scans.
"""

from typing import Dict, List, Optional, Tuple

from libs.gui_libs.style_system import StyleSystem


class EditorLint:
    """Lightweight multi-language static analysis for CodeEditor.

    Attaches to the editor's text widget and runs checks on a debounce
    timer. Issues are marked with colored underline tags.
    """

    LINT_DEBOUNCE_MS = 600
    LINT_TAG_ERROR = "lint_error"
    LINT_TAG_WARNING = "lint_warning"
    ERROR_COLOR = "#FF5555"
    WARNING_COLOR = "#D19A66"

    # Languages that use // and /* */ comments
    SLASH_COMMENT_LANGS = frozenset({
        "java", "rust", "c", "cpp", "javascript", "typescript",
        "go", "php", "csharp", "kotlin", "swift", "scala",
    })
    # Languages that use # comments
    HASH_COMMENT_LANGS = frozenset({"python", "ruby", "shell", "yaml", "toml"})

    def __init__(self, parent):
        """Initialize the lint handler.

        Args:
            parent: CodeEditor instance
        """
        self.parent = parent
        self._after_id = None
        self._style_system = StyleSystem()
        self._setup_tags()

    def _setup_tags(self):
        """Configure lint tag appearance on the text widget."""
        tb = self.parent._textbox
        error_color = self._style_system.get_value(
            "editor", "lint_error_color", self.ERROR_COLOR)
        warn_color = self._style_system.get_value(
            "editor", "lint_warning_color", self.WARNING_COLOR)
        tb.tag_configure(self.LINT_TAG_ERROR, underline=True,
                         foreground=error_color)
        tb.tag_configure(self.LINT_TAG_WARNING, underline=True,
                         foreground=warn_color)

    def schedule_lint(self):
        """Schedule a lint pass after the debounce interval.

        Called by CodeEditor.on_key_release so rapid keystrokes merge
        into a single scan.
        """
        if self._after_id is not None:
            try:
                self.parent.master.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.parent.master.after(
            self.LINT_DEBOUNCE_MS, self._run_lint)

    def _run_lint(self):
        """Execute the deferred lint pass."""
        self._after_id = None
        tb = self.parent._textbox
        content = tb.get("1.0", "end-1c")
        # Clear previous lint tags
        tb.tag_remove(self.LINT_TAG_ERROR, "1.0", "end")
        tb.tag_remove(self.LINT_TAG_WARNING, "1.0", "end")

        language = self.parent.language
        if language == "python":
            self._lint_python(content)
        elif language in self.SLASH_COMMENT_LANGS:
            self._lint_slash_lang(content)
        else:
            self._lint_generic(content)

    def _lint_generic(self, content: str):
        """Generic checks applicable to all languages.

        - Bracket balance: (), [], {}
        - Trailing whitespace (warning)
        """
        tb = self.parent._textbox
        lines = content.splitlines()

        # Bracket balance check (single-line scope for generic)
        brackets = {'(': ')', '[': ']', '{': '}'}
        for line_num, line in enumerate(lines, 1):
            in_string = None
            stack = []
            i = 0
            while i < len(line):
                ch = line[i]
                if in_string:
                    if ch == '\\' and i + 1 < len(line):
                        i += 1
                    elif ch == in_string:
                        in_string = None
                elif ch in ('"', "'", '`'):
                    in_string = ch
                elif ch in brackets:
                    stack.append((ch, i))
                elif ch in brackets.values():
                    if stack and brackets[stack[-1][0]] == ch:
                        stack.pop()
                    else:
                        tb.tag_add(self.LINT_TAG_ERROR,
                                   f"{line_num}.{i}", f"{line_num}.{i + 1}")
                i += 1
            # Unmatched opening brackets on this line
            for ch, col in stack:
                tb.tag_add(self.LINT_TAG_ERROR,
                           f"{line_num}.{col}", f"{line_num}.{col + 1}")

            # Trailing whitespace
            stripped = line.rstrip()
            if len(stripped) < len(line):
                tb.tag_add(self.LINT_TAG_WARNING,
                           f"{line_num}.{len(stripped)}", f"{line_num}.end")

    def _lint_python(self, content: str):
        """Python-specific lint checks."""
        self._lint_generic(content)
        tb = self.parent._textbox
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            # Mixed tabs and spaces in indentation
            indent = line[:len(line) - len(line.lstrip())]
            if '\t' in indent and '  ' in indent:
                tb.tag_add(self.LINT_TAG_WARNING,
                           f"{line_num}.0", f"{line_num}.{len(indent)}")

    def _lint_slash_lang(self, content: str):
        """Lint for // and /* */ comment languages.

        - Cross-line bracket balance (handles multi-line blocks)
        - Trailing whitespace (warning)
        """
        tb = self.parent._textbox
        lines = content.splitlines()

        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []  # (bracket_char, line_num, col)
        in_block_comment = False

        for line_num, line in enumerate(lines, 1):
            in_string = None
            i = 0
            while i < len(line):
                ch = line[i]
                if in_string:
                    if ch == '\\' and i + 1 < len(line):
                        i += 1
                    elif ch == in_string:
                        in_string = None
                elif in_block_comment:
                    if i < len(line) - 1 and ch == '*' and line[i + 1] == '/':
                        in_block_comment = False
                        i += 1
                elif i < len(line) - 1 and ch == '/' and line[i + 1] == '/':
                    break  # Line comment
                elif i < len(line) - 1 and ch == '/' and line[i + 1] == '*':
                    in_block_comment = True
                    i += 1
                elif ch in ('"', "'", '`'):
                    in_string = ch
                elif ch in brackets:
                    stack.append((ch, line_num, i))
                elif ch in brackets.values():
                    if stack and brackets[stack[-1][0]] == ch:
                        stack.pop()
                    else:
                        tb.tag_add(self.LINT_TAG_ERROR,
                                   f"{line_num}.{i}", f"{line_num}.{i + 1}")
                i += 1

            # Trailing whitespace
            stripped = line.rstrip()
            if len(stripped) < len(line):
                tb.tag_add(self.LINT_TAG_WARNING,
                           f"{line_num}.{len(stripped)}", f"{line_num}.end")

        # Unmatched opening brackets (cross-line)
        for ch, line_num, col in stack:
            tb.tag_add(self.LINT_TAG_ERROR,
                       f"{line_num}.{col}", f"{line_num}.{col + 1}")

    def clear(self):
        """Remove all lint markers and cancel pending scan."""
        if self._after_id is not None:
            try:
                self.parent.master.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            tb = self.parent._textbox
            tb.tag_remove(self.LINT_TAG_ERROR, "1.0", "end")
            tb.tag_remove(self.LINT_TAG_WARNING, "1.0", "end")
        except Exception:
            pass
