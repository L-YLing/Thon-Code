#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas File Tree",
    "Path": ".main.libs.gui_libs.file_tree.canvas_tree",
    "Entrance": "main.py"
}

"""
Canvas-based file tree widget with customizable styling.

Provides a highly customizable file tree using Canvas for rendering,
supporting folder/file icons, expand/collapse, context menus, and
keyboard navigation with a style system interface.
"""

import os
import bisect
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider, EventHandler, LazyLoadable


class TreeNode:
    """Represents a node in the file tree hierarchy.

    Attributes:
        path: Absolute filesystem path
        name: Display name of the node
        is_dir: Whether the node is a directory
        children: List of child TreeNode objects
        expanded: Whether the node is currently expanded
        icon: Icon identifier for display
    """

    def __init__(self, path: str, name: str = "", is_dir: bool = False) -> None:
        """Initialize a tree node.

        Args:
            path: Absolute filesystem path
            name: Display name for the node
            is_dir: Whether this node is a directory
        """
        self.path = path
        self.name = name or os.path.basename(path)
        self.is_dir = is_dir
        self.children: List[TreeNode] = []
        self.expanded: bool = False
        self.icon: str = ""

    def get_icon(self) -> str:
        """Get the icon string for display.

        Returns:
            Icon character or string
        """
        if self.is_dir:
            return "📂" if self.expanded else "📁"
        return "📄"

    def __repr__(self) -> str:
        return f"TreeNode({self.name}, dir={self.is_dir}, children={len(self.children)})"


