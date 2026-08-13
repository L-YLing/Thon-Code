#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - git_functions",
    "Path": ".main.test.test_git_functions",
    "Entrance": "main.py"
}

import os
import shutil
import subprocess
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_git_functions")

# Detect git availability once; tests requiring a real repo are skipped otherwise.
try:
    _GIT_OK = subprocess.run(
        ['git', '--version'], capture_output=True, text=True, timeout=5
    ).returncode == 0
except Exception:
    _GIT_OK = False


def make_git(project_root):
    """Create a GitFunctions instance bypassing __init__ side effects."""
    from libs.git_functions import GitFunctions
    g = GitFunctions.__new__(GitFunctions)
    g.project_root = project_root
    g.status_callback = None
    g.parent = None
    return g


@unittest.skipUnless(_GIT_OK, "git executable not available")
class GitFunctionsRepoTests(unittest.TestCase):
    """Tests exercising GitFunctions against a real temporary git repository."""

    def setUp(self):
        """Create a fresh git repo in a temp directory."""
        self.tmp = tempfile.mkdtemp()
        # Initialize repo and set a committed identity so commits succeed.
        subprocess.run(['git', 'init'], cwd=self.tmp, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 't@t.com'], cwd=self.tmp, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=self.tmp, capture_output=True)
        self.git = make_git(self.tmp)

    def tearDown(self):
        """Remove the temp repository."""
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, content="x"):
        """Write a file inside the repo and return its path."""
        path = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(name) else None
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_is_repo_true_after_init(self):
        """Verify is_repo returns True in an initialized repository."""
        self.assertTrue(self.git.is_repo())
        logger.info("is_repo_true: repo detected")
        print("[PASS] test_is_repo_true_after_init: repo detected")

    def test_add_and_commit(self):
        """Verify add_file + commit with an ASCII message succeeds."""
        self._write("a.py", "print(1)")
        self.assertTrue(self.git.add_file("a.py"))
        self.assertTrue(self.git.commit("initial commit"))
        logger.info("add_and_commit: file added and committed")
        print("[PASS] test_add_and_commit: file added and committed")

    def test_commit_chinese_message_no_mangle(self):
        """Verify a Chinese commit message is stored verbatim via -F - stdin."""
        self._write("b.py", "y = 2")
        self.git.add_file("b.py")
        msg = "初始化提交: 添加 b 模块"
        self.assertTrue(self.git.commit(msg))
        # Read back the latest commit subject.
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%s'],
            cwd=self.tmp, capture_output=True, text=True, encoding='utf-8'
        )
        self.assertEqual(result.stdout.strip(), msg)
        logger.info("commit_chinese_message: message stored verbatim")
        print("[PASS] test_commit_chinese_message_no_mangle: message stored verbatim")

    def test_status_detailed_untracked(self):
        """Verify untracked files appear in the untracked list."""
        self._write("new.py", "z = 3")
        status = self.git.get_status_detailed()
        self.assertIn("new.py", status['untracked'])
        logger.info("status_untracked: untracked file detected")
        print("[PASS] test_status_detailed_untracked: untracked file detected")

    def test_status_detailed_rename(self):
        """Verify renamed entries resolve to the new path, not 'old -> new'."""
        self._write("old.py", "v = 1")
        self.git.add_file("old.py")
        self.git.commit("base")
        # Rename via git mv so porcelain reports an 'R' status.
        subprocess.run(['git', 'mv', 'old.py', 'new.py'], cwd=self.tmp, capture_output=True)
        status = self.git.get_status_detailed()
        # The new path should be present; the raw 'old.py -> new.py' must not.
        self.assertTrue(any("new.py" in p for p in status['staged']))
        self.assertFalse(any("->" in p for p in status['staged']))
        logger.info("status_rename: rename resolved to new path")
        print("[PASS] test_status_detailed_rename: rename resolved to new path")

    def test_status_uses_quotepath_false(self):
        """Verify Chinese filenames are returned literally (quotepath off)."""
        self._write("中文.py", "a = 1")
        status = self.git.get_status_detailed()
        self.assertTrue(any("中文.py" in p for p in status['untracked']))
        logger.info("status_quotepath: chinese path returned literally")
        print("[PASS] test_status_uses_quotepath_false: chinese path returned literally")

    def test_discard_all_keeps_untracked_by_default(self):
        """Verify discard_all preserves untracked files by default."""
        self._write("tracked.py", "1")
        self.git.add_file("tracked.py")
        self.git.commit("base")
        self._write("tracked.py", "2")  # modify tracked
        self._write("untracked.py", "3")
        self.assertTrue(self.git.discard_all())  # keep_untracked=True default
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "untracked.py")))
        logger.info("discard_all_keep_untracked: untracked preserved by default")
        print("[PASS] test_discard_all_keeps_untracked_by_default: untracked preserved")

    def test_discard_all_removes_untracked_when_requested(self):
        """Verify discard_all(keep_untracked=False) cleans untracked files."""
        self._write("tracked.py", "1")
        self.git.add_file("tracked.py")
        self.git.commit("base")
        self._write("untracked.py", "3")
        self.assertTrue(self.git.discard_all(keep_untracked=False))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "untracked.py")))
        logger.info("discard_all_remove_untracked: untracked removed when requested")
        print("[PASS] test_discard_all_removes_untracked_when_requested: untracked removed")


