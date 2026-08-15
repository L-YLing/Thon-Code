# Canvas File Tree

## Description

A highly customizable file tree component built with Canvas. Provides filesystem browsing, directory expand/collapse, node selection, and context menus for IDE-standard file tree functionality.

## Core Components

### CanvasFileTree (`canvas_tree.py`)

Main file tree component providing complete filesystem browsing.

**API Interface:**

| Method | Description | Parameters | Return Value |
|--------|-------------|-----------|-------------|
| `create_widget()` | Create file tree widget | None | `tk.Frame`: Main frame |
| `set_project_root(path)` | Set project root directory | `path: str` directory path | `None` |
| `refresh()` | Refresh file tree | None | `None` |
| `get_selected_node()` | Get currently selected node | None | `Optional[TreeNode]` |
| `get_project_root()` | Get current project root path | None | `str` |
| `expand_node(node)` | Expand a node | `node: TreeNode` | `None` |
| `collapse_node(node)` | Collapse a node | `node: TreeNode` | `None` |
| `set_on_node_open(cb)` | Set open callback | `cb: Callable[[TreeNode], None]` | `None` |
| `set_on_node_select(cb)` | Set select callback | `cb: Callable[[TreeNode], None]` | `None` |
| `set_on_node_expand(cb)` | Set expand callback | `cb: Callable[[TreeNode], None]` | `None` |
| `set_on_context_menu(cb)` | Set context menu callback | `cb: Callable[[TreeNode, Event], None]` | `None` |
| `apply_style(name)` | Apply style | `name: str` | `None` |
| `load()` | Lazy load initialization | None | `None` |
| `unload()` | Unload and release resources | None | `None` |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_loaded` | `bool` | Whether component is loaded |

### TreeNode (`canvas_tree.py`)

File tree node data model.

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `path` | `str` | Absolute filesystem path |
| `name` | `str` | Display name |
| `is_dir` | `bool` | Whether node is a directory |
| `children` | `List[TreeNode]` | Child node list |
| `expanded` | `bool` | Whether node is expanded |
| `icon` | `str` | Icon identifier |

**Methods:**

| Method | Description | Return Value |
|--------|-------------|-------------|
| `get_icon()` | Get node icon string | `str` |

## Usage Examples

```python
from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree

# Create tree
tree = CanvasFileTree(parent_frame)
tree.create_widget()
tree.pack(fill="both", expand=True)

# Set project root
tree.set_project_root("/path/to/project")

# Register callbacks
tree.set_on_node_open(lambda node: print(f"Open: {node.path}"))
tree.set_on_node_select(lambda node: print(f"Selected: {node.name}"))
tree.set_on_context_menu(lambda node, event: show_menu(node, event))

# Navigate programmatically
selected = tree.get_selected_node()
if selected and selected.is_dir:
    tree.expand_node(selected)
```

## Style Configuration

The file tree supports style configuration through StyleSystem with the following properties:

```python
from libs.gui_libs.style_system import StyleSystem

ss = StyleSystem()

# Tree-specific style keys
ss.set_style("tree", "bg", "#282c34")
ss.set_style("tree", "fg", "#abb2bf")
ss.set_style("tree", "hover_bg", "#3e4451")
ss.set_style("tree", "selection_bg", "#264f78")
ss.set_style("tree", "font_family", "Microsoft YaHei")
ss.set_style("tree", "font_size", 10)
ss.set_style("tree", "indent_width", 16)
ss.set_style("tree", "row_height", 22)
ss.set_style("tree", "icon_size", 16)
ss.set_style("tree", "expand_indicator", "▾")
ss.set_style("tree", "collapse_indicator", "▸")
```

## Event Handling

Supported mouse and keyboard events:

| Event Type | Behavior |
|------------|----------|
| Left click | Select node / toggle fold |
| Left double-click | Open file / toggle folder fold |
| Right click | Trigger context menu callback |
| Mouse drag | Dynamic node selection |
| Mouse hover | Highlight hovered node |
| Mouse wheel | Vertical scroll |
| ↑/↓ | Navigate up/down |
| ←/→ | Collapse/Expand |
| Enter | Open file or expand folder |

## Lazy Loading

Child nodes are loaded on first expansion to optimize startup performance:

```python
# Lazy loading: children loaded only on expand
tree.set_project_root("/project")  # Only root level loaded
tree.expand_node(some_folder)       # Children loaded here
```

## Notes

- Tree operations on Tkinter widgets must run on the main thread
- Expanding folders loads children and skips hidden files (starting with `.`)
- Default skipped dirs: `.git`, `.idea`, `.vscode`, `node_modules`, `__pycache__`
- `TreeNode` doesn't store parent references; depth is calculated from visible list

## Known Limitations

- Drag-and-drop to external applications not supported
- Right-click context menu must be implemented by the consumer
- Multi-select not supported
- Real-time file monitoring requires external implementation