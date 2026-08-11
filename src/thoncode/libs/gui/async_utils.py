#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Async Utils",
    "Path": ".main.libs.gui.async_utils",
    "Entrance": "main.py"
}

"""
Async utility module for non-blocking I/O operations in Tkinter.

Provides thread-based async execution with safe UI callbacks.
All background tasks use daemon threads to avoid blocking app exit.
UI updates are scheduled via root.after() to ensure thread safety.
"""

import threading
import functools
from typing import Callable, Any, Optional, TypeVar
from concurrent.futures import ThreadPoolExecutor

T = TypeVar("T")


class AsyncTaskRunner:
    """Manages background thread execution with safe UI callbacks.

    Uses a thread pool for efficient resource management.
    All callbacks are scheduled on the Tkinter main thread via after().
    """

    _instance: Optional["AsyncTaskRunner"] = None
    _executor: Optional[ThreadPoolExecutor] = None
    _root: Optional[Any] = None

    def __new__(cls) -> "AsyncTaskRunner":
        """Enforce singleton pattern for shared thread pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, root: Any) -> None:
        """Initialize the runner with the Tkinter root widget.

        Args:
            root: The Tkinter root widget (tk.Tk instance)
        """
        cls._root = root
        if cls._executor is None:
            # Use max_workers=4 for balanced I/O concurrency
            cls._executor = ThreadPoolExecutor(
                max_workers=4,
                thread_name_prefix="thon-async"
            )

    @classmethod
    def shutdown(cls) -> None:
        """Shutdown the thread pool and release resources."""
        if cls._executor is not None:
            cls._executor.shutdown(wait=False, cancel_futures=True)
            cls._executor = None
        cls._root = None

    @classmethod
    def run(
        cls,
        func: Callable[..., T],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        on_success: Optional[Callable[[T], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> threading.Thread:
        """Run a function in a background thread with UI-safe callbacks.

        Args:
            func: The function to execute in background
            args: Positional arguments for func
            kwargs: Keyword arguments for func
            on_success: Callback receiving result on success (runs on main thread)
            on_error: Callback receiving exception on error (runs on main thread)

        Returns:
            The Thread object running the task
        """
        if kwargs is None:
            kwargs = {}

        def _task():
            """Background task wrapper that schedules callbacks on main thread."""
            try:
                result = func(*args, **kwargs)
                if on_success:
                    cls._schedule_callback(on_success, result)
            except Exception as e:
                if on_error:
                    cls._schedule_callback(on_error, e)

        # Use daemon thread so it doesn't block app exit
        thread = threading.Thread(target=_task, daemon=True)
        thread.start()
        return thread

    @classmethod
    def _schedule_callback(cls, callback: Callable, data: Any) -> None:
        """Schedule a callback on the Tkinter main thread.

        Args:
            callback: The callback function to execute
            data: Data to pass to the callback
        """
        if cls._root is not None:
            try:
                cls._root.after(0, lambda: callback(data))
            except Exception:
                # Root may be destroyed during shutdown
                pass
        else:
            # No root available, call directly (may not be thread-safe)
            callback(data)

    @classmethod
    def run_in_executor(
        cls,
        func: Callable[..., T],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        on_success: Optional[Callable[[T], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Submit a task to the thread pool executor.

        Args:
            func: The function to execute in thread pool
            args: Positional arguments for func
            kwargs: Keyword arguments for func
            on_success: Callback receiving result on success (runs on main thread)
            on_error: Callback receiving exception on error (runs on main thread)
        """
        if cls._executor is None:
            # Fallback to direct thread if executor not initialized
            cls.run(func, args, kwargs, on_success, on_error)
            return

        if kwargs is None:
            kwargs = {}

        def _task():
            """Thread pool task wrapper with main-thread callbacks."""
            try:
                result = func(*args, **kwargs)
                if on_success:
                    cls._schedule_callback(on_success, result)
            except Exception as e:
                if on_error:
                    cls._schedule_callback(on_error, e)

        cls._executor.submit(_task)


def async_run(
    on_success: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
) -> Callable:
    """Decorator to run a method in a background thread.

    Args:
        on_success: Method name (string) or callable for success callback
        on_error: Method name (string) or callable for error callback

    Returns:
        Decorated function that runs in background thread
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            """Wrapper that dispatches the function to a background thread."""
            # Resolve string callback names to bound methods
            success_cb = None
            error_cb = None
            if isinstance(on_success, str):
                success_cb = getattr(self, on_success, None)
            elif callable(on_success):
                success_cb = on_success
            if isinstance(on_error, str):
                error_cb = getattr(self, on_error, None)
            elif callable(on_error):
                error_cb = on_error

            return AsyncTaskRunner.run(
                func,
                args=(self, *args),
                kwargs=kwargs,
                on_success=success_cb,
                on_error=error_cb,
            )

        return wrapper

    return decorator


class AsyncFileIO:
    """Async file I/O operations that don't block the UI thread.

    Provides read and write operations with callbacks for
    completion and error handling. All file operations run
    in background threads with results delivered on the main thread.
    """

    @staticmethod
    def read_file(
        file_path: str,
        encoding: str = "utf-8",
        on_success: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> threading.Thread:
        """Read a file asynchronously.

        Args:
            file_path: Path to the file to read
            encoding: File encoding (default: utf-8)
            on_success: Callback receiving file content as string
            on_error: Callback receiving exception on error

        Returns:
            Thread running the read operation
        """

        def _read():
            """Background file read operation."""
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()

        return AsyncTaskRunner.run(
            _read,
            on_success=on_success,
            on_error=on_error,
        )

    @staticmethod
    def write_file(
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        on_success: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> threading.Thread:
        """Write content to a file asynchronously.

        Args:
            file_path: Path to the file to write
            content: String content to write
            encoding: File encoding (default: utf-8)
            on_success: Callback receiving the file path on success
            on_error: Callback receiving exception on error

        Returns:
            Thread running the write operation
        """

        def _write():
            """Background file write operation."""
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)
            return file_path

        return AsyncTaskRunner.run(
            _write,
            on_success=on_success,
            on_error=on_error,
        )
