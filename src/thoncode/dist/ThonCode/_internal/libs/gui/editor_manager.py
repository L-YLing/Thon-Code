import os
import customtkinter as ctk
from libs.gui.code_editor import CodeEditor
import libs.cfg_handle as cfg_handle


class EditorManager:
    def __init__(self, parent, main_window, status_callback, update_title_callback):
        self.parent = parent
        self.main_window = main_window
        self.status_callback = status_callback
        self.update_title_callback = update_title_callback
        
        self.editor = None
        self.editor_widget = None
        self.current_file = None
        self.is_dirty = False
        self.last_saved_content = ""
        
        self._create_editor()
    
    def _set_editor_language(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        # 支持语法高亮和自动补全的语言
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
        self.editor_widget = self.editor.get_widget()  # 返回主框架
        self.textbox_widget = self.editor.get_textbox()  # 返回文本框
        self.editor.current_file = self.current_file
        self.textbox_widget._textbox.bind("<<Modified>>", self._on_modified)
        self.textbox_widget._textbox.edit_modified(False)

    def get_widget(self):
        return self.editor_widget

    def get_textbox(self):
        return self.textbox_widget
    
    def get_editor_instance(self):
        return self.editor
    
    def set_content(self, content):
        self.textbox_widget.delete("1.0", "end")
        self.textbox_widget.insert("1.0", content)
        self.last_saved_content = content
        self.is_dirty = False
        self.textbox_widget._textbox.edit_modified(False)
        if self.current_file:
            self._set_editor_language(self.current_file)
        else:
            self.editor.highlight_all()

    def clear(self):
        self.textbox_widget.delete("1.0", "end")
        self.current_file = None
        self.is_dirty = False
        self.last_saved_content = ""
        if hasattr(self.editor, 'current_file'):
            self.editor.current_file = None
            self.editor.set_language('text')
        self.update_title_callback()

    def get_content(self):
        return self.textbox_widget.get("1.0", "end-1c")
    
    def open_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.set_content(content)
            self.current_file = file_path
            self.editor.current_file = file_path
            self._set_editor_language(file_path)
            self.update_title_callback()
            self.status_callback(f"已打开: {file_path}")
            return True
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("错误", f"无法打开文件：{e}")
            return False
    
    def save_file(self, file_path=None):
        if file_path is None and not self.current_file:
            return None
        
        save_path = file_path or self.current_file
        try:
            content = self.get_content()
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file = save_path
            self.is_dirty = False
            self.last_saved_content = content
            self.textbox_widget._textbox.edit_modified(False)
            if hasattr(self.editor, '_saving'):
                self.editor._saving = False
            self.update_title_callback()
            self.status_callback(f"已保存: {save_path}")
            return True
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("错误", f"保存失败：{e}")
            return False
    
    def _on_modified(self, event):
        current_content = self.get_content()
        self.is_dirty = (current_content != self.last_saved_content)
        self.update_title_callback()
        self.textbox_widget._textbox.edit_modified(False)
    
    def is_dirty(self):
        return self.is_dirty
    
    def get_current_file(self):
        return self.current_file