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

    Processes text content to apply keyword, string, number, function,
    and classname highlighting tags based on loaded language groups.
    Colors are sourced from StyleSystem singleton for theme consistency.
    """

    def __init__(self, parent):
        """Initialize the highlight handler.

        Args:
            parent: CodeEditor instance that owns this handler
        """
        self.parent = parent
        self.bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        self._style_system = StyleSystem()
        self._style_system.sync_from_theme()

    def highlight_all(self, event=None):
        """Apply syntax highlighting to the entire document.

        Args:
            event: Optional event that triggered highlighting
        """
        text_widget = self.parent._textbox
        content = text_widget.get("1.0", "end-1c")
        if not content.strip():
            for tag in text_widget.tag_names():
                if tag.startswith("kw_") or tag in ("comment","string","number","function","classname"):
                    text_widget.tag_delete(tag)
            return

        for g in self.parent.groups:
            text_widget.tag_config(f"kw_{g['name']}", foreground=g["color"])
        text_widget.tag_config("comment", foreground=self._style_system.get_value("highlight", "comment", "#5C6370"))
        text_widget.tag_config("string", foreground=self._style_system.get_value("highlight", "string", "#98C379"))
        text_widget.tag_config("number", foreground=self._style_system.get_value("highlight", "number", "#D19A66"))
        text_widget.tag_config("function", foreground=self._style_system.get_value("highlight", "function", "#61AFEF"))
        text_widget.tag_config("classname", foreground=self._style_system.get_value("highlight", "classname", "#E5C07B"))

        lines = content.splitlines(keepends=True)
        line_num = 1
        in_multiline_comment = False
        for line in lines:
            in_multiline_comment = self._highlight_line(text_widget, line_num, line, in_multiline_comment)
            line_num += 1

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
                matched = False
                for g in self.parent.groups:
                    if word in g["words"]:
                        text_widget.tag_add(f"kw_{g['name']}", f"{line_num}.{start}", f"{line_num}.{i}")
                        matched = True
                        break
                if not matched:
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

    def highlight_matching_bracket(self):
        """Highlight matching brackets at the cursor position."""
        text_widget = self.parent._textbox
        try:
            text_widget.tag_delete("bracket_match")
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
        """Find a matching bracket character in the text.

        Args:
            text_widget: The text widget to search in
            start_idx: Starting index position
            open_ch: Opening bracket character
            close_ch: Closing bracket character

        Returns:
            Index of the matching bracket, or None if not found
        """
        before = text_widget.get("1.0", start_idx)
        full_text = text_widget.get("1.0", "end-1c")
        offset = len(before)
        stack = []
        for i, ch in enumerate(full_text):
            if ch == open_ch:
                stack.append(i)
            elif ch == close_ch:
                if stack:
                    if i == offset:
                        return text_widget.index(f"1.0+{stack[-1]}c")
                    popped = stack.pop()
                    if i == offset:
                        return text_widget.index(f"1.0+{popped}c")
        return None