class CanvasFileTree(BaseWidget, StyleProvider, EventHandler, LazyLoadable):
    """Canvas-based file tree with customizable styling and interactions.

    Features:
    - Canvas rendering for full control over appearance
    - Expand/collapse nodes with indicator animation
    - Folder/file visual distinction with icons
    - Right-click context menus
    - Keyboard navigation (arrow keys, Enter, etc.)
    - Drag selection and hover highlighting
    - Style system integration for colors, fonts, spacing
    - Lazy loading for child nodes (load on expand)
    """

    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        """Initialize the canvas file tree.

        Args:
            parent: Parent widget container
            **kwargs: Additional configuration options
        """
        self._parent = parent
        self._canvas: Optional[tk.Canvas] = None
        self._main_frame: Optional[tk.Frame] = None
        self._scrollbar: Optional[tk.Scrollbar] = None

        self._root_node: Optional[TreeNode] = None
        self._selected_node: Optional[TreeNode] = None
        self._hover_node: Optional[TreeNode] = None
        self._nodes_by_y: List[Tuple[int, TreeNode]] = []
        self._visible_nodes: List[TreeNode] = []
        # Cached depth and y-position per node, populated in _refresh_visible_nodes.
        self._node_depths: Dict[TreeNode, int] = {}
        self._node_y_pos: Dict[TreeNode, int] = {}

        self._project_root: str = ""
        self._indent_width: int = 16
        self._row_height: int = 22
        self._font_size: int = 10
        self._font_family: str = "Microsoft YaHei"
        self._font: Optional[tk.font.Font] = None
        self._icon_size: int = 16
        self._bg_color: str = "#282c34"
        self._fg_color: str = "#abb2bf"
        self._hover_bg: str = "#3e4451"
        self._sel_bg: str = "#264f78"
        self._sel_fg: str = "#ffffff"
        self._expand_indicator: str = "▾"
        self._collapse_indicator: str = "▸"

        self._loaded: bool = False
        self._drag_start_y: Optional[int] = None
        self._is_dragging: bool = False

        self._on_node_open: Optional[Callable[[TreeNode], None]] = None
        self._on_node_select: Optional[Callable[[TreeNode], None]] = None
        self._on_node_expand: Optional[Callable[[TreeNode], None]] = None
        self._on_context_menu: Optional[Callable[[TreeNode, tk.Event], None]] = None

        self._style_system = StyleSystem()

        super().__init__(parent)

    def create_widget(self) -> tk.Frame:
        """Create the file tree widget hierarchy.

        Returns:
            The main frame containing the tree canvas
        """
        self._main_frame = tk.Frame(self._parent)
        self._load_style()
        self._setup_canvas()
        self._setup_scrollbar()
        self._setup_layout()
        self._setup_bindings()
        self._loaded = True
        return self._main_frame

    def _load_style(self) -> None:
        """Load tree style configuration from StyleSystem."""
        self._font_family = self._style_system.get_value("tree", "font_family", "Microsoft YaHei")
        self._font_size = self._style_system.get_value("tree", "font_size", 10)
        self._indent_width = self._style_system.get_value("tree", "indent_width", 16)
        self._row_height = self._style_system.get_value("tree", "row_height", 22)
        self._icon_size = self._style_system.get_value("tree", "icon_size", 16)
        self._bg_color = self._style_system.get_value("tree", "bg", "#282c34")
        self._fg_color = self._style_system.get_value("tree", "fg", "#abb2bf")
        self._hover_bg = self._style_system.get_value("tree", "hover_bg", "#3e4451")
        self._sel_bg = self._style_system.get_value("tree", "selection_bg", "#264f78")
        self._sel_fg = self._style_system.get_value("tree", "selection_fg", "#ffffff")
        self._expand_indicator = self._style_system.get_value("tree", "expand_indicator", "▾")
        self._collapse_indicator = self._style_system.get_value("tree", "collapse_indicator", "▸")
        self._font = tk.font.Font(family=self._font_family, size=self._font_size)

    def _setup_canvas(self) -> None:
        """Create the Canvas widget for tree rendering."""
        self._canvas = tk.Canvas(
            self._main_frame,
            bg=self._bg_color,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
            cursor="hand2",
        )

    def _setup_scrollbar(self) -> None:
        """Create the vertical scrollbar."""
        self._scrollbar = tk.Scrollbar(
            self._main_frame,
            orient="vertical",
            command=self._canvas.yview
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

    def _setup_layout(self) -> None:
        """Arrange tree widgets in the correct layout."""
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

    def _setup_bindings(self) -> None:
        """Setup keyboard, mouse, and scroll event bindings."""
        self._canvas.bind("<Button-1>", self._on_left_click)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<Button-3>", self._on_right_click)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_drag_release)
        self._canvas.bind("<Motion>", self._on_hover)
        self._canvas.bind("<Leave>", self._on_leave)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>", lambda e: self._canvas.yview_scroll(1, "units"))
        self._canvas.bind("<Configure>", lambda e: self._redraw())
        self._canvas.bind("<Key>", self._on_key)
        self._canvas.focus_set()

    # ---- Public API ----

    def set_project_root(self, path: str) -> None:
        """Set the project root directory and rebuild the tree.

        Args:
            path: Absolute path to the project root
        """
        self._project_root = path
        self._root_node = TreeNode(path, os.path.basename(path), is_dir=True)
        self._load_children(self._root_node)
        self._root_node.expanded = True
        self._refresh_visible_nodes()
        self._redraw()

    def refresh(self) -> None:
        """Refresh the tree by reloading from the project root."""
        if self._project_root:
            self.set_project_root(self._project_root)

    def get_selected_node(self) -> Optional[TreeNode]:
        """Get the currently selected tree node.

        Returns:
            The selected TreeNode or None
        """
        return self._selected_node

    def get_project_root(self) -> str:
        """Get the current project root path.

        Returns:
            Project root path
        """
        return self._project_root

    def set_on_node_open(self, callback: Callable[[TreeNode], None]) -> None:
        """Set callback for double-click (open) events.

        Args:
            callback: Function receiving the opened node
        """
        self._on_node_open = callback

    def set_on_node_select(self, callback: Callable[[TreeNode], None]) -> None:
        """Set callback for single-click (select) events.

        Args:
            callback: Function receiving the selected node
        """
        self._on_node_select = callback

    def set_on_node_expand(self, callback: Callable[[TreeNode], None]) -> None:
        """Set callback for node expand/collapse events.

        Args:
            callback: Function receiving the expanded node
        """
        self._on_node_expand = callback

    def set_on_context_menu(self, callback: Callable[[TreeNode, tk.Event], None]) -> None:
        """Set callback for context menu requests.

        Args:
            callback: Function receiving node and event
        """
        self._on_context_menu = callback

    def expand_node(self, node: TreeNode) -> None:
        """Expand a tree node to show its children.

        Args:
            node: TreeNode to expand
        """
        if node.is_dir:
            self._load_children(node)
            node.expanded = True
            self._refresh_visible_nodes()
            self._redraw()
            if self._on_node_expand:
                self._on_node_expand(node)

    def collapse_node(self, node: TreeNode) -> None:
        """Collapse a tree node to hide its children.

        Args:
            node: TreeNode to collapse
        """
        if node.is_dir:
            node.expanded = False
            self._refresh_visible_nodes()
            self._redraw()

    # ---- Internal Methods ----

    def _load_children(self, node: TreeNode) -> None:
        """Load child nodes for a directory node.

        Args:
            node: Parent TreeNode to load children for
        """
        if not node.is_dir or not os.path.isdir(node.path):
            return

        node.children.clear()
        try:
            entries = sorted(os.listdir(node.path))
        except PermissionError:
            return

        skip_dirs = {'.git', '.idea', '.vscode', 'node_modules', '__pycache__', 'dist', 'build'}

        for entry in entries:
            if entry.startswith('.') or entry in skip_dirs:
                continue
            full_path = os.path.join(node.path, entry)
            is_dir = os.path.isdir(full_path)
            child = TreeNode(full_path, entry, is_dir=is_dir)
            node.children.append(child)

    def _refresh_visible_nodes(self) -> None:
        """Rebuild the flat list of visible nodes from the tree hierarchy.

        Depth is computed during traversal and cached in _node_depths so that
        _get_depth becomes an O(1) lookup instead of an O(n) rescan per node
        (which previously made _redraw O(n^2)).
        """
        self._visible_nodes = []
        self._nodes_by_y = []
        self._node_depths = {}
        self._node_y_pos = {}

        def traverse(node: TreeNode, depth: int) -> None:
            y_pos = len(self._visible_nodes) * self._row_height
            self._visible_nodes.append(node)
            self._nodes_by_y.append((y_pos, node))
            self._node_depths[node] = depth
            self._node_y_pos[node] = y_pos
            if node.expanded:
                for child in node.children:
                    traverse(child, depth + 1)

        if self._root_node:
            traverse(self._root_node, 0)

    def _redraw(self) -> None:
        """Redraw only the tree nodes within the current viewport.

        Virtualized rendering: computes the visible y-range from the canvas
        yview and height, and draws only nodes whose row intersects it. For
        large projects this keeps each redraw proportional to the number of
        on-screen rows rather than the total node count.
        """
        if not self._canvas:
            return

        self._canvas.delete("all")
        total_height = len(self._visible_nodes) * self._row_height
        canvas_width = self._canvas.winfo_width()
        self._canvas.configure(scrollregion=(0, 0, canvas_width, total_height))

        # Determine the viewport y-range in canvas coordinates.
        try:
            yview = self._canvas.yview()
            view_height = self._canvas.winfo_height()
        except Exception:
            return
        if view_height <= 1:
            # Widget not yet laid out; draw a small prefix so the tree is visible.
            view_height = max(1, total_height)
        y_top = yview[0] * total_height
        y_bottom = y_top + view_height

        # Binary-search the first node whose row bottom is below the viewport
        # top, then iterate only until rows pass the viewport bottom.
        # _nodes_by_y is sorted by y_pos; build a parallel keys list for bisection.
        ys = [ny for ny, _ in self._nodes_by_y]
        start_idx = bisect.bisect_right(ys, y_top - self._row_height)
        for i in range(start_idx, len(self._nodes_by_y)):
            y_pos, node = self._nodes_by_y[i]
            if y_pos > y_bottom:
                break
            self._draw_node(node, y_pos)

    def _draw_node(self, node: TreeNode, y: int) -> None:
        """Draw a single tree node on the canvas.

        Args:
            node: TreeNode to draw
            y: Y coordinate for the node
        """
        # Depth comes from the traversal cache (O(1)) instead of rescanning.
        depth = self._node_depths.get(node, 0)
        x = depth * self._indent_width + 4

        # Draw selection/hover background
        is_selected = node == self._selected_node
        is_hover = node == self._hover_node

        if is_selected:
            self._canvas.create_rectangle(
                0, y, self._canvas.winfo_width(), y + self._row_height,
                fill=self._sel_bg, outline=""
            )
        elif is_hover:
            self._canvas.create_rectangle(
                0, y, self._canvas.winfo_width(), y + self._row_height,
                fill=self._hover_bg, outline=""
            )

        # Draw expand/collapse indicator
        if node.is_dir:
            indicator = self._expand_indicator if node.expanded else self._collapse_indicator
            self._canvas.create_text(
                x, y + self._row_height // 2,
                text=indicator,
                anchor="w",
                font=self._font,
                fill=self._fg_color,
            )

        # Draw icon
        icon_x = x + self._indent_width
        icon_text = node.get_icon()
        self._canvas.create_text(
            icon_x, y + self._row_height // 2,
            text=icon_text,
            anchor="w",
            font=self._font,
        )

        # Draw node name
        name_x = icon_x + self._icon_size + 4
        color = self._sel_fg if is_selected else self._fg_color
        self._canvas.create_text(
            name_x, y + self._row_height // 2,
            text=node.name,
            anchor="w",
            font=self._font,
            fill=color,
        )

    def _get_depth(self, node: TreeNode) -> int:
        """Get the cached depth of a node.

        Args:
            node: TreeNode to calculate depth for

        Returns:
            Depth level (0 for root)
        """
        return self._node_depths.get(node, 0)

    def _find_node_at_y(self, y: int) -> Optional[TreeNode]:
        """Find the tree node at a given y coordinate via binary search.

        Args:
            y: Y coordinate in canvas units

        Returns:
            TreeNode at the coordinate or None
        """
        if not self._nodes_by_y:
            return None
        yview = self._canvas.yview()
        total_height = len(self._visible_nodes) * self._row_height
        y_offset = yview[0] * total_height
        adjusted_y = y + y_offset

        ys = [ny for ny, _ in self._nodes_by_y]
        # Locate the rightmost row start <= adjusted_y.
        idx = bisect.bisect_right(ys, adjusted_y) - 1
        if idx < 0:
            return None
        node_y, node = self._nodes_by_y[idx]
        if node_y <= adjusted_y <= node_y + self._row_height:
            return node
        return None

    def _on_left_click(self, event: tk.Event) -> None:
        """Handle left click for node selection and expand/collapse.

        Args:
            event: The mouse click event
        """
        node = self._find_node_at_y(event.y)
        if node:
            self._selected_node = node
            self._redraw()
            if node.is_dir:
                # Check if click was on the expand indicator
                depth = self._get_depth(node)
                indicator_x = depth * self._indent_width + 4 + self._indent_width
                if event.x <= indicator_x or not node.expanded:
                    if node.expanded:
                        self.collapse_node(node)
                    else:
                        self.expand_node(node)
            if self._on_node_select:
                self._on_node_select(node)

    def _on_double_click(self, event: tk.Event) -> None:
        """Handle double click for file opening or folder expand.

        Args:
            event: The mouse double-click event
        """
        node = self._find_node_at_y(event.y)
        if node:
            if node.is_dir:
                if node.expanded:
                    self.collapse_node(node)
                else:
                    self.expand_node(node)
            else:
                if self._on_node_open:
                    self._on_node_open(node)

    def _on_right_click(self, event: tk.Event) -> None:
        """Handle right click for context menu.

        Args:
            event: The mouse right-click event
        """
        node = self._find_node_at_y(event.y)
        if node:
            self._selected_node = node
            self._redraw()
            if self._on_context_menu:
                self._on_context_menu(node, event)

    def _on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag for selection.

        Args:
            event: The mouse drag event
        """
        if self._drag_start_y is None:
            self._drag_start_y = event.y
            self._is_dragging = True
        node = self._find_node_at_y(event.y)
        if node and node != self._selected_node:
            self._selected_node = node
            self._redraw()

    def _on_drag_release(self, event: tk.Event) -> None:
        """Handle mouse button release after drag.

        Args:
            event: The mouse event
        """
        self._drag_start_y = None
        self._is_dragging = False

    def _on_hover(self, event: tk.Event) -> None:
        """Handle mouse hover for highlighting.

        Args:
            event: The mouse motion event
        """
        node = self._find_node_at_y(event.y)
        if node != self._hover_node:
            self._hover_node = node
            self._redraw()

    def _on_leave(self, event: tk.Event) -> None:
        """Handle mouse leave for clearing hover highlight.

        Args:
            event: The mouse leave event
        """
        self._hover_node = None
        self._redraw()

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel scrolling.

        Args:
            event: The mouse wheel event
        """
        delta = -1 * (event.delta / 120)
        self._canvas.yview_scroll(int(delta), "units")

    def _on_key(self, event: tk.Event) -> None:
        """Handle keyboard navigation.

        Args:
            event: The keyboard event
        """
        if not self._selected_node:
            return

        idx = self._visible_nodes.index(self._selected_node) if self._selected_node in self._visible_nodes else -1

        if event.keysym == "Down":
            idx = min(idx + 1, len(self._visible_nodes) - 1)
            self._selected_node = self._visible_nodes[idx]
            self._ensure_visible(self._selected_node)
            self._redraw()
        elif event.keysym == "Up":
            idx = max(idx - 1, 0)
            self._selected_node = self._visible_nodes[idx]
            self._ensure_visible(self._selected_node)
            self._redraw()
        elif event.keysym == "Right":
            if self._selected_node.is_dir and not self._selected_node.expanded:
                self.expand_node(self._selected_node)
        elif event.keysym == "Left":
            if self._selected_node.is_dir and self._selected_node.expanded:
                self.collapse_node(self._selected_node)
        elif event.keysym == "Return":
            if self._selected_node.is_dir:
                if self._selected_node.expanded:
                    self.collapse_node(self._selected_node)
                else:
                    self.expand_node(self._selected_node)
            elif self._on_node_open:
                self._on_node_open(self._selected_node)

    def _ensure_visible(self, node: TreeNode) -> None:
        """Ensure a node is visible by scrolling.

        Args:
            node: TreeNode to make visible
        """
        if node in self._visible_nodes:
            idx = self._visible_nodes.index(node)
            y_pos = idx * self._row_height
            self._canvas.yview_moveto(max(0, (y_pos - self._row_height) / max(1, len(self._visible_nodes) * self._row_height)))

    # ---- BaseWidget Implementation ----

    def pack(self, **kwargs) -> None:
        """Pack the tree widget into its parent.

        Args:
            **kwargs: Pack configuration options
        """
        if self._main_frame:
            self._main_frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        """Grid the tree widget into its parent.

        Args:
            **kwargs: Grid configuration options
        """
        if self._main_frame:
            self._main_frame.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the tree widget and free resources."""
        if self._main_frame and not self._destroyed:
            self._main_frame.destroy()
            self._destroyed = True

    # ---- StyleProvider Implementation ----

    def apply_style(self, style_name: str) -> None:
        """Apply a named style to the tree.

        Args:
            style_name: Name of the style to apply
        """
        if self._style_system.apply_style(style_name) and self._loaded:
            self._load_style()
            self._redraw()

    def get_style_value(self, key: str, default: Any = None) -> Any:
        """Get a style value by key.

        Args:
            key: Style property key
            default: Default value

        Returns:
            The style value
        """
        return self._style_system.get_value("tree", key, default)

    def set_style_value(self, key: str, value: Any) -> None:
        """Set a single style property.

        Args:
            key: Style property key
            value: New value
        """
        self._style_system.set_style("tree", key, value)

    # ---- LazyLoadable Implementation ----

    def load(self) -> None:
        """Load and initialize the tree on demand."""
        if not self._loaded:
            self.create_widget()

    def unload(self) -> None:
        """Unload and release tree resources."""
        if self._loaded:
            self.destroy()
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the tree is currently loaded.

        Returns:
            bool: True if loaded
        """
        return self._loaded

    # ---- EventHandler Implementation ----

    def on_key_press(self, event: Any) -> Optional[str]:
        """Handle key press events.

        Args:
            event: The keyboard event

        Returns:
            Optional[str]: 'break' if consumed
        """
        self._on_key(event)
        return None

    def on_mouse_click(self, event: Any) -> None:
        """Handle mouse click events.

        Args:
            event: The mouse event
        """
        self._on_left_click(event)

    def on_mouse_drag(self, event: Any) -> None:
        """Handle mouse drag events.

        Args:
            event: The mouse event
        """
        self._on_drag(event)

    def on_mouse_hover(self, event: Any) -> None:
        """Handle mouse hover events.

        Args:
            event: The mouse event
        """
        self._on_hover(event)

    # ---- Access Methods ----

    def get_widget(self) -> Optional[tk.Frame]:
        """Get the underlying Tkinter widget.

        Returns:
            The main frame widget
        """
        return self._main_frame

    def get_canvas(self) -> Optional[tk.Canvas]:
        """Get the canvas widget.

        Returns:
            The canvas widget
        """
        return self._canvas