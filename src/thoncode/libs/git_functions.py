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
    
    def _run_git_command(self, args: List[str], check_output: bool = False) -> tuple:
        """
        Run a git command and return result.
        
        Args:
            args: Git command arguments
            check_output: If True, return output as string
        
        Returns:
            tuple: (success: bool, output: str)
        """
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            success = result.returncode == 0
            output = result.stdout.strip() if success else result.stderr.strip()
            
            if self.status_callback:
                if success:
                    self.status_callback(f"Git: {output[:100]}")
                else:
                    self.status_callback(f"Git error: {output[:100]}")
            
            return success, output
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"Git exception: {str(e)}")
            return False, str(e)
    
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
        """Get git status output"""
        success, output = self._run_git_command(['status', '--short'])
        return output if success else ""
    
    def get_status_detailed(self) -> Dict[str, List[str]]:
        """Get detailed status with staged, unstaged, and untracked files"""
        status = {
            'staged': [],
            'unstaged': [],
            'untracked': []
        }
        
        success, output = self._run_git_command(['status', '--porcelain'])
        if not success or not output:
            return status
        
        for line in output.splitlines():
            if not line:
                continue
            code = line[:2]
            file_path = line[3:].strip()
            
            if code[0] in ('M', 'A', 'D', 'R', 'C'):
                status['staged'].append(file_path)
            
            if code[1] in ('M', 'D'):
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
        """Commit changes with message"""
        success, _ = self._run_git_command(['commit', '-m', message])
        return success
    
    def push(self, remote: str = 'origin', branch: str = 'HEAD') -> bool:
        """Push to remote"""
        success, _ = self._run_git_command(['push', remote, branch])
        return success
    
    def pull(self, remote: str = 'origin', branch: str = 'HEAD') -> bool:
        """Pull from remote"""
        success, _ = self._run_git_command(['pull', remote, branch])
        return success
    
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
    
    def discard_all(self) -> bool:
        """Discard all changes (use with caution)"""
        return self.checkout_file('.')
    
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
        success, _ = self._run_git_command(args)
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
        """Open changelog manager window"""
        ChangelogWindow = LazyLoader.get('libs.gui.changelog_ui', 'ChangelogWindow')
        if self.parent:
            ChangelogWindow(
                self.parent,
                project_root=self.project_root,
                status_callback=self.status_callback
            )
        else:
            # Fallback: create a temporary root
            import ttkbootstrap as ttkb
            root = ttkb.Window(themename="darkly")
            root.withdraw()
            ChangelogWindow(
                root,
                project_root=self.project_root,
                status_callback=self.status_callback
            )
            root.mainloop()
    
    def manage_license(self):
        """Open license manager window"""
        LicenseManagerWindow = LazyLoader.get('libs.gui.license_ui', 'LicenseManagerWindow')
        if self.parent:
            LicenseManagerWindow(
                self.parent,
                project_root=self.project_root,
                status_callback=self.status_callback
            )
        else:
            import ttkbootstrap as ttkb
            root = ttkb.Window(themename="darkly")
            root.withdraw()
            LicenseManagerWindow(
                root,
                project_root=self.project_root,
                status_callback=self.status_callback
            )
            root.mainloop()