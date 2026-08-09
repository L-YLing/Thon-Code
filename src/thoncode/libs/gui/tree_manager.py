import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import customtkinter as ctk

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class TreeManager:
    def __init__(self, parent, root_widget, project_root, open_file_callback, status_callback):
        self.parent = parent
        self.root_widget = root_widget
        self.project_root = project_root
        self.open_file_callback = open_file_callback
        self.status_callback = status_callback
        
        self.folder_icon = None
        self.default_file_icon = None
        self.file_icons = {}
        self._right_click_item = None
        self._right_click_path = None
        
        self._load_icons()
        self._build_tree()
    
    def _build_tree(self):
        self.tree = ttk.Treeview(self.root_widget, selectmode="browse",
                                 columns=("path",), show="tree")
        self.tree.column("path", width=0, stretch=False)
        self.tree.heading("path", text="")
        self.tree.pack(fill="both", expand=True, padx=3, pady=3)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.populate_tree()
    
    def _load_icons(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_dir = os.path.join(base_dir, "assets", "images")
        target_size = (16, 16)

        folder_path = os.path.join(icon_dir, "folder.png")
        self.folder_icon = self._load_icon_with_resize(folder_path, target_size)
        if self.folder_icon is None:
            print(f"警告: 文件夹图标不存在: {folder_path}")

        default_icon_path = os.path.join(icon_dir, "file.png")
        self.default_file_icon = self._load_icon_with_resize(default_icon_path, target_size)
        if self.default_file_icon is None:
            print(f"警告: 默认文件图标不存在: {default_icon_path}")

        self.file_icons = {}
        if os.path.exists(icon_dir):
            for filename in os.listdir(icon_dir):
                if filename.startswith("file_") and filename.endswith(".png"):
                    ext = filename[5:-4]
                    if ext:
                        full_path = os.path.join(icon_dir, filename)
                        icon = self._load_icon_with_resize(full_path, target_size)
                        if icon:
                            self.file_icons[ext] = icon
    
    def _load_icon_with_resize(self, file_path, target_size=(16, 16)):
        if not file_path or not os.path.exists(file_path):
            return None
        if HAS_PIL:
            try:
                img = Image.open(file_path)
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Pillow缩放失败: {e}，回退到原始尺寸")
                return tk.PhotoImage(file=file_path)
        else:
            return tk.PhotoImage(file=file_path)
    
    def get_tree(self):
        return self.tree
    
    def populate_tree(self, parent="", path=None):
        expanded_paths = self._get_expanded_paths()
        for item in self.tree.get_children():
            self.tree.delete(item)

        if path is None:
            path = self.project_root
            node = self.tree.insert(parent, "end", text=os.path.basename(path), open=True)
            self.tree.set(node, "path", path)
            self._add_children(node, path)
        else:
            node = self.tree.insert(parent, "end", text=os.path.basename(path), open=False)
            self.tree.set(node, "path", path)
            self._add_children(node, path)

        self._restore_expanded_paths(expanded_paths)
    
    def refresh(self):
        self.populate_tree()
    
    def set_project_root(self, path):
        self.project_root = path
        self.refresh()
    
    def _get_expanded_paths(self):
        expanded = []
        def collect(item):
            if self.tree.item(item, 'open'):
                path = self.tree.set(item, "path")
                if path:
                    expanded.append(path)
            for child in self.tree.get_children(item):
                collect(child)
        for root in self.tree.get_children():
            collect(root)
        return expanded
    
    def _restore_expanded_paths(self, expanded_paths):
        def restore(item):
            path = self.tree.set(item, "path")
            if path in expanded_paths:
                self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                restore(child)
        for root in self.tree.get_children():
            restore(root)
    
    def _add_children(self, parent, path):
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return
        for name in items:
            full_path = os.path.join(path, name)
            if name.startswith('.') or name in ('__pycache__', '.git', '.idea', '.vscode', 'node_modules', 'dist', 'build'):
                continue

            if os.path.isdir(full_path):
                icon = self.folder_icon
                node = self.tree.insert(parent, "end", text=name, open=False, image=icon if icon else '')
                self.tree.set(node, "path", full_path)
                self._add_children(node, full_path)
            else:
                _, ext = os.path.splitext(name)
                ext = ext.lstrip('.').lower()
                if ext in self.file_icons:
                    icon = self.file_icons[ext]
                else:
                    icon = self.default_file_icon
                node = self.tree.insert(parent, "end", text=name, image=icon if icon else '')
                self.tree.set(node, "path", full_path)
    
    def on_tree_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        path = self.tree.set(item, "path")
        if path and os.path.isfile(path):
            self.open_file_callback(path)
    
    def on_tree_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._right_click_item = item
            self._right_click_path = self.tree.set(item, "path")
        else:
            self._right_click_item = None
            self._right_click_path = self.project_root

        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label="刷新", command=self.refresh)
        menu.add_separator()
        menu.add_command(label="新建文件", command=self.menu_new_file)
        menu.add_command(label="新建文件夹", command=self.menu_new_folder)
        menu.add_separator()
        menu.add_command(label="重命名", command=self.menu_rename)
        menu.add_command(label="删除", command=self.menu_delete)
        menu.add_command(label="移动到回收站", command=self.menu_move_to_trash)
        menu.post(event.x_root, event.y_root)
    
    def menu_new_file(self):
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        dialog = ctk.CTkInputDialog(text="输入文件名（含扩展名）：", title="新建文件")
        name = dialog.get_input()
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                pass
            self.refresh()
        except Exception as e:
            messagebox.showerror("错误", f"创建文件失败：{e}")
    
    def menu_new_folder(self):
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        dialog = ctk.CTkInputDialog(text="输入文件夹名称：", title="新建文件夹")
        name = dialog.get_input()
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            os.mkdir(full_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("错误", f"创建文件夹失败：{e}")
    
    def menu_rename(self):
        if not self._right_click_item:
            return
        old_path = self._right_click_path
        old_name = os.path.basename(old_path)
        dialog = ctk.CTkInputDialog(text="输入新名称：", title="重命名", initialvalue=old_name)
        new_name = dialog.get_input()
        if not new_name or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        try:
            os.rename(old_path, new_path)
            self.refresh()
            return old_path, new_path
        except Exception as e:
            messagebox.showerror("错误", f"重命名失败：{e}")
            return None, None
    
    def menu_delete(self):
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno("确认删除", f"确定要永久删除 {os.path.basename(path)} 吗？"):
            return
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            self.refresh()
            return path
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{e}")
            return None
    
    def menu_move_to_trash(self):
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno("确认", f"确定将 {os.path.basename(path)} 移动到回收站吗？"):
            return
        try:
            if HAS_SEND2TRASH:
                send2trash.send2trash(path)
            else:
                if messagebox.askyesno("未安装 send2trash", "未安装 send2trash 库，将永久删除文件。是否继续？"):
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                else:
                    return
            self.refresh()
            return path
        except Exception as e:
            messagebox.showerror("错误", f"操作失败：{e}")
            return None