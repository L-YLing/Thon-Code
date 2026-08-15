from tkinter import messagebox


class EditorShortcuts:
    def __init__(self, parent):
        self.parent = parent

    def _on_ctrl_s(self, event):
        if not self.parent.main_window:
            return "break"
        
        master = self.parent.main_window
        if master.current_file:
            try:
                content = self.parent._textbox.get("1.0", "end-1c")
                with open(master.current_file, "w", encoding="utf-8") as f:
                    f.write(content)
                master.is_dirty = False
                master.last_saved_content = content
                master.update_title()
                master.status_bar.configure(text=f"已保存: {master.current_file}")
                self.parent._textbox.edit_modified(False)
                self.parent.current_file = master.current_file
                self.parent._completion_enabled = self.parent._should_enable_completion(self.parent.current_file)
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：{e}")
        else:
            if hasattr(master, 'save_as'):
                master.save_as()
        return "break"

    def _on_ctrl_z(self, event):
        try:
            self.parent._textbox.edit_undo()
        except:
            pass
        return "break"

    def _on_ctrl_y(self, event):
        try:
            self.parent._textbox.edit_redo()
        except:
            pass
        return "break"

    def _on_ctrl_shift_z(self, event):
        try:
            self.parent._textbox.edit_redo()
        except:
            pass
        return "break"

    def on_tab(self, event):
        if self.parent.completion_window and self.parent.completion_window.winfo_ismapped():
            self.parent._select_completion()
            return "break"
        text_widget = self.parent._textbox
        if text_widget.tag_ranges("sel"):
            self._indent_selection(1)
            return "break"
        text_widget.insert("insert", " " * self.parent.tab_size)
        return "break"

    def on_shift_tab(self, event):
        if self.parent._textbox.tag_ranges("sel"):
            self._indent_selection(-1)
        return "break"

    def _indent_selection(self, direction):
        text_widget = self.parent._textbox
        start = text_widget.index("sel.first")
        end = text_widget.index("sel.last")
        start_line = int(start.split('.')[0])
        end_line = int(end.split('.')[0])
        if end.split('.')[1] == '0' and end_line > start_line:
            end_line -= 1
        for line in range(start_line, end_line + 1):
            line_start = f"{line}.0"
            line_text = text_widget.get(line_start, f"{line}.end")
            leading_spaces = len(line_text) - len(line_text.lstrip(' '))
            if direction == 1:
                text_widget.insert(line_start, " " * self.parent.tab_size)
            else:
                remove_count = min(leading_spaces, self.parent.tab_size)
                if remove_count > 0:
                    text_widget.delete(line_start, f"{line_start}+{remove_count}c")
        self.parent.highlight_all()

    def select_all(self, event=None):
        self.parent._hide_completion()
        self.parent._textbox.tag_add("sel", "1.0", "end")
        return "break"