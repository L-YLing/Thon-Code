#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - async_utils",
    "Path": ".main.test.test_async_utils",
    "Entrance": "main.py"
}

import os
import sys
import time
import threading
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_async_utils")


class AsyncTaskRunnerTests(unittest.TestCase):
    """Test cases for AsyncTaskRunner and AsyncFileIO components."""

    def setUp(self):
        """Initialize async runner with a mock root for testing."""
        from libs.gui.async_utils import AsyncTaskRunner

        class MockRoot:
            """Mock Tkinter root widget that executes after() callbacks synchronously."""
            def after(self, ms, func):
                func()

        AsyncTaskRunner.initialize(MockRoot())

    def tearDown(self):
        """Shutdown async runner after each test."""
        from libs.gui.async_utils import AsyncTaskRunner
        AsyncTaskRunner.shutdown()

    def test_package_declaration(self):
        """Verify async_utils has proper package declaration."""
        import libs.gui.async_utils as async_utils
        self.assertTrue(hasattr(async_utils, 'package'))
        pkg = async_utils.package
        self.assertIn('ID', pkg)
        self.assertIn('Name', pkg)
        logger.info("package_declaration: async_utils package verified")
        print("[PASS] test_package_declaration: Package declaration valid")

    def test_async_task_runner_class_exists(self):
        """Verify AsyncTaskRunner class can be imported."""
        from libs.gui.async_utils import AsyncTaskRunner
        self.assertTrue(hasattr(AsyncTaskRunner, 'run'))
        self.assertTrue(hasattr(AsyncTaskRunner, 'initialize'))
        self.assertTrue(hasattr(AsyncTaskRunner, 'shutdown'))
        logger.info("async_task_runner_class_exists: verified")
        print("[PASS] test_async_task_runner_class_exists: Class methods verified")

    def test_run_basic_function(self):
        """Test running a basic function in background thread."""
        from libs.gui.async_utils import AsyncTaskRunner

        result_holder = []

        def task():
            return 42

        def on_success(result):
            result_holder.append(result)

        thread = AsyncTaskRunner.run(task, on_success=on_success)
        thread.join(timeout=2.0)

        self.assertEqual(result_holder, [42])
        logger.info("run_basic_function: result=%s", result_holder)
        print("[PASS] test_run_basic_function: Basic function executed correctly")

    def test_run_with_args(self):
        """Test running a function with positional arguments."""
        from libs.gui.async_utils import AsyncTaskRunner

        result_holder = []

        def add(a, b):
            return a + b

        def on_success(result):
            result_holder.append(result)

        thread = AsyncTaskRunner.run(add, args=(10, 20), on_success=on_success)
        thread.join(timeout=2.0)

        self.assertEqual(result_holder, [30])
        logger.info("run_with_args: result=%s", result_holder)
        print("[PASS] test_run_with_args: Arguments passed correctly")

    def test_run_with_kwargs(self):
        """Test running a function with keyword arguments."""
        from libs.gui.async_utils import AsyncTaskRunner

        result_holder = []

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        def on_success(result):
            result_holder.append(result)

        thread = AsyncTaskRunner.run(
            greet,
            args=("World",),
            kwargs={"greeting": "Hi"},
            on_success=on_success,
        )
        thread.join(timeout=2.0)

        self.assertEqual(result_holder, ["Hi, World!"])
        logger.info("run_with_kwargs: result=%s", result_holder)
        print("[PASS] test_run_with_kwargs: Keyword arguments passed correctly")

    def test_run_error_handling(self):
        """Test that errors are properly caught and passed to on_error callback."""
        from libs.gui.async_utils import AsyncTaskRunner

        error_holder = []

        def failing_task():
            raise ValueError("Test error")

        def on_error(error):
            error_holder.append(error)

        thread = AsyncTaskRunner.run(failing_task, on_error=on_error)
        thread.join(timeout=2.0)

        self.assertEqual(len(error_holder), 1)
        self.assertIsInstance(error_holder[0], ValueError)
        self.assertEqual(str(error_holder[0]), "Test error")
        logger.info("run_error_handling: error=%s", error_holder[0])
        print("[PASS] test_run_error_handling: Error handling works correctly")

    def test_run_no_callbacks(self):
        """Test running a function without any callbacks."""
        from libs.gui.async_utils import AsyncTaskRunner

        def task():
            return "no callbacks"

        thread = AsyncTaskRunner.run(task)
        thread.join(timeout=2.0)

        # Should complete without error
        self.assertFalse(thread.is_alive())
        logger.info("run_no_callbacks: completed without error")
        print("[PASS] test_run_no_callbacks: Runs without callbacks correctly")

    def test_run_returns_thread(self):
        """Test that run() returns a Thread object."""
        from libs.gui.async_utils import AsyncTaskRunner

        def task():
            time.sleep(0.01)

        thread = AsyncTaskRunner.run(task)
        self.assertIsInstance(thread, threading.Thread)
        self.assertTrue(thread.daemon)
        thread.join(timeout=2.0)
        logger.info("run_returns_thread: daemon=%s", thread.daemon)
        print("[PASS] test_run_returns_thread: Returns daemon Thread object")

    def test_singleton_pattern(self):
        """Verify AsyncTaskRunner uses singleton pattern."""
        from libs.gui.async_utils import AsyncTaskRunner

        instance1 = AsyncTaskRunner()
        instance2 = AsyncTaskRunner()
        self.assertIs(instance1, instance2)
        logger.info("singleton_pattern: verified")
        print("[PASS] test_singleton_pattern: Singleton pattern verified")

    def test_initialize_and_shutdown(self):
        """Test initialize and shutdown lifecycle."""
        from libs.gui.async_utils import AsyncTaskRunner

        class MockRoot:
            def after(self, ms, func):
                func()

        # After setUp already initialized, shutdown and re-init
        AsyncTaskRunner.shutdown()
        self.assertIsNone(AsyncTaskRunner._executor)
        self.assertIsNone(AsyncTaskRunner._root)

        AsyncTaskRunner.initialize(MockRoot())
        self.assertIsNotNone(AsyncTaskRunner._executor)
        self.assertIsNotNone(AsyncTaskRunner._root)

        logger.info("initialize_and_shutdown: verified")
        print("[PASS] test_initialize_and_shutdown: Lifecycle management works")

    def test_run_in_executor(self):
        """Test running a task via thread pool executor."""
        from libs.gui.async_utils import AsyncTaskRunner

        result_holder = []

        def task():
            return "executor result"

        def on_success(result):
            result_holder.append(result)

        AsyncTaskRunner.run_in_executor(task, on_success=on_success)

        # Wait for executor to complete (non-blocking)
        time.sleep(0.5)

        self.assertIn("executor result", result_holder)
        logger.info("run_in_executor: result=%s", result_holder)
        print("[PASS] test_run_in_executor: Executor submission works correctly")


