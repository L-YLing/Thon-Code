# Canvas Code Editor

## Description

A highly customizable code editor component built with Canvas. Uses a hybrid architecture:
- `tk.Text` handles text editing, IME, clipboard, undo/redo, accessibility
- `Canvas` overlays render line numbers, fold indicators, and custom decorations

## Core Components

### CanvasCodeEditor (`canvas_editor.py`)

Main editor component providing full code editing functionality.

**API Interface:**

| Method | Description | Parameters | Return Value |
|--------|-------------|-----------|-------------|
| `create_widget()` | Create editor widget | None | `tk.Frame`: Main frame |
| `get_content()` | Get editor content | None | `str`: Text content |
| `set_content(content)` | Set editor content | `content: str` text content | `None` |
| `clear()` | Clear editor | None | `None` |
| `open_file(file_path)` | Open file | `file_path: str` file path | `bool`: Success status |
| `save_file(file_path?)` | Save file | `file_path: Optional[str]` | `bool`: Success status |
| `select_all()` | Select all text | None | `str`: 'break' |
| `apply_style(style_name)` | Apply style | `style_name: str` | `None` |
| `load()` | Lazy load initialization | None | `None` |
| `unload()` | Unload and release resources | None | `None` |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_dirty` | `bool` | Whether there are unsaved changes |
| `current_file` | `Optional[str]` | Currently opened file path |
| `is_loaded` | `bool` | Whether component is loaded |

### EditorGutter (`editor_gutter.py`)

Canvas-based gutter component displaying line numbers and fold indicators.

**API Interface:**

| Method | Description | Parameters |
|--------|-------------|-----------|
| `set_foldable_regions(regions)` | Set foldable regions | `regions: List[Tuple[int, int]]` |
| `set_folded_lines(folded)` | Set folded lines state | `folded: Dict[int, int]` |
| `get_folded_lines()` | Get folded lines state | None |
| `set_on_line_click(callback)` | Set line click callback | `callback: Callable[[int], None]` |
| `set_on_fold_click(callback)` | Set fold click callback | `callback: Callable[[int], None]` |
| `sync_scroll()` | Synchronize scroll position | None |
| `redraw()` | Force full redraw | None |

## Usage Examples

```python
from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
from libs.gui_libs.style_system import StyleSystem

# Create editor
editor = CanvasCodeEditor(parent_frame)
editor.create_widget()
editor.pack(fill="both", expand=True)

# Set content
editor.set_content("print('Hello, World!')")

# Open and save files
editor.open_file("example.py")
editor.save_file()

# Apply styles
style_system = StyleSystem()
style_system.set_style("editor", "bg", "#1e1e1e")
editor.apply_style("default")

# Use callbacks
editor.set_on_file_changed(lambda path: print(f"Opened: {path}"))
editor.set_on_text_modified(lambda: print("Text modified"))
```

## Style Configuration

Style management through `StyleSystem` with JSON file loading and runtime modification.

```python
from libs.gui_libs.style_system import StyleSystem

ss = StyleSystem()

# Read style values
bg = ss.get_value("editor", "bg")
font = ss.get_value("editor", "font_family")

# Modify style
ss.set_style("editor", "bg", "#ffffff")
ss.set_component_style("editor", {"bg": "#fff", "fg": "#000"})

# Load from file
ss.load_from_file("my_style.json")
```

## Notes

- Editor uses lazy loading; call `load()` or `create_widget()` to initialize
- Syntax highlighting requires language config files in `assets/languages/`
- Fold functionality uses tk.Text elide tags
- Tkinter widgets should be created and manipulated on the main thread
- `is_dirty` property is read-only, reflecting current modification state

## Known Limitations

- Auto-completion is a placeholder requiring full implementation
- Drag operations handle text selection only, no file drag-and-drop
- Advanced features (multi-cursor, split view) not yet implemented
- Single-file editing only, no tab support