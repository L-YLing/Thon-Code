#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor Completion",
    "Path": ".main.libs.gui.editor_completion",
    "Entrance": "main.py"
}

"""Code completion popup manager for the editor.

Features (beyond the original keyword-only popup):

* Multi-language – no longer restricted to ``.py`` files. Works for any
  file whose language has a symbol extractor registered in the
  :class:`libs.gui.symbol_loader.SymbolLoaderRegistry` (Python, Java,
  Rust built-in; extensible via plugins).
* Import-aware lazy loading – the popup includes symbols pulled from
  files that the current file imports (``import x``, ``from x import y``,
  Java ``import foo.bar.Baz``, Rust ``use foo::bar`` ...).
* Function signatures & variable names – alongside static highlight
  keywords, we include top-level / scoped function names, classes and
  variable names extracted from the file plus its imports.
* Plugin built-in symbols – plugins can seed language standard-library
  symbols via :meth:`PluginAPI.register_builtin_symbols`; they are
  merged into the popup when the pattern matches the active file.
"""

import os
import tkinter as tk
from typing import Any, Dict, List, Optional, Tuple

from libs.gui import theme
from libs.gui_libs.style_system import StyleSystem


# A completion entry: (insert_text, display_label, signature_or_None)
CompletionEntry = Tuple[str, str, Optional[str]]


