# Canvas File Tree (Canvas 文件树组件)

## 功能描述 (Description)

基于 Canvas 实现的高度可自定义文件树组件。提供文件系统浏览、目录展开折叠、节点选择和上下文菜单等 IDE 标准文件树功能。

A highly customizable file tree component built with Canvas. Provides filesystem browsing, directory expand/collapse, node selection, and context menus for IDE-standard file tree functionality.

## 核心组件 (Core Components)

### CanvasFileTree (`canvas_tree.py`)

主文件树组件，提供完整的文件系统浏览功能。

Main file tree component providing complete filesystem browsing.

**API 接口 (API Interface):**

| 方法 | 描述 | 参数 | 返回值 |
|------|------|------|--------|
| `create_widget()` | 创建文件树控件 | 无 | `tk.Frame`: 主框架 |
| `set_project_root(path)` | 设置项目根目录 | `path: str` 目录路径 | `None` |
| `refresh()` | 刷新文件树 | 无 | `None` |
| `get_selected_node()` | 获取当前选中节点 | 无 | `Optional[TreeNode]` |
| `get_project_root()` | 获取当前项目根路径 | 无 | `str` |
| `expand_node(node)` | 展开节点 | `node: TreeNode` | `None` |
| `collapse_node(node)` | 折叠节点 | `node: TreeNode` | `None` |
| `set_on_node_open(cb)` | 设置打开回调 | `cb: Callable[[TreeNode], None]` | `None` |
| `set_on_node_select(cb)` | 设置选择回调 | `cb: Callable[[TreeNode], None]` | `None` |
| `set_on_node_expand(cb)` | 设置展开回调 | `cb: Callable[[TreeNode], None]` | `None` |
| `set_on_context_menu(cb)` | 设置右键菜单回调 | `cb: Callable[[TreeNode, Event], None]` | `None` |
| `apply_style(name)` | 应用样式 | `name: str` | `None` |
| `load()` | 懒加载初始化 | 无 | `None` |
| `unload()` | 卸载释放资源 | 无 | `None` |

**属性 (Properties):**

| 属性 | 类型 | 描述 |
|------|------|------|
| `is_loaded` | `bool` | 组件是否已加载 |

### TreeNode (`canvas_tree.py`)

文件树节点数据模型。

File tree node data model.

**属性 (Properties):**

| 属性 | 类型 | 描述 |
|------|------|------|
| `path` | `str` | 文件系统绝对路径 |
| `name` | `str` | 显示名称 |
| `is_dir` | `bool` | 是否为目录 |
| `children` | `List[TreeNode]` | 子节点列表 |
| `expanded` | `bool` | 是否已展开 |
| `icon` | `str` | 图标标识 |

**方法 (Methods):**

| 方法 | 描述 | 返回值 |
|------|------|--------|
| `get_icon()` | 获取节点图标字符串 | `str` |

## 使用示例 (Usage Examples)

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

## 样式配置 (Style Configuration)

文件树支持通过 StyleSystem 进行样式配置，可调整以下属性：

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

## 事件处理 (Event Handling)

文件树支持以下鼠标和键盘事件：

Supported mouse and keyboard events:

| 事件类型 | 行为 |
|----------|------|
| 左键单击 | 选中节点 / 切换折叠 |
| 左键双击 | 打开文件 / 切换文件夹折叠 |
| 右键单击 | 触发上下文菜单回调 |
| 鼠标拖拽 | 动态选择节点 |
| 鼠标悬停 | 高亮悬停节点 |
| 滚轮滚动 | 垂直滚动 |
| ↑/↓ | 上下导航 |
| ←/→ | 折叠/展开 |
| Enter | 打开文件或展开文件夹 |

## 懒加载机制 (Lazy Loading)

子节点在首次展开时才会加载，以优化启动性能：

Child nodes are loaded on first expansion to optimize startup performance:

```python
# Lazy loading: children loaded only on expand
tree.set_project_root("/project")  # Only root level loaded
tree.expand_node(some_folder)       # Children loaded here
```

## 注意事项 (Notes)

- 文件树仅在主线程中操作 Tkinter 控件
- 展开文件夹时会加载子节点并跳过隐藏文件（以`.`开头）
- 默认跳过的目录：`.git`, `.idea`, `.vscode`, `node_modules`, `__pycache__`
- `TreeNode` 不存储父节点引用，深度通过可见节点列表计算

- Tree operations on Tkinter widgets must run on the main thread
- Expanding folders loads children and skips hidden files (starting with `.`)
- Default skipped dirs: `.git`, `.idea`, `.vscode`, `node_modules`, `__pycache__`
- `TreeNode` doesn't store parent references; depth is calculated from visible list

## 已知限制 (Known Limitations)

- 不支持拖拽文件操作到外部应用
- 右键菜单需自行实现和提供 UI
- 暂不支持多选操作
- 文件监控（实时更新）需要外部实现

- Drag-and-drop to external applications not supported
- Right-click context menu must be implemented by the consumer
- Multi-select not supported
- Real-time file monitoring requires external implementation