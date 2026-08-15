import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import customtkinter as ctk


class LazyLoader:
    """Universal lazy loader for GUI components and heavy libraries"""
    _instances = {}
    
    @classmethod
    def get(cls, module_path, class_name=None):
        cache_key = f"{module_path}:{class_name}" if class_name else module_path
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        module = __import__(module_path, fromlist=[class_name] if class_name else [])
        if class_name:
            result = getattr(module, class_name)
        else:
            result = module
        cls._instances[cache_key] = result
        return result
    
    @classmethod
    def get_send2trash(cls):
        try:
            return cls.get('send2trash', 'send2trash')
        except ImportError:
            return None
    
    @classmethod
    def get_pil(cls):
        try:
            from PIL import Image, ImageTk
            return Image, ImageTk
        except ImportError:
            return None, None


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
        self._icon_cache = {}
        self._children_loaded = set()
        
        self._load_icons_lazy()
        self._build_tree()
    
    def _build_tree(self):
        self.tree = ttk.Treeview(self.root_widget, selectmode="browse",
                                 columns=("path",), show="tree")
        self.tree.column("path", width=0, stretch=False)
        self.tree.heading("path", text="")
        self.tree.pack(fill="both", expand=True, padx=3, pady=3)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        self._populate_root()
    
    def _load_icons_lazy(self):
        """Load icons only when needed"""
        if self._icon_cache:
            return
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_dir = os.path.join(base_dir, "assets", "images")
        target_size = (16, 16)

        folder_path = os.path.join(icon_dir, "folder.png")
        self.folder_icon = self._load_icon_with_resize(folder_path, target_size)

        default_icon_path = os.path.join(icon_dir, "file.png")
        self.default_file_icon = self._load_icon_with_resize(default_icon_path, target_size)

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
        
        self._icon_cache['loaded'] = True
    
    def _load_icon_with_resize(self, file_path, target_size=(16, 16)):
        if not file_path or not os.path.exists(file_path):
            return None
        
        Image, ImageTk = LazyLoader.get_pil()
        if Image and ImageTk:
            try:
                img = Image.open(file_path)
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception:
                return tk.PhotoImage(file=file_path)
        else:
            return tk.PhotoImage(file=file_path)
    
    def get_tree(self):
        return self.tree
    
    def _populate_root(self):
        """Populate only the root node initially"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self._children_loaded.clear()
        
        if not os.path.exists(self.project_root):
            return
        
        node = self.tree.insert("", "end", text=os.path.basename(self.project_root), open=False)
        self.tree.set(node, "path", self.project_root)
        
        self._add_children(node, self.project_root, load_icons=True)
        self._children_loaded.add(node)
    
    def populate_tree(self, parent="", path=None):
        """Full tree refresh - use with caution on large projects"""
        self._load_icons_lazy()
        expanded_paths = self._get_expanded_paths()
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self._children_loaded.clear()
        
        if path is None:
            path = self.project_root
            node = self.tree.insert(parent, "end", text=os.path.basename(path), open=True)
            self.tree.set(node, "path", path)
            self._add_children(node, path, load_icons=True)
            self._children_loaded.add(node)
        else:
            node = self.tree.insert(parent, "end", text=os.path.basename(path), open=False)
            self.tree.set(node, "path", path)
            self._add_children(node, path, load_icons=True)
            self._children_loaded.add(node)

        self._restore_expanded_paths(expanded_paths)
    
    def _on_tree_open(self, event):
        """Load children when a tree node is expanded"""
        item = self.tree.focus()
        if not item:
            return
        
        path = self.tree.set(item, "path")
        if not path or not os.path.isdir(path):
            return
        
        if item not in self._children_loaded:
            self._load_icons_lazy()
            self._add_children(item, path, load_icons=True)
            self._children_loaded.add(item)
    
    def refresh(self):
        """Refresh the entire tree"""
        self._populate_root()
    
    def set_project_root(self, path):
        self.project_root = path
        self._populate_root()
    
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
                if item not in self._children_loaded and os.path.isdir(path):
                    self._add_children(item, path, load_icons=True)
                    self._children_loaded.add(item)
            for child in self.tree.get_children(item):
                restore(child)
        for root in self.tree.get_children():
            restore(root)
    
    def _add_children(self, parent, path, load_icons=True):
        """Add children to a tree node"""
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return
        
        for name in items:
            full_path = os.path.join(path, name)
            if name.startswith('.') or name in ('__pycache__', '.git', '.idea', '.vscode', 'node_modules', 'dist', 'build'):
                continue

            if os.path.isdir(full_path):
                node = self.tree.insert(parent, "end", text=name, open=False, image=self.folder_icon if self.folder_icon else '')
                self.tree.set(node, "path", full_path)
            else:
                _, ext = os.path.splitext(name)
                ext = ext.lstrip('.').lower()
                icon = self.file_icons.get(ext, self.default_file_icon)
                node = self.tree.insert(parent, "end", text=name, image=icon if icon else '')
                self.tree.set(node, "path", full_path)
    
    def on_tree_double_click(self, event):
        """Handle double click on tree items"""
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        path = self.tree.set(item, "path")
        if path and os.path.isfile(path):
            self.open_file_callback(path)
        elif path and os.path.isdir(path):
            if self.tree.item(item, 'open'):
                self.tree.item(item, open=False)
            else:
                self.tree.item(item, open=True)
                if item not in self._children_loaded:
                    self._load_icons_lazy()
                    self._add_children(item, path, load_icons=True)
                    self._children_loaded.add(item)
    
    def on_tree_right_click(self, event):
        """Handle right click on tree items"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._right_click_item = item
            self._right_click_path = self.tree.set(item, "path")
        else:
            self._right_click_item = None
            self._right_click_path = self.project_root

        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label="Refresh", command=self.refresh)
        menu.add_separator()
        menu.add_command(label="New File", command=self.menu_new_file)
        menu.add_command(label="New Folder", command=self.menu_new_folder)
        menu.add_separator()
        menu.add_command(label="Rename", command=self.menu_rename)
        menu.add_command(label="Delete", command=self.menu_delete)
        menu.add_command(label="Move to Trash", command=self.menu_move_to_trash)
        menu.post(event.x_root, event.y_root)
    
    def menu_new_file(self):
        """Create a new file"""
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        dialog = ctk.CTkInputDialog(text="Enter file name (with extension):", title="New File")
        name = dialog.get_input()
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                pass
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create file: {e}")
    
    def menu_new_folder(self):
        """Create a new folder"""
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        dialog = ctk.CTkInputDialog(text="Enter folder name:", title="New Folder")
        name = dialog.get_input()
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            os.mkdir(full_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create folder: {e}")
    
    def menu_rename(self):
        """Rename a file or folder"""
        if not self._right_click_item:
            return
        old_path = self._right_click_path
        old_name = os.path.basename(old_path)
        dialog = ctk.CTkInputDialog(text="Enter new name:", title="Rename", initialvalue=old_name)
        new_name = dialog.get_input()
        if not new_name or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        try:
            os.rename(old_path, new_path)
            self.refresh()
            return old_path, new_path
        except Exception as e:
            messagebox.showerror("Error", f"Rename failed: {e}")
            return None, None
    
    def menu_delete(self):
        """Delete a file or folder permanently"""
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete {os.path.basename(path)}?"):
            return
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            self.refresh()
            return path
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")
            return None
    
    def menu_move_to_trash(self):
        """Move a file or folder to trash"""
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno("Confirm", f"Move {os.path.basename(path)} to trash?"):
            return
        try:
            send2trash = LazyLoader.get_send2trash()
            if send2trash:
                send2trash.send2trash(path)
            else:
                if messagebox.askyesno("send2trash not installed", "send2trash not installed. Permanently delete instead?"):
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                else:
                    return
            self.refresh()
            return path
        except Exception as e:
            messagebox.showerror("Error", f"Operation failed: {e}")
            return None