class GitFunctionsUnitTests(unittest.TestCase):
    """Tests that do not require a real repository or git installation."""

    def test_run_git_command_git_not_installed_sentinel(self):
        """Verify FileNotFoundError yields the GIT_NOT_INSTALLED sentinel."""
        git = make_git(os.getcwd())

        original_run = subprocess.run

        def fake_run(*args, **kwargs):
            raise FileNotFoundError("git not found")

        subprocess.run = fake_run
        try:
            success, output = git._run_git_command(['status'])
        finally:
            subprocess.run = original_run
        self.assertFalse(success)
        self.assertEqual(output, "GIT_NOT_INSTALLED")
        logger.info("git_not_installed_sentinel: sentinel returned")
        print("[PASS] test_run_git_command_git_not_installed_sentinel: sentinel returned")

    def test_run_git_command_timeout(self):
        """Verify TimeoutExpired is reported as a failure with a message."""
        git = make_git(os.getcwd())
        original_run = subprocess.run

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get('timeout', 30))

        subprocess.run = fake_run
        try:
            success, output = git._run_git_command(['status'])
        finally:
            subprocess.run = original_run
        self.assertFalse(success)
        self.assertIn("timed out", output.lower())
        logger.info("git_timeout: timeout reported")
        print("[PASS] test_run_git_command_timeout: timeout reported")

    def test_push_passes_branch_when_provided(self):
        """Verify push includes the branch argument only when given."""
        git = make_git(os.getcwd())
        captured = {}

        original = git._run_git_command

        def fake_run(args, **kwargs):
            captured['args'] = args
            captured['kwargs'] = kwargs
            return True, ""

        git._run_git_command = fake_run
        try:
            git.push(branch="main")
            self.assertEqual(captured['args'], ['push', 'origin', 'main'])
            self.assertEqual(captured['kwargs'].get('timeout'), 60)
            # Without a branch, no branch arg is appended.
            git.push()
            self.assertEqual(captured['args'], ['push', 'origin'])
        finally:
            git._run_git_command = original
        logger.info("push_branch_arg: branch appended only when provided")
        print("[PASS] test_push_passes_branch_when_provided: branch arg correct")

    def test_pull_passes_branch_when_provided(self):
        """Verify pull includes the branch argument only when given."""
        git = make_git(os.getcwd())
        captured = {}

        original = git._run_git_command

        def fake_run(args, **kwargs):
            captured['args'] = args
            return True, ""

        git._run_git_command = fake_run
        try:
            git.pull(branch="dev")
            self.assertEqual(captured['args'], ['pull', 'origin', 'dev'])
            git.pull()
            self.assertEqual(captured['args'], ['pull', 'origin'])
        finally:
            git._run_git_command = original
        logger.info("pull_branch_arg: branch appended only when provided")
        print("[PASS] test_pull_passes_branch_when_provided: branch arg correct")

    def test_commit_uses_stdin_flag(self):
        """Verify commit pipes the message via -F - rather than -m."""
        git = make_git(os.getcwd())
        captured = {}

        original = git._run_git_command

        def fake_run(args, **kwargs):
            captured['args'] = args
            captured['input'] = kwargs.get('input')
            return True, ""

        git._run_git_command = fake_run
        try:
            git.commit("hello 世界")
            self.assertEqual(captured['args'], ['commit', '-F', '-'])
            self.assertEqual(captured['input'], "hello 世界")
        finally:
            git._run_git_command = original
        logger.info("commit_stdin_flag: message piped via -F -")
        print("[PASS] test_commit_uses_stdin_flag: message piped via -F -")


if __name__ == "__main__":
    unittest.main(verbosity=2)
