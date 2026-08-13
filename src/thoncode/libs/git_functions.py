# libs/git_functions.py - Complete file with parent attribute

import os
import subprocess
from typing import Optional, List, Dict, Any
from tkinter import messagebox
from libs.gui.lazy_loader import LazyLoader

class GitFunctions:
    """
    Git operations handler for project version control.
    Provides core git functionality without UI dependencies.
    """

    def __init__(self, project_root: Optional[str] = None, status_callback=None):
        """
        Initialize GitFunctions with project root.

        Args:
            project_root: Root directory of the git repository
            status_callback: Optional callback for status messages
        """
        self.project_root = project_root or os.getcwd()
        self.status_callback = status_callback
        self.parent = None  # Will be set by window if needed

    def set_parent(self, parent):
        """Set parent window for dialogs"""
        self.parent = parent

    def _run_git_command(self, args: List[str], check_output: bool = False,
                         timeout: int = 30, input: Optional[str] = None) -> tuple:
        """
        Run a git command and return result.

        Args:
            args: Git command arguments
            check_output: If True, return output as string
            timeout: Maximum seconds to wait for the command to complete
            input: Optional string piped to the command's stdin

        Returns:
            tuple: (success: bool, output: str). On a missing git binary the
            output is the sentinel string "GIT_NOT_INSTALLED".
        """
        try:
            kwargs = {
                'cwd': self.project_root,
                'capture_output': True,
                'text': True,
                'encoding': 'utf-8',
                'errors': 'replace',
                'timeout': timeout,
                'env': {
                    **os.environ,
                    # Prevent git from blocking on interactive credential prompts
                    'GIT_TERMINAL_PROMPT': '0',
                    # Force git to communicate in utf-8 (avoid GBK mangling)
                    'GIT_ENCODING': 'utf-8',
                },
            }
            if input is not None:
                kwargs['input'] = input
            result = subprocess.run(['git'] + args, **kwargs)
            success = result.returncode == 0
            output = result.stdout.strip() if success else result.stderr.strip()

            if self.status_callback:
                if success:
                    self.status_callback(f"Git: {output[:100]}")
                else:
                    self.status_callback(f"Git error: {output[:100]}")

            return success, output
        except FileNotFoundError:
            # Git executable is not installed or not available on PATH
            if self.status_callback:
                self.status_callback("Git is not installed or not in PATH")
            return False, "GIT_NOT_INSTALLED"
        except subprocess.TimeoutExpired:
            msg = f"Git command timed out after {timeout}s: {' '.join(args)}"
            if self.status_callback:
                self.status_callback(msg)
            return False, msg
        except Exception as e:
            # Preserve the exception type so callers can distinguish failures
            msg = f"{type(e).__name__}: {e}"
            if self.status_callback:
                self.status_callback(f"Git exception: {msg}")
            return False, msg

    def is_git_installed(self) -> bool:
        """Return True if the git executable is available on the system."""
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
                env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_repo(self) -> bool:
        """Check if current directory is a git repository"""
        success, _ = self._run_git_command(['rev-parse', '--is-inside-work-tree'])
        return success

    def init(self) -> bool:
        """Initialize a new git repository"""
        success, output = self._run_git_command(['init'])
        return success

    def get_branches(self) -> List[str]:
        """Get list of all branches"""
        success, output = self._run_git_command(['branch', '--format=%(refname:short)'])
        if success and output:
            return [b.strip() for b in output.splitlines() if b.strip()]
        return []

    def get_current_branch(self) -> Optional[str]:
        """Get current branch name"""
        success, output = self._run_git_command(['branch', '--show-current'])
        return output if success else None

    def get_status(self) -> str:
        """Get git status output (quotepath disabled for unicode paths)."""
        success, output = self._run_git_command(
            ['-c', 'core.quotepath=false', 'status', '--short']
        )
        return output if success else ""

    def get_status_detailed(self) -> Dict[str, List[str]]:
        """Get detailed status with staged, unstaged, and untracked files"""
        status = {
            'staged': [],
            'unstaged': [],
            'untracked': []
        }

        # Disable quote-path so Chinese/unicode paths are returned literally
        success, output = self._run_git_command(
            ['-c', 'core.quotepath=false', 'status', '--porcelain']
        )
        if not success or not output:
            return status

        for line in output.splitlines():
            if not line:
                continue
            code = line[:2]
            file_path = line[3:].strip()

            # Rename/copy entries use the "old -> new" format; keep the new path
            if code[0] in ('R', 'C') or code[1] in ('R', 'C'):
                if ' -> ' in file_path:
                    file_path = file_path.split(' -> ', 1)[1].strip()

            if code[0] in ('M', 'A', 'D', 'R', 'C'):
                status['staged'].append(file_path)

            if code[1] in ('M', 'D', 'R', 'C'):
                status['unstaged'].append(file_path)

            if code == '??':
                status['untracked'].append(file_path)

        return status

    def add_all(self) -> bool:
        """Add all files to staging"""
        success, _ = self._run_git_command(['add', '.'])
        return success

    def add_file(self, file_path: str) -> bool:
        """Add specific file to staging"""
        success, _ = self._run_git_command(['add', file_path])
        return success

    def commit(self, message: str) -> bool:
        """
        Commit changes with message.

        The message is piped through stdin via ``-F -`` so non-ASCII
        characters are not mangled by the system code page when passed as a
        command-line argument.
        """
        success, _ = self._run_git_command(['commit', '-F', '-'], input=message)
        return success

    def push(self, remote: str = 'origin', branch: Optional[str] = None) -> bool:
        """
        Push to remote.

        When ``branch`` is None no branch is specified, letting git use the
        default upstream behaviour.
        """
        args = ['push', remote]
        if branch:
            args.append(branch)
        success, _ = self._run_git_command(args, timeout=60)
        return success

    def pull(self, remote: str = 'origin', branch: Optional[str] = None) -> bool:
        """
        Pull from remote.

        When ``branch`` is None no branch is specified, letting git use the
        default upstream behaviour.
        """
        args = ['pull', remote]
        if branch:
            args.append(branch)
        success, _ = self._run_git_command(args, timeout=60)
        return success

    def sync(self, remote: str = 'origin', branch: Optional[str] = None) -> tuple:
        """Synchronize with remote: pull then push (VSCode-style sync).

        Pulls first to incorporate remote changes, then pushes local commits.
        If pull fails (e.g. conflicts), push is skipped and the failure is
        reported so the user can resolve manually.

        Args:
            remote: Remote name (default 'origin')
            branch: Optional branch; None uses default upstream

        Returns:
            tuple: (pull_success: bool, push_success: bool, message: str)
        """
        pull_ok = self.pull(remote, branch)
        if not pull_ok:
            return False, False, "Pull failed; push skipped to avoid conflicts"
        push_ok = self.push(remote, branch)
        if push_ok:
            return True, True, "Sync complete (pull + push succeeded)"
        return True, False, "Pull succeeded but push failed"

    def create_branch(self, branch_name: str) -> bool:
        """Create a new branch"""
        success, _ = self._run_git_command(['branch', branch_name])
        return success

    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete a branch"""
        args = ['branch', '-d' if not force else '-D', branch_name]
        success, _ = self._run_git_command(args)
        return success

    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a branch"""
        success, _ = self._run_git_command(['switch', branch_name])
        return success

    def checkout_branch(self, branch_name: str) -> bool:
        """Checkout a branch (legacy)"""
        success, _ = self._run_git_command(['checkout', branch_name])
        return success

    def checkout_file(self, file_path: str) -> bool:
        """Checkout/discard changes to a file"""
        success, _ = self._run_git_command(['checkout', '--', file_path])
        return success

    def discard_file(self, file_path: str) -> bool:
        """Discard changes to a file (alias for checkout_file)"""
        return self.checkout_file(file_path)

    def discard_all(self, keep_untracked: bool = True) -> bool:
        """
        Discard all tracked changes.

        Args:
            keep_untracked: When True (default) untracked files are preserved
                for safety and backward compatibility. When False,
                ``git clean -fd`` is also executed to remove untracked files
                and directories.
        """
        if not self.checkout_file('.'):
            return False
        if not keep_untracked:
            success, _ = self._run_git_command(['clean', '-fd'])
            return success
        return True

    def get_log(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get commit log"""
        args = [
            'log',
            f'--max-count={limit}',
            '--pretty=format:%H|%an|%ae|%ad|%s',
            '--date=short'
        ]
        success, output = self._run_git_command(args)

        if not success or not output:
            return []

        commits = []
        for line in output.splitlines():
            if not line:
                continue
            parts = line.split('|', 4)
            if len(parts) == 5:
                commits.append({
                    'hash': parts[0][:8],
                    'author': parts[1],
                    'email': parts[2],
                    'date': parts[3],
                    'message': parts[4]
                })
        return commits

    def get_remote_url(self) -> Optional[str]:
        """Get remote URL"""
        success, output = self._run_git_command(['remote', 'get-url', 'origin'])
        return output if success else None

    def set_remote(self, url: str) -> bool:
        """Set remote URL"""
        success, _ = self._run_git_command(['remote', 'add', 'origin', url])
        if not success:
            success, _ = self._run_git_command(['remote', 'set-url', 'origin', url])
        return success

    def clone(self, url: str, target_dir: Optional[str] = None) -> bool:
        """Clone a repository"""
        args = ['clone', url]
        if target_dir:
            args.append(target_dir)
        success, _ = self._run_git_command(args, timeout=60)
        if success and target_dir:
            self.project_root = target_dir
        return success

    def get_diff(self, file_path: Optional[str] = None) -> str:
        """Get diff of changes"""
        args = ['diff']
        if file_path:
            args.append(file_path)
        success, output = self._run_git_command(args)
        return output if success else ""

    def is_dirty(self) -> bool:
        """Check if working directory has changes"""
        status = self.get_status()
        return bool(status)

    def get_staged_files(self) -> List[str]:
        """Get list of staged files"""
        success, output = self._run_git_command(['diff', '--name-only', '--cached'])
        if success and output:
            return [f.strip() for f in output.splitlines() if f.strip()]
        return []

    def get_unstaged_files(self) -> List[str]:
        """Get list of unstaged files"""
        success, output = self._run_git_command(['diff', '--name-only'])
        if success and output:
            return [f.strip() for f in output.splitlines() if f.strip()]
        return []

    def get_untracked_files(self) -> List[str]:
        """Get list of untracked files"""
        success, output = self._run_git_command(['ls-files', '--others', '--exclude-standard'])
        if success and output:
            return [f.strip() for f in output.splitlines() if f.strip()]
        return []

    def manage_changelog(self):
        """
        Open the changelog manager window.

        A parent window must have been set via ``set_parent`` first; this
        method never creates its own root or runs a nested event loop.
        """
        if self.parent is None:
            raise RuntimeError(
                "manage_changelog requires a parent window; call set_parent() first"
            )
        ChangelogWindow = LazyLoader.get('libs.gui.changelog_ui', 'ChangelogWindow')
        ChangelogWindow(
            self.parent,
            project_root=self.project_root,
            status_callback=self.status_callback
        )

    def manage_license(self):
        """
        Open the license manager window.

        A parent window must have been set via ``set_parent`` first; this
        method never creates its own root or runs a nested event loop.
        """
        if self.parent is None:
            raise RuntimeError(
                "manage_license requires a parent window; call set_parent() first"
            )
        LicenseManagerWindow = LazyLoader.get('libs.gui.license_ui', 'LicenseManagerWindow')
        LicenseManagerWindow(
            self.parent,
            project_root=self.project_root,
            status_callback=self.status_callback
        )