class EditorCompletion:
    """Code completion popup manager for the editor."""

    def __init__(self, editor, widget_parent=None):
        self.editor = editor
        self.widget_parent = widget_parent if widget_parent else editor.master
        self._style_system = StyleSystem()
        self._style_system.sync_from_theme()
        self._is_selecting = False
        self._after_completion_id = None
        self._keywords_cache = None
        self._keywords_signature = None
        self.completion_window = None
        self.completion_listbox = None
        self.completion_matches: List[CompletionEntry] = []
        self.completion_prefix = ""
        self.completion_word_start = 0
        self._init_completion_window()

    def _init_completion_window(self):
        self.completion_window = theme.themed_toplevel(self.widget_parent)
        self.completion_window.wm_overrideredirect(True)
        self.completion_window.wm_attributes("-topmost", True)
        self.completion_window.withdraw()

        completion_font_family = self._style_system.get_value("editor", "font_family", "Consolas")
        completion_font_size = max(9, self._style_system.get_value("editor", "font_size", 10) - 2)
        self.completion_listbox = theme.themed_listbox(
            self.completion_window,
            font=(completion_font_family, completion_font_size),
        )
        self.completion_listbox.pack(fill="both", expand=True, padx=1, pady=1)
        self.completion_listbox.bind("<ButtonRelease-1>", self._select_completion)
        self.completion_listbox.bind("<Double-Button-1>", self._select_completion)

    # ------------------------------------------------------------------
    # Public API (kept small so callers stay simple)
    # ------------------------------------------------------------------

    def trigger_update(self):
        """Called by CodeEditor after each keystroke / paste."""
        if self._after_completion_id is not None:
            try:
                self.editor._textbox.after_cancel(self._after_completion_id)
            except Exception:
                pass
        self._after_completion_id = self.editor._textbox.after(60, self._update_completion)

    def hide(self):
        self._hide_completion()

    # ------------------------------------------------------------------
    # Internal: keyword/symbol aggregation
    # ------------------------------------------------------------------

    def _get_highlight_keywords(self) -> List[str]:
        sig = tuple((g.get("name"), len(g.get("words", []))) for g in getattr(self.editor, "groups", []))
        if sig != self._keywords_signature:
            result: List[str] = []
            for group in getattr(self.editor, "groups", []):
                result.extend(group.get("words", []))
            self._keywords_cache = result
            self._keywords_signature = sig
        return self._keywords_cache or []

    def _get_plugin_builtin_symbols(self, language: str,
                                    file_path: Optional[str]) -> List[CompletionEntry]:
        """Return plugin-registered builtins matching the current language."""
        host = getattr(self.editor, "main_window", None)
        if host is None:
            return []
        registry: Dict[Tuple[str, ...], List[Tuple[str, Optional[str]]]] = \
            getattr(host, "_builtin_symbol_registry", None) or {}
        results: List[CompletionEntry] = []
        patterns_to_check: List[List[str]] = []
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        if language:
            patterns_to_check.append([language])
        if ext:
            patterns_to_check.append([ext])
        # wildcard bucket matches everything
        patterns_to_check.append(["*"])
        seen = set()
        for bucket_key, symbols in registry.items():
            bucket_key_list = list(bucket_key)
            for check in patterns_to_check:
                if any(p in bucket_key_list for p in check):
                    for name, sig in symbols:
                        if not name or name in seen:
                            continue
                        seen.add(name)
                        label = f"{name}    {sig}" if sig else name
                        results.append((name, label, sig))
                    break
        return results

    def _get_lazy_symbol_entries(self, language: str,
                                 file_path: Optional[str],
                                 live_text: str) -> List[CompletionEntry]:
        """Ask SymbolLoaderRegistry for locals + imports (lazy)."""
        try:
            from libs.gui.symbol_loader import SymbolLoaderRegistry
        except Exception:
            return []
        project_root = ""
        host = getattr(self.editor, "main_window", None)
        if host is not None:
            project_root = getattr(host, "current_project", "") or \
                getattr(host, "project_root", "") or ""
        reg = SymbolLoaderRegistry.instance()
        try:
            keywords = reg.collect_completion_keywords(
                file_path or "", language, project_root, live_text
            )
        except Exception:
            return []
        results: List[CompletionEntry] = []
        seen = set()
        for name, sig in keywords:
            if not name or name in seen:
                continue
            seen.add(name)
            label = f"{name}    {sig}" if sig else name
            results.append((name, label, sig))
        return results

    def _language_for_file(self, file_path: Optional[str],
                           declared_language: str) -> str:
        if declared_language:
            return declared_language
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            return {
                ".py": "python",
                ".java": "java",
                ".rs": "rust",
                ".js": "javascript",
                ".ts": "typescript",
                ".c": "c",
                ".cpp": "cpp", ".cxx": "cpp", ".h": "cpp", ".hpp": "cpp",
                ".json": "json",
                ".md": "markdown",
            }.get(ext, "")
        return ""

    # ------------------------------------------------------------------
    # Internal: context extraction
    # ------------------------------------------------------------------

    def _extract_prefix(self, text_widget, line: int, col: int, line_text: str
                        ) -> Optional[str]:
        before = line_text[:col]
        # Suppress inside strings (heuristic) – we skip anything after an
        # unbalanced quote character. This is intentionally language-agnostic.
        in_string = False
        quote = None
        for i, ch in enumerate(before):
            if in_string:
                if ch == quote and (i == 0 or before[i - 1] != "\\"):
                    in_string = False
            elif ch in ('"', "'", '`'):
                in_string = True
                quote = ch
        if in_string:
            return None
        # line/block comments – per-language lookups are OK.
        language = self._language_for_file(self.editor.current_file,
                                           getattr(self.editor, "language", ""))
        if language in ("python",):
            if "#" in before:
                return None
        elif language in ("java", "rust", "c", "cpp", "javascript", "typescript"):
            if "//" in before:
                return None
        # Walk backwards to capture valid identifier start (letters, digits, _, '.').
        start = col
        while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] in "_."):
            start -= 1
        prefix = line_text[start:col]
        if not prefix:
            return None
        # Record word_start column so replacement can happen later
        self.completion_word_start = start
        # Don't trigger on a leading '.' alone (needs at least one letter after)
        if prefix == ".":
            return None
        return prefix

    # ------------------------------------------------------------------
    # Internal: popup logic
    # ------------------------------------------------------------------

    def _update_completion(self):
        if self._is_selecting:
            return
        editor = self.editor
        if not getattr(editor, "_completion_enabled", True):
            self._hide_completion()
            return
        text_widget = editor._textbox
        try:
            live_text = text_widget.get("1.0", "end-1c")
        except Exception:
            live_text = ""
        if not live_text.strip():
            self._hide_completion()
            return
        cursor = text_widget.index("insert")
        line, col = map(int, cursor.split('.'))
        line_text = text_widget.get(f"{line}.0", f"{line}.end")

        prefix = self._extract_prefix(text_widget, line, col, line_text)
        if not prefix:
            self._hide_completion()
            return

        language = self._language_for_file(
            getattr(editor, "current_file", None),
            getattr(editor, "language", ""))

        # Build the combined entry list. Each entry is (insert, label, sig).
        entries: List[CompletionEntry] = []
        seen: set = set()

        def _push(insert: str, label: str, sig: Optional[str]) -> None:
            if not insert or insert in seen:
                return
            seen.add(insert)
            entries.append((insert, label, sig))

        # 1) Static highlight groups (backward compatible).
        for kw in self._get_highlight_keywords():
            _push(kw, kw, None)

        # 2) Plugin-registered standard library entries.
        for insert, label, sig in self._get_plugin_builtin_symbols(
                language, getattr(editor, "current_file", None)):
            _push(insert, label, sig)

        # 3) Lazy symbols (local + imports).
        for insert, label, sig in self._get_lazy_symbol_entries(
                language, getattr(editor, "current_file", None), live_text):
            _push(insert, label, sig)

        # 4) Prefix matching. We accept both a case-sensitive prefix and
        #    (fallback) a case-insensitive one. The list stays sorted.
        prefix_lower = prefix.lower()
        matches_sensitive = [e for e in entries if e[0].startswith(prefix)]
        matches_insensitive = [e for e in entries
                               if e[0].lower().startswith(prefix_lower)
                               and e not in matches_sensitive]
        matches = (matches_sensitive + matches_insensitive)[:50]

        if not matches:
            self._hide_completion()
            return

        self._show_completion(matches, prefix)

    def _show_completion(self, matches: List[CompletionEntry], prefix: str):
        self.completion_listbox.delete(0, tk.END)
        width = 220
        for _insert, label, _sig in matches:
            self.completion_listbox.insert(tk.END, label)
            width = max(width, min(640, len(label) * 9 + 20))
        self.completion_matches = matches
        self.completion_prefix = prefix
        self._is_selecting = False

        text_widget = self.editor._textbox
        bbox = text_widget.bbox("insert")
        if bbox:
            x, y, bw, height = bbox
            x += text_widget.winfo_rootx()
            y += text_widget.winfo_rooty() + height
            list_height = min(len(matches), 12) * 20 + 4
            self.completion_window.geometry(f"{width}x{list_height}+{x}+{y}")
            self.completion_window.deiconify()
            self.completion_listbox.selection_clear(0, tk.END)
            self.completion_listbox.selection_set(0)
            self.completion_listbox.see(0)
        else:
            self.completion_window.deiconify()

    def _hide_completion(self, event=None):
        self._is_selecting = False
        if self.completion_window:
            self.completion_window.withdraw()
            self.completion_listbox.delete(0, tk.END)
            self.completion_matches = []
            self.completion_prefix = ""
            self.completion_listbox.selection_clear(0, tk.END)

    def _select_completion(self, event=None):
        self._is_selecting = False
        if not self.completion_matches:
            self._hide_completion()
            return
        sel = self.completion_listbox.curselection()
        if not sel:
            if self.completion_matches:
                entry = self.completion_matches[0]
            else:
                self._hide_completion()
                return
        else:
            entry = self.completion_matches[sel[0]]
        insert_text = entry[0]

        text_widget = self.editor._textbox
        cursor = text_widget.index("insert")
        line, col = map(int, cursor.split('.'))
        # Replace from completion_word_start to current col
        start_idx = f"{line}.{self.completion_word_start}"
        end_idx = cursor
        text_widget.delete(start_idx, end_idx)
        text_widget.insert(start_idx, insert_text)
        self._hide_completion()
        try:
            self.editor.highlight_all()
        except Exception:
            pass

    def on_key_press(self, event):
        if self.completion_window and self.completion_window.winfo_ismapped():
            if event.keysym in ('Up', 'Down'):
                if not self.completion_matches:
                    return "break"
                current = self.completion_listbox.curselection()
                idx = current[0] if current else -1
                if event.keysym == 'Up':
                    idx = (idx - 1) % len(self.completion_matches)
                elif event.keysym == 'Down':
                    idx = (idx + 1) % len(self.completion_matches)
                self.completion_listbox.selection_clear(0, tk.END)
                self.completion_listbox.selection_set(idx)
                self.completion_listbox.see(idx)
                self._is_selecting = True
                return "break"
            elif event.keysym in ('Return', 'Tab'):
                self._select_completion()
                return "break"
            elif event.keysym == 'Escape':
                self._hide_completion()
                return "break"
        return None
