# Canvas 代码编辑器

## 功能描述

基于 Canvas 实现的高度可自定义代码编辑器组件。采用混合架构设计：
- `tk.Text` 处理文本编辑、IME、剪贴板、撤销/重做、无障碍访问
- `Canvas` 覆盖层渲染行号、折叠指示器和自定义装饰

## 核心组件

### CanvasCodeEditor (`canvas_editor.py`)

主编辑器组件，提供完整的代码编辑功能。

**API 接口：**

| 方法 | 描述 | 参数 | 返回值 |
|------|------|------|--------|
| `create_widget()` | 创建编辑器控件 | 无 | `tk.Frame`: 主框架 |
| `get_content()` | 获取编辑器内容 | 无 | `str`: 文本内容 |
| `set_content(content)` | 设置编辑器内容 | `content: str` 文本内容 | `None` |
| `clear()` | 清空编辑器 | 无 | `None` |
| `open_file(file_path)` | 打开文件 | `file_path: str` 文件路径 | `bool`: 是否成功 |
| `save_file(file_path?)` | 保存文件 | `file_path: Optional[str]` | `bool`: 是否成功 |
| `select_all()` | 全选文本 | 无 | `str`: 'break' |
| `apply_style(style_name)` | 应用样式 | `style_name: str` | `None` |
| `load()` | 懒加载初始化 | 无 | `None` |
| `unload()` | 卸载释放资源 | 无 | `None` |

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `is_dirty` | `bool` | 是否有未保存的修改 |
| `current_file` | `Optional[str]` | 当前打开的文件路径 |
| `is_loaded` | `bool` | 组件是否已加载 |

### EditorGutter (`editor_gutter.py`)

基于 Canvas 的侧边栏组件，显示行号和折叠指示器。

**API 接口：**

| 方法 | 描述 | 参数 |
|------|------|------|
| `set_foldable_regions(regions)` | 设置可折叠区域 | `regions: List[Tuple[int, int]]` |
| `set_folded_lines(folded)` | 设置已折叠行 | `folded: Dict[int, int]` |
| `get_folded_lines()` | 获取已折叠行 | 无 |
| `set_on_line_click(callback)` | 设置行号点击回调 | `callback: Callable[[int], None]` |
| `set_on_fold_click(callback)` | 设置折叠点击回调 | `callback: Callable[[int], None]` |
| `sync_scroll()` | 同步滚动 | 无 |
| `redraw()` | 强制重绘 | 无 |

## 使用示例

```python
from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
from libs.gui_libs.style_system import StyleSystem

# 创建编辑器
editor = CanvasCodeEditor(parent_frame)
editor.create_widget()
editor.pack(fill="both", expand=True)

# 设置内容
editor.set_content("print('Hello, World!')")

# 打开和保存文件
editor.open_file("example.py")
editor.save_file()

# 应用样式
style_system = StyleSystem()
style_system.set_style("editor", "bg", "#1e1e1e")
editor.apply_style("default")

# 使用回调
editor.set_on_file_changed(lambda path: print(f"已打开: {path}"))
editor.set_on_text_modified(lambda: print("文本已修改"))
```

## 样式配置

通过 `StyleSystem` 进行样式管理，支持 JSON 文件加载和运行时修改。

```python
from libs.gui_libs.style_system import StyleSystem

ss = StyleSystem()

# 读取样式值
bg = ss.get_value("editor", "bg")
font = ss.get_value("editor", "font_family")

# 修改样式
ss.set_style("editor", "bg", "#ffffff")
ss.set_component_style("editor", {"bg": "#fff", "fg": "#000"})

# 从文件加载
ss.load_from_file("my_style.json")
```

## 注意事项

- 编辑器采用懒加载机制，需调用 `load()` 或 `create_widget()` 初始化
- 语法高亮依赖语言配置文件，位于 `assets/languages/` 目录
- 折叠功能使用 tk.Text 的 elide 标签实现
- 建议在主线程中创建和操作 Tkinter 控件
- `is_dirty` 属性为只读，反映当前修改状态

## 已知限制

- 自动补全系统为框架占位，需要后续完整实现
- 拖拽操作仅处理文本选择，不支持文件拖放
- 部分高级编辑器功能（多光标、分屏）暂未实现
- 仅支持单文件编辑，暂不支持标签页