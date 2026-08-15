# Async Utils Module

## Description

A non-blocking I/O and async task execution module for Tkinter applications.
Provides thread-based background execution with UI-safe callbacks, ensuring
the main thread remains responsive during file operations and heavy computations.

### Key Features
- **AsyncTaskRunner**: Singleton thread pool manager with UI-safe callback scheduling
- **AsyncFileIO**: Non-blocking file read/write operations
- **async_run decorator**: Method-level async dispatch with string-based callback resolution
- **Thread safety**: All callbacks executed on Tkinter main thread via `root.after()`

## API Reference

### AsyncTaskRunner

Singleton class managing background thread execution.

| Method | Description | Parameters | Return Value |
|--------|-------------|-----------|-------------|
| `initialize(root)` | Initialize with Tkinter root widget | `root: tk.Tk` | `None` |
| `shutdown()` | Shutdown thread pool and release resources | None | `None` |
| `run(func, args, kwargs, on_success, on_error)` | Run function in background thread | `func: Callable`, `args: tuple`, `kwargs: dict`, `on_success: Callable`, `on_error: Callable` | `threading.Thread` |
| `run_in_executor(func, args, kwargs, on_success, on_error)` | Submit to thread pool | Same as `run()` | `None` |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `_root` | `Optional[tk.Tk]` | Tkinter root for `after()` scheduling |
| `_executor` | `Optional[ThreadPoolExecutor]` | Thread pool (max_workers=4) |
| `_instance` | `Optional[AsyncTaskRunner]` | Singleton instance |

### AsyncFileIO

Static methods for non-blocking file I/O.

| Method | Description | Parameters | Return Value |
|--------|-------------|-----------|-------------|
| `read_file(path, encoding, on_success, on_error)` | Read file asynchronously | `path: str`, `encoding: str`, `on_success: Callable[[str], None]`, `on_error: Callable[[Exception], None]` | `threading.Thread` |
| `write_file(path, content, encoding, on_success, on_error)` | Write file asynchronously | `path: str`, `content: str`, `encoding: str`, `on_success: Callable[[str], None]`, `on_error: Callable[[Exception], None]` | `threading.Thread` |

### async_run Decorator

Decorator for method-level async execution.

| Parameter | Type | Description |
|-----------|------|-------------|
| `on_success` | `Optional[Union[str, Callable]]` | Success callback (method name or callable) |
| `on_error` | `Optional[Union[str, Callable]]` | Error callback (method name or callable) |

## Usage Examples

### Basic Background Task

```python
from libs.gui.async_utils import AsyncTaskRunner

# Initialize in main window
AsyncTaskRunner.initialize(self.root)

# Run a function in background
def heavy_computation(data):
    # ... process data ...
    return result

AsyncTaskRunner.run(
    heavy_computation,
    args=(large_dataset,),
    on_success=lambda result: update_ui(result),
    on_error=lambda error: show_error(error),
)
```

### Async File I/O

```python
from libs.gui.async_utils import AsyncFileIO

# Read a file without blocking UI
AsyncFileIO.read_file(
    "/path/to/large_file.py",
    on_success=lambda content: editor.set_content(content),
    on_error=lambda error: messagebox.showerror("Error", str(error)),
)

# Write a file without blocking UI
AsyncFileIO.write_file(
    "/path/to/save.py",
    editor.get_content(),
    on_success=lambda path: status_bar.config(text=f"Saved: {path}"),
    on_error=lambda error: messagebox.showerror("Error", str(error)),
)
```

### Async Method Decorator

```python
from libs.gui.async_utils import async_run

class DataManager:
    @async_run(on_success='_on_load_done', on_error='_on_load_error')
    def load_data(self, file_path):
        with open(file_path, 'r') as f:
            return f.read()

    def _on_load_done(self, content):
        # Runs on main thread - safe to update UI
        self.text_widget.insert("1.0", content)

    def _on_load_error(self, error):
        messagebox.showerror("Error", str(error))
```

### Thread Pool Execution

```python
from libs.gui.async_utils import AsyncTaskRunner

# Submit multiple tasks to thread pool
for file_path in file_list:
    AsyncTaskRunner.run_in_executor(
        process_file,
        args=(file_path,),
        on_success=lambda result: results.append(result),
    )
```

## Notes

- Always call `AsyncTaskRunner.initialize(root)` before using any async operations
- All callbacks are scheduled via `root.after(0, callback)` ensuring thread safety
- Background threads are daemon threads, so they won't block application exit
- Call `AsyncTaskRunner.shutdown()` on app exit to release thread pool resources
- If `_root` is None (not initialized), callbacks execute directly (not thread-safe)

## Known Limitations

- Thread pool max_workers is fixed at 4
- No task cancellation API for individual running tasks
- No progress reporting mechanism for long-running tasks
- `async_run` decorator only supports instance methods (requires `self` parameter)
- Callbacks are one-shot; no streaming/iterator pattern available
