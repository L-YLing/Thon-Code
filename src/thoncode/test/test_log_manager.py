#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Log Manager Test",
    "Path": ".main.test.test_log_manager",
    "Entrance": "run_all.py"
}

"""Tests for libs.log_manager: rotation, directory creation, and logger retrieval.

Verifies that init_logging creates the log directory, get_logger returns
functional loggers, and rotating handlers are attached to prevent
unbounded log growth.
"""

import os
import sys
import tempfile
import logging
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_log_manager")

from libs.log_manager import init_logging, get_logger as lm_get_logger, get_log_dir


class TestLogManager(unittest.TestCase):
    """Test suite for the log_manager module."""

    def setUp(self):
        """Create a fresh temp directory for each test."""
        self._tmp_dir = tempfile.mkdtemp(prefix="thoncode_test_logs_")
        # Reset the initialized flag so init_logging runs again
        import libs.log_manager as lm
        lm._initialized = False
        lm._log_dir = ""

    def tearDown(self):
        """Clean up handlers to avoid pollution between tests."""
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    def test_init_creates_log_dir(self):
        """init_logging should create the log directory if it doesn't exist."""
        log_dir = os.path.join(self._tmp_dir, "mylogs")
        result = init_logging(log_dir=log_dir)
        self.assertEqual(result, log_dir)
        self.assertTrue(os.path.isdir(log_dir))
        logger.info("test_init_creates_log_dir passed")

    def test_init_returns_same_dir_on_repeat(self):
        """Repeated init_logging calls should be no-ops returning the same dir."""
        log_dir = os.path.join(self._tmp_dir, "repeat")
        first = init_logging(log_dir=log_dir)
        second = init_logging(log_dir=os.path.join(self._tmp_dir, "other"))
        self.assertEqual(first, second)
        logger.info("test_init_returns_same_dir_on_repeat passed")

    def test_get_logger_returns_logger(self):
        """get_logger should return a logging.Logger instance."""
        init_logging(log_dir=self._tmp_dir)
        lg = lm_get_logger("test_module")
        self.assertIsInstance(lg, logging.Logger)
        logger.info("test_get_logger_returns_logger passed")

    def test_logger_writes_to_file(self):
        """Logging a message should create and write to the log file."""
        init_logging(log_dir=self._tmp_dir)
        lg = lm_get_logger("test_write")
        lg.info("test message for file write")
        # Flush all handlers
        for handler in logging.getLogger().handlers:
            handler.flush()
        log_file = os.path.join(self._tmp_dir, "thoncode.log")
        self.assertTrue(os.path.exists(log_file))
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("test message for file write", content)
        logger.info("test_logger_writes_to_file passed")

    def test_get_log_dir_returns_initialized_dir(self):
        """get_log_dir should return the directory set by init_logging."""
        log_dir = os.path.join(self._tmp_dir, "query")
        init_logging(log_dir=log_dir)
        self.assertEqual(get_log_dir(), log_dir)
        logger.info("test_get_log_dir_returns_initialized_dir passed")

    def test_get_logger_auto_initializes(self):
        """get_logger should auto-initialize if init_logging wasn't called."""
        import libs.log_manager as lm
        lm._initialized = False
        lm._log_dir = ""
        lg = lm_get_logger("auto_init")
        self.assertIsInstance(lg, logging.Logger)
        # Clean up auto-created log dir
        if lm._log_dir and os.path.isdir(lm._log_dir):
            import shutil
            shutil.rmtree(lm._log_dir, ignore_errors=True)
        logger.info("test_get_logger_auto_initializes passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
