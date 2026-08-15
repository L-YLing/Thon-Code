# 异步工具模块

## 功能描述

用于 Tkinter 应用的非阻塞 I/O 和异步任务执行模块。
提供基于线程的后台执行机制和 UI 安全回调，确保主线程在文件操作
和大量计算期间保持响应。

### 核心功能
- **AsyncTaskRunner**: 单例线程池管理器，支持 UI 安全的回调调度
- **AsyncFileIO**: 非阻塞文件读写操作
- **async_run 装饰器**: 方法级异步分发，支持字符串回调名解析
- **线程安全**: 所有回调通过 `root.after()` 在 Tkinter 主线程执行

## API 接口说明

### AsyncTaskRunner

管理后台线程执行的单例类。

| 方法 | 描述 | 参数 | 返回值 |
|------|------|------|--------|
| `initialize(root)` | 使用 Tkinter root 控件初始化 | `root: tk.Tk` | `None` |
| `shutdown()` | 关闭线程池并释放资源 | 无 | `None` |
| `run(func, args, kwargs, on_success, on_error)` | 在后台线程中运行函数 | `func: Callable`, `args: tuple`, `kwargs: dict`, `on_success: Callable`, `on_error: Callable` | `threading.Thread` |
| `run_in_executor(func, args, kwargs, on_success, on_error)` | 提交到线程池执行 | 同 `run()` | `None` |

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `_root` | `Optional[tk.Tk]` | 用于 `after()` 调度的 Tkinter root |
| `_executor` | `Optional[ThreadPoolExecutor]` | 线程池（最大工作线程数=4） |
| `_instance` | `Optional[AsyncTaskRunner]` | 单例实例 |

### AsyncFileIO

非阻塞文件 I/O 的静态方法集合。

| 方法 | 描述 | 参数 | 返回值 |
|------|------|------|--------|
| `read_file(path, encoding, on_success, on_error)` | 异步读取文件 | `path: str`, `encoding: str`, `on_success: Callable[[str], None]`, `on_error: Callable[[Exception], None]` | `threading.Thread` |
| `write_file(path, content, encoding, on_success, on_error)` | 异步写入文件 | `path: str`, `content: str`, `encoding: str`, `on_success: Callable[[str], None]`, `on_error: Callable[[Exception], None]` | `threading.Thread` |

### async_run 装饰器

用于方法级异步执行的装饰器。

| 参数 | 类型 | 描述 |
|------|------|------|
| `on_success` | `Optional[Union[str, Callable]]` | 成功回调（方法名或可调用对象） |
| `on_error` | `Optional[Union[str, Callable]]` | 错误回调（方法名或可调用对象） |

## 使用示例

### 基本后台任务

```python
from libs.gui.async_utils import AsyncTaskRunner

# 在主窗口中初始化
AsyncTaskRunner.initialize(self.root)

# 在后台运行函数
def heavy_computation(data):
    # ... 处理数据 ...
    return result

AsyncTaskRunner.run(
    heavy_computation,
    args=(large_dataset,),
    on_success=lambda result: update_ui(result),
    on_error=lambda error: show_error(error),
)
```

### 异步文件 I/O

```python
from libs.gui.async_utils import AsyncFileIO

# 不阻塞 UI 读取文件
AsyncFileIO.read_file(
    "/path/to/large_file.py",
    on_success=lambda content: editor.set_content(content),
    on_error=lambda error: messagebox.showerror("错误", str(error)),
)

# 不阻塞 UI 写入文件
AsyncFileIO.write_file(
    "/path/to/save.py",
    editor.get_content(),
    on_success=lambda path: status_bar.config(text=f"已保存: {path}"),
    on_error=lambda error: messagebox.showerror("错误", str(error)),
)
```

### 异步方法装饰器

```python
from libs.gui.async_utils import async_run

class DataManager:
    @async_run(on_success='_on_load_done', on_error='_on_load_error')
    def load_data(self, file_path):
        with open(file_path, 'r') as f:
            return f.read()

    def _on_load_done(self, content):
        # 在主线程执行 - 可安全更新 UI
        self.text_widget.insert("1.0", content)

    def _on_load_error(self, error):
        messagebox.showerror("错误", str(error))
```

### 线程池执行

```python
from libs.gui.async_utils import AsyncTaskRunner

# 提交多个任务到线程池
for file_path in file_list:
    AsyncTaskRunner.run_in_executor(
        process_file,
        args=(file_path,),
        on_success=lambda result: results.append(result),
    )
```

## 注意事项

- 使用任何异步操作前必须调用 `AsyncTaskRunner.initialize(root)`
- 所有回调通过 `root.after(0, callback)` 调度，确保线程安全
- 后台线程为守护线程，不会阻止应用退出
- 应用退出时调用 `AsyncTaskRunner.shutdown()` 释放线程池资源
- 若 `_root` 为 None（未初始化），回调将直接执行（非线程安全）

## 已知限制

- 线程池最大工作线程数固定为 4
- 无单个运行中任务的取消 API
- 无长时间运行任务的进度报告机制
- `async_run` 装饰器仅支持实例方法（需要 `self` 参数）
- 回调为一次性触发，不支持流式/迭代器模式