class AsyncFileIOTests(unittest.TestCase):
    """Test cases for AsyncFileIO read/write operations."""

    def setUp(self):
        """Initialize async runner with a mock root for testing."""
        from libs.gui.async_utils import AsyncTaskRunner

        class MockRoot:
            """Mock Tkinter root that executes after() callbacks synchronously."""
            def after(self, ms, func):
                func()

        AsyncTaskRunner.initialize(MockRoot())

    def tearDown(self):
        """Shutdown async runner after each test."""
        from libs.gui.async_utils import AsyncTaskRunner
        AsyncTaskRunner.shutdown()

    def test_async_file_io_class_exists(self):
        """Verify AsyncFileIO class can be imported."""
        from libs.gui.async_utils import AsyncFileIO
        self.assertTrue(hasattr(AsyncFileIO, 'read_file'))
        self.assertTrue(hasattr(AsyncFileIO, 'write_file'))
        logger.info("async_file_io_class_exists: verified")
        print("[PASS] test_async_file_io_class_exists: Class methods verified")

    def test_read_file_success(self):
        """Test reading a file asynchronously."""
        from libs.gui.async_utils import AsyncFileIO

        # Create temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Hello, Async World!")
            temp_path = f.name

        try:
            result_holder = []
            thread = AsyncFileIO.read_file(
                temp_path,
                on_success=lambda content: result_holder.append(content),
            )
            thread.join(timeout=2.0)

            self.assertEqual(result_holder, ["Hello, Async World!"])
            logger.info("read_file_success: content=%s", result_holder[0])
            print("[PASS] test_read_file_success: File read correctly")
        finally:
            os.unlink(temp_path)

    def test_read_file_error(self):
        """Test reading a non-existent file triggers error callback."""
        from libs.gui.async_utils import AsyncFileIO

        error_holder = []
        thread = AsyncFileIO.read_file(
            "/nonexistent/path/file.txt",
            on_error=lambda e: error_holder.append(e),
        )
        thread.join(timeout=2.0)

        self.assertEqual(len(error_holder), 1)
        self.assertIsInstance(error_holder[0], (FileNotFoundError, OSError))
        logger.info("read_file_error: error=%s", error_holder[0])
        print("[PASS] test_read_file_error: Error callback triggered correctly")

    def test_write_file_success(self):
        """Test writing a file asynchronously."""
        from libs.gui.async_utils import AsyncFileIO

        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), "thon_async_test_write.txt")

        try:
            result_holder = []
            thread = AsyncFileIO.write_file(
                temp_path,
                "Async write content",
                on_success=lambda path: result_holder.append(path),
            )
            thread.join(timeout=2.0)

            self.assertEqual(result_holder, [temp_path])
            # Verify file content
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content, "Async write content")
            logger.info("write_file_success: path=%s", result_holder[0])
            print("[PASS] test_write_file_success: File written correctly")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_write_file_error(self):
        """Test writing to an invalid path triggers error callback."""
        from libs.gui.async_utils import AsyncFileIO

        error_holder = []
        thread = AsyncFileIO.write_file(
            "/nonexistent/dir/file.txt",
            "content",
            on_error=lambda e: error_holder.append(e),
        )
        thread.join(timeout=2.0)

        self.assertEqual(len(error_holder), 1)
        self.assertIsInstance(error_holder[0], (FileNotFoundError, OSError))
        logger.info("write_file_error: error=%s", error_holder[0])
        print("[PASS] test_write_file_error: Error callback triggered correctly")

    def test_read_file_with_encoding(self):
        """Test reading a file with custom encoding."""
        from libs.gui.async_utils import AsyncFileIO

        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write("测试中文".encode('gbk'))
            temp_path = f.name

        try:
            result_holder = []
            thread = AsyncFileIO.read_file(
                temp_path,
                encoding='gbk',
                on_success=lambda content: result_holder.append(content),
            )
            thread.join(timeout=2.0)

            self.assertEqual(result_holder, ["测试中文"])
            logger.info("read_file_with_encoding: content=%s", result_holder[0])
            print("[PASS] test_read_file_with_encoding: Custom encoding works")
        finally:
            os.unlink(temp_path)

    def test_write_file_returns_thread(self):
        """Test that write_file returns a Thread object."""
        from libs.gui.async_utils import AsyncFileIO

        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), "thon_async_thread_test.txt")

        try:
            thread = AsyncFileIO.write_file(temp_path, "test")
            self.assertIsInstance(thread, threading.Thread)
            thread.join(timeout=2.0)
            print("[PASS] test_write_file_returns_thread: Returns Thread object")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class AsyncRunDecoratorTests(unittest.TestCase):
    """Test cases for the async_run decorator."""

    def setUp(self):
        """Initialize async runner with a mock root for testing."""
        from libs.gui.async_utils import AsyncTaskRunner

        class MockRoot:
            def after(self, ms, func):
                func()

        AsyncTaskRunner.initialize(MockRoot())

    def tearDown(self):
        """Shutdown async runner after each test."""
        from libs.gui.async_utils import AsyncTaskRunner
        AsyncTaskRunner.shutdown()

    def test_async_run_decorator_exists(self):
        """Verify async_run decorator can be imported."""
        from libs.gui.async_utils import async_run
        self.assertTrue(callable(async_run))
        logger.info("async_run_decorator_exists: verified")
        print("[PASS] test_async_run_decorator_exists: Decorator is callable")

    def test_async_run_with_string_callbacks(self):
        """Test async_run decorator with string method name callbacks."""
        from libs.gui.async_utils import async_run

        class TestClass:
            def __init__(self):
                self.results = []
                self.errors = []

            @async_run(on_success='_on_success', on_error='_on_error')
            def compute(self, value):
                return value * 2

            def _on_success(self, result):
                self.results.append(result)

            def _on_error(self, error):
                self.errors.append(error)

        obj = TestClass()
        thread = obj.compute(21)
        thread.join(timeout=2.0)

        self.assertEqual(obj.results, [42])
        self.assertEqual(obj.errors, [])
        logger.info("async_run_with_string_callbacks: results=%s", obj.results)
        print("[PASS] test_async_run_with_string_callbacks: String callbacks work")

    def test_async_run_error_handling(self):
        """Test async_run decorator handles errors correctly."""
        from libs.gui.async_utils import async_run

        class TestClass:
            def __init__(self):
                self.errors = []

            @async_run(on_error='_on_error')
            def failing_method(self):
                raise RuntimeError("Decorator error")

            def _on_error(self, error):
                self.errors.append(error)

        obj = TestClass()
        thread = obj.failing_method()
        thread.join(timeout=2.0)

        self.assertEqual(len(obj.errors), 1)
        self.assertIsInstance(obj.errors[0], RuntimeError)
        logger.info("async_run_error_handling: error=%s", obj.errors[0])
        print("[PASS] test_async_run_error_handling: Error handling works correctly")


if __name__ == "__main__":
    unittest.main(verbosity=2)
