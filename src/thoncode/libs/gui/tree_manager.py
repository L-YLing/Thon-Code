#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Tree Manager",
    "Path": ".main.libs.gui.tree_manager",
    "Entrance": "main.py"
}

import os
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import shutil

from libs.gui.lazy_loader import LazyLoader
import libs.langs_loader as langs_loader

_logger = logging.getLogger("thoncode.tree_manager")


class TreeManager:
    # Directories ignored everywhere to keep large projects responsive.
    IGNORED_DIRS = ('__pycache__', '.git', '.idea', '.vscode', 'node_modules', 'dist', 'build')
    # Tag marking placeholder child nodes used to show the expander arrow
    # on lazy-loaded directories before their real children are loaded.
    PLACEHOLDER_TAG = "placeholder"

    def __init__(self, parent, root_widget, project_root, open_file_callback, status_callback):
        self.parent = parent
        self.root_widget = root_widget
        self.project_root = project_root
        self.open_file_callback = open_file_callback
        self.status_callback = status_callback

        self.lang = langs_loader.langs()

        self.folder_icon = None
        self.default_file_icon = None
        self.file_icons = {}
        self._right_click_item = None
        self._right_click_path = None
        self._icon_cache = {}
        self._children_loaded = set()

        self._build_tree()
        # Defer icon loading (PIL import + Image.open) to the first idle tick so
        # it does not block startup; the tree renders without icons first, then
        # icons are applied once loaded.
        self.root_widget.after(0, self._apply_icons_to_all)

    def _get_text(self, key):
        return getattr(self.lang, key.replace('.', '_'), key)

    def _build_tree(self):
        self.tree = ttk.Treeview(self.root_widget, selectmode="browse",
                                 columns=("path",), show="tree")
        self.tree.column("path", width=0, stretch=False)
        self.tree.heading("path", text="")
        self.tree.pack(fill="both", expand=True, padx=3, pady=3)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        # Single-click on a folder's label toggles expand/collapse so the user
        # does not have to aim for the small triangle indicator.
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")
        self._populate_root()

    def _ensure_icons(self):
        """Load icons on first use if not already loaded.

        Called by user-triggered operations (expand, populate) so the heavy
        PIL import and Image.open calls happen lazily rather than at startup.
        """
        if not self._icon_cache:
            self._load_icons_lazy()

    def _apply_icons_to_all(self):
        """Load icons on the first idle tick and apply them to existing nodes.

        Walks the whole tree and sets the correct image on each item based on
        its stored path, so nodes created before icons were loaded get their
        icons retroactively without rebuilding the tree.
        """
        self._ensure_icons()
        for root in self.tree.get_children():
            self._apply_icons_recursive(root)

    def _apply_icons_recursive(self, item):
        """Recursively apply the correct icon to an item and its descendants.

        Args:
            item: Tree item id to apply icons to
        """
        path = self.tree.set(item, "path")
        if path:
            if os.path.isdir(path):
                if self.folder_icon:
                    self.tree.item(item, image=self.folder_icon)
            else:
                _, ext = os.path.splitext(path)
                ext = ext.lstrip('.').lower()
                icon = self.file_icons.get(ext, self.default_file_icon)
                if icon:
                    self.tree.item(item, image=icon)
        for child in self.tree.get_children(item):
            self._apply_icons_recursive(child)

    def _clear_placeholder(self, item):
        """Remove placeholder child nodes from an item.

        Placeholders exist only to make the ttk expander arrow visible for
        lazy-loaded directories; they are replaced by real children on expand.

        Args:
            item: Tree item id whose placeholder children should be removed
        """
        for child in self.tree.get_children(item):
            tags = self.tree.item(child, "tags") or ()
            if self.PLACEHOLDER_TAG in tags:
                self.tree.delete(child)

    def _load_icons_lazy(self):
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
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._children_loaded.clear()

        if not os.path.exists(self.project_root):
            _logger.warning("Project root does not exist: %s", self.project_root)
            return

        _logger.debug("Populating tree root: %s", self.project_root)
        node = self.tree.insert("", "end", text=os.path.basename(self.project_root), open=False)
        self.tree.set(node, "path", self.project_root)

        self._add_children(node, self.project_root, load_icons=True)
        self._children_loaded.add(node)

    def populate_tree(self, parent="", path=None):
        self._ensure_icons()
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

    def _on_tree_click(self, event):
        """Toggle expand/collapse when clicking a folder's label or indicator.

        ttk natively toggles on indicator (triangle) clicks, so we skip those
        to avoid double-toggling. For clicks on the folder's text or image we
        toggle manually so the user doesn't have to aim for the small triangle.
        Focus is set before toggling so <<TreeviewOpen>> receives the correct
        item (our widget-level binding runs before ttk's class binding which
        normally sets focus).

        Args:
            event: The mouse click event
        """
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # identify("element", ...) returns names like "Treeitem.indicator",
        # "Treeitem.text", "Treeitem.image" etc. — check with "in" for robustness.
        try:
            element = self.tree.identify("element", event.x, event.y)
        except Exception:
            return
        if element and "indicator" in element:
            # ttk handles indicator clicks natively; let it through.
            return
        path = self.tree.set(item, "path")
        if not path or not os.path.isdir(path):
            return
        # Set focus/selection BEFORE toggling so <<TreeviewOpen>> (fired
        # synchronously by item(open=True)) sees the correct focused item.
        self.tree.focus(item)
        self.tree.selection_set(item)
        # Toggle the open state; ttk fires <<TreeviewOpen>> when opening.
        if self.tree.item(item, "open"):
            self.tree.item(item, open=False)
        else:
            self.tree.item(item, open=True)

    def _on_tree_open(self, event):
        item = self.tree.focus()
        if not item:
            return

        path = self.tree.set(item, "path")
        if not path or not os.path.isdir(path):
            return

        if item not in self._children_loaded:
            # Remove the placeholder child used to render the expander arrow
            # before inserting the directory's real children.
            self._clear_placeholder(item)
            self._ensure_icons()
            self._add_children(item, path, load_icons=True)
            self._children_loaded.add(item)

    def refresh(self):
        """Incrementally refresh the tree preserving expansion and loaded state.

        Instead of deleting and rebuilding the whole tree, this diffs each
        already-loaded directory against the filesystem: new entries are
        inserted, removed entries deleted, and unchanged directories keep
        their expansion state and loaded children. Large projects therefore
        refresh without collapsing expanded folders or re-listing every dir.
        """
        if not os.path.exists(self.project_root):
            return
        root_children = self.tree.get_children()
        if not root_children:
            self._populate_root()
            return
        root_item = root_children[0]
        self._refresh_children(root_item, self.project_root)

    def _list_sorted(self, path):
        """List a directory returning dir-first, case-insensitively sorted entries.

        Args:
            path: Directory to list

        Returns:
            list[tuple[str, str, bool]]: (name, full_path, is_dir) tuples with
            directories first, each group sorted case-insensitively.
        """
        try:
            names = os.listdir(path)
        except PermissionError:
            return []
        dirs = []
        files = []
        for name in names:
            if name.startswith('.') or name in self.IGNORED_DIRS:
                continue
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            entry = (name, full_path, is_dir)
            if is_dir:
                dirs.append(entry)
            else:
                files.append(entry)
        dirs.sort(key=lambda e: e[0].lower())
        files.sort(key=lambda e: e[0].lower())
        return dirs + files

    def _insert_node(self, parent, name, full_path, is_dir):
        """Insert a single tree node with the appropriate icon.

        For directories a placeholder child is inserted so the ttk.Treeview
        expander arrow is visible before real children are lazy-loaded.

        Args:
            parent: Parent tree item id
            name: Display name
            full_path: Absolute path stored in the "path" column
            is_dir: Whether the entry is a directory

        Returns:
            The newly created tree item id
        """
        if is_dir:
            node = self.tree.insert(parent, "end", text=name, open=False,
                                    image=self.folder_icon if self.folder_icon else '')
            self.tree.set(node, "path", full_path)
            # Insert a placeholder child so the expander arrow is shown even
            # before the directory's real children are loaded on expand.
            self.tree.insert(node, "end", text="", tags=(self.PLACEHOLDER_TAG,))
            return node
        else:
            _, ext = os.path.splitext(name)
            ext = ext.lstrip('.').lower()
            icon = self.file_icons.get(ext, self.default_file_icon)
            node = self.tree.insert(parent, "end", text=name, image=icon if icon else '')
            self.tree.set(node, "path", full_path)
            return node

    def _refresh_children(self, parent_item, path):
        """Refresh direct children of parent_item with minimal churn.

        Diffs the current children against the filesystem: keeps unchanged
        nodes (recursing into already-loaded directories), inserts new ones,
        and deletes gone ones. Expansion state of kept directories is
        preserved because their tree items are not touched.

        Args:
            parent_item: Tree item id whose children to refresh
            path: Filesystem path of parent_item
        """
        entries = self._list_sorted(path)
        # Map existing child path -> item id, skipping placeholder nodes that
        # only exist to render the expander arrow for lazy-loaded directories.
        existing = {}
        for child in self.tree.get_children(parent_item):
            tags = self.tree.item(child, "tags") or ()
            if self.PLACEHOLDER_TAG in tags:
                continue
            try:
                existing[self.tree.set(child, "path")] = child
            except Exception:
                continue

        new_paths = set()
        for name, full_path, is_dir in entries:
            new_paths.add(full_path)
            if full_path in existing:
                # Unchanged node: recurse into already-loaded directories.
                child_item = existing[full_path]
                if is_dir and child_item in self._children_loaded:
                    child_path = self.tree.set(child_item, "path")
                    self._refresh_children(child_item, child_path)
            else:
                self._insert_node(parent_item, name, full_path, is_dir)

        # Delete nodes that no longer exist on disk.
        for full_path, child_item in existing.items():
            if full_path not in new_paths:
                self._children_loaded.discard(child_item)
                try:
                    self.tree.delete(child_item)
                except Exception:
                    pass

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
        """Populate a tree node with its filesystem children.

        Uses dir-first case-insensitive sorting via _list_sorted and the
        shared _insert_node helper so insertion logic is reused by refresh.

        Args:
            parent: Parent tree item id
            path: Filesystem path to list
            load_icons: Whether to ensure icons are loaded first
        """
        entries = self._list_sorted(path)
        for name, full_path, is_dir in entries:
            self._insert_node(parent, name, full_path, is_dir)

    def on_tree_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        path = self.tree.set(item, "path")
        if path and os.path.isfile(path):
            self.open_file_callback(path)
        elif path and os.path.isdir(path):
            # Set focus before toggling so <<TreeviewOpen>> sees the right item.
            self.tree.focus(item)
            if self.tree.item(item, 'open'):
                self.tree.item(item, open=False)
            else:
                self.tree.item(item, open=True)
                if item not in self._children_loaded:
                    self._clear_placeholder(item)
                    self._ensure_icons()
                    self._add_children(item, path, load_icons=True)
                    self._children_loaded.add(item)

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
        menu.add_command(label=self._get_text("tree.refresh"), command=self.refresh)
        menu.add_separator()
        menu.add_command(label=self._get_text("tree.new_file"), command=self.menu_new_file)
        menu.add_command(label=self._get_text("tree.new_folder"), command=self.menu_new_folder)
        menu.add_separator()
        menu.add_command(label=self._get_text("tree.rename"), command=self.menu_rename)
        menu.add_command(label=self._get_text("tree.delete"), command=self.menu_delete)
        menu.add_command(label=self._get_text("tree.move_trash"), command=self.menu_move_to_trash)
        menu.post(event.x_root, event.y_root)

    def menu_new_file(self):
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        name = simpledialog.askstring(self._get_text("tree.new_file"), self._get_text("tree.enter_file_name"))
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                pass
            self.refresh()
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("tree.failed_create") + f" {e}")

    def menu_new_folder(self):
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        name = simpledialog.askstring(self._get_text("tree.new_folder"), self._get_text("tree.enter_folder_name"))
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            os.mkdir(full_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("tree.failed_create_folder") + f" {e}")

    def menu_rename(self):
        if not self._right_click_item:
            return
        old_path = self._right_click_path
        old_name = os.path.basename(old_path)
        new_name = simpledialog.askstring(self._get_text("tree.rename"), self._get_text("tree.enter_new_name"), initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        try:
            os.rename(old_path, new_path)
            self.refresh()
            return old_path, new_path
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("tree.failed_rename") + f" {e}")
            return None, None

    def menu_delete(self):
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno(self._get_text("tree.confirm_delete_title"), self._get_text("tree.confirm_delete").format(name=os.path.basename(path))):
            return
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            self.refresh()
            return path
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("tree.failed_delete") + f" {e}")
            return None

    def menu_move_to_trash(self):
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno(self._get_text("tree.confirm_trash_title"), self._get_text("tree.confirm_trash").format(name=os.path.basename(path))):
            return
        try:
            send2trash = LazyLoader.get_send2trash()
            if send2trash:
                send2trash.send2trash(path)
            else:
                if messagebox.askyesno(self._get_text("tree.send2trash_missing_title"), self._get_text("tree.send2trash_missing")):
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                else:
                    return
            self.refresh()
            return path
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("tree.failed_trash") + f" {e}")
            return None