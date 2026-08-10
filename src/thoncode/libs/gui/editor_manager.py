#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor Manager",
    "Path": ".main.libs.gui.editor_manager",
    "Entrance": "main.py"
}

import os
from libs.gui.code_editor import CodeEditor
import libs.cfg_handle as cfg_handle


class EditorManager:
    """Manages the code editor instance and file operations.

    Handles file opening, saving, content management, and language
    detection for syntax highlighting and auto-completion.
    """

    def __init__(self, parent, main_window, status_callback, update_title_callback):
        """Initialize the editor manager.

        Args:
            parent: Parent widget for the editor
            main_window: Reference to the main window
            status_callback: Callback function for status updates
            update_title_callback: Callback to update window title
        """
        self.parent = parent
        self.main_window = main_window
        self.status_callback = status_callback
        self.update_title_callback = update_title_callback

        self.editor = None
        self.editor_widget = None
        self.current_file = None
        self._is_dirty = False
        self.last_saved_content = ""

        self._create_editor()

    def _set_editor_language(self, file_path):
        """Set the editor language based on file extension.

        Args:
            file_path: Path to the file to detect language for
        """
        ext = os.path.splitext(file_path)[1].lower()

        # Languages supporting syntax highlighting and auto-completion
        supported_langs = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.txt': 'text',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'cpp',
            '.hpp': 'cpp',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.sh': 'shell',
            '.bash': 'shell',
            '.sql': 'sql',
        }

        lang = supported_langs.get(ext, 'text')
        self.editor.set_language(lang)
        self.editor.highlight_all()

    def _create_editor(self):
        """Create and initialize the CodeEditor widget."""
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        ligatures = cfg.get("font_ligatures", True)
        tab_size = cfg.get("tab_size", 4)

        self.editor = CodeEditor(
            self.parent,
            main_window=self.main_window,
            language="python",
            font_ligatures=ligatures,
            tab_size=tab_size,
            current_file=self.current_file
        )
        self.editor_widget = self.editor.get_widget()
        self.textbox_widget = self.editor.get_textbox()
        self.editor.current_file = self.current_file
        self.textbox_widget.bind("<<Modified>>", self._on_modified)
        self.textbox_widget.edit_modified(False)

    def get_widget(self):
        """Get the editor's main frame widget.

        Returns:
            The editor frame widget
        """
        return self.editor_widget

    def get_textbox(self):
        """Get the editor's textbox widget.

        Returns:
            The textbox widget
        """
        return self.textbox_widget

    def get_editor_instance(self):
        """Get the CodeEditor instance.

        Returns:
            The CodeEditor instance
        """
        return self.editor

    def set_content(self, content):
        """Set the editor content and update state.

        Args:
            content: Text content to set in the editor
        """
        self.textbox_widget.delete("1.0", "end")
        self.textbox_widget.insert("1.0", content)
        self.last_saved_content = content
        self._is_dirty = False
        self.textbox_widget.edit_modified(False)
        if self.current_file:
            self._set_editor_language(self.current_file)
        else:
            self.editor.highlight_all()

    def clear(self):
        """Clear the editor content and reset state."""
        self.textbox_widget.delete("1.0", "end")
        self.current_file = None
        self._is_dirty = False
        self.last_saved_content = ""
        if hasattr(self.editor, 'current_file'):
            self.editor.current_file = None
            self.editor.set_language('text')
        self.update_title_callback()

    def get_content(self):
        """Get the current editor content.

        Returns:
            The text content of the editor
        """
        return self.textbox_widget.get("1.0", "end-1c")

    def open_file(self, file_path):
        """Open a file and load its content into the editor.

        Args:
            file_path: Absolute path to the file to open

        Returns:
            bool: True if file was opened successfully
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.set_content(content)
            self.current_file = file_path
            self.editor.current_file = file_path
            self._set_editor_language(file_path)
            self.update_title_callback()
            self.status_callback(f"Opened: {file_path}")
            return True
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Cannot open file: {e}")
            return False

    def save_file(self, file_path=None):
        """Save the current editor content to a file.

        Args:
            file_path: Optional path to save to (uses current_file if None)

        Returns:
            bool: True if save was successful, None if no file is open
        """
        if file_path is None and not self.current_file:
            return None

        save_path = file_path or self.current_file
        try:
            content = self.get_content()
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file = save_path
            self._is_dirty = False
            self.last_saved_content = content
            self.textbox_widget.edit_modified(False)
            if hasattr(self.editor, '_saving'):
                self.editor._saving = False
            self.update_title_callback()
            self.status_callback(f"Saved: {save_path}")
            return True
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Save failed: {e}")
            return False

    def _on_modified(self, event):
        """Handle text modification events and update dirty state.

        Args:
            event: The modification event
        """
        current_content = self.get_content()
        self._is_dirty = (current_content != self.last_saved_content)
        self.update_title_callback()
        self.textbox_widget.edit_modified(False)

    @property
    def is_dirty(self) -> bool:
        """Check if the editor has unsaved changes.

        Returns:
            bool: True if content has been modified since last save
        """
        return self._is_dirty

    def get_current_file(self):
        """Get the path of the currently open file.

        Returns:
            The file path string, or None if no file is open
        """
        return self.current_file