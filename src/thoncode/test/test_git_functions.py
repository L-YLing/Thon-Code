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

from libs.git_functions import GitFunctions

logger = get_logger("test_git_functions")


def _git_available() -> bool:
    """检测系统是否安装 git"""
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


@unittest.skipUnless(_git_available(), "系统未安装 git，跳过 Git 功能测试")
class GitFunctionsTests(unittest.TestCase):
    """GitFunctions Git 操作封装类的测试集

    在临时目录中初始化真实 git 仓库进行端到端验证。
    """

    def setUp(self):
        """初始化临时 git 仓库并配置提交者信息"""
        self.repo_dir = tempfile.mkdtemp(prefix="git_test_")
        self.git = GitFunctions(project_root=self.repo_dir, status_callback=self._on_status)
        self.git.init()
        # 配置本地提交者，避免 git 提交时报错
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                       cwd=self.repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"],
                       cwd=self.repo_dir, capture_output=True, check=True)
        logger.debug("setUp: 仓库 %s", self.repo_dir)
        print(f"[setUp] 初始化仓库: {self.repo_dir}")

    def tearDown(self):
        shutil.rmtree(self.repo_dir, ignore_errors=True)
        logger.debug("tearDown: 已清理 %s", self.repo_dir)

    def _on_status(self, msg: str):
        """状态回调，记录日志"""
        logger.debug("git status 回调: %s", msg)

    def _write_file(self, name: str, content: str = "hello\n"):
        """在仓库中写入文件"""
        path = os.path.join(self.repo_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_is_repo(self):
        """验证 is_repo 识别已初始化仓库"""
        self.assertTrue(self.git.is_repo())
        logger.info("is_repo = True")
        print("[PASS] is_repo 识别仓库成功")

    def test_is_repo_false_for_non_repo(self):
        """验证非仓库目录 is_repo 返回 False"""
        non_repo = tempfile.mkdtemp(prefix="git_norepo_")
        try:
            g = GitFunctions(project_root=non_repo)
            self.assertFalse(g.is_repo())
            print("[PASS] 非仓库目录 is_repo=False")
        finally:
            shutil.rmtree(non_repo, ignore_errors=True)

    def test_get_current_branch(self):
        """验证 get_current_branch 返回当前分支名"""
        branch = self.git.get_current_branch()
        logger.info("当前分支: %s", branch)
        self.assertIsNotNone(branch)
        self.assertTrue(len(branch) > 0)
        print(f"[PASS] 当前分支: {branch}")

    def test_get_branches(self):
        """验证 get_branches 返回分支列表

        新初始化且无提交的仓库 git branch 不列出任何分支，
        需先产生一次提交使分支实际存在。
        """
        # 先提交一次，使 master 分支真正建立
        self._write_file("init.txt", "init\n")
        self.git.add_all()
        self.git.commit("initial")
        branches = self.git.get_branches()
        logger.info("分支列表: %s", branches)
        self.assertGreaterEqual(len(branches), 1)
        print(f"[PASS] 分支数: {len(branches)}")

    def test_add_and_commit(self):
        """验证 add_file + commit 提交流程"""
        self._write_file("a.txt", "content a\n")
        self.assertTrue(self.git.add_file("a.txt"))
        self.assertTrue(self.git.commit("first commit"))
        log = self.git.get_log(limit=5)
        logger.info("提交日志: %s", log)
        self.assertGreaterEqual(len(log), 1)
        self.assertEqual(log[0]["message"], "first commit")
        print("[PASS] add/commit 流程成功")

    def test_get_status_empty(self):
        """验证干净工作区 get_status 为空字符串"""
        status = self.git.get_status()
        logger.info("空状态: '%s'", status)
        self.assertEqual(status, "")
        print("[PASS] 干净工作区状态为空")

    def test_get_status_with_changes(self):
        """验证有改动时 get_status 非空"""
        self._write_file("b.txt", "b\n")
        status = self.git.get_status()
        logger.info("改动状态: %s", status)
        self.assertIn("b.txt", status)
        print("[PASS] 改动状态正确")

    def test_get_status_detailed(self):
        """验证 get_status_detailed 分类未跟踪文件"""
        self._write_file("c.txt", "c\n")
        detail = self.git.get_status_detailed()
        logger.info("详细状态: %s", detail)
        self.assertIn("c.txt", detail["untracked"])
        print("[PASS] 详细状态分类正确")

    def test_get_untracked_files(self):
        """验证 get_untracked_files 返回未跟踪文件列表"""
        self._write_file("d.txt", "d\n")
        untracked = self.git.get_untracked_files()
        logger.info("未跟踪: %s", untracked)
        self.assertIn("d.txt", untracked)
        print("[PASS] 未跟踪文件列表正确")

    def test_is_dirty(self):
        """验证 is_dirty 检测工作区改动"""
        self.assertFalse(self.git.is_dirty())
        self._write_file("e.txt", "e\n")
        self.assertTrue(self.git.is_dirty())
        print("[PASS] is_dirty 检测正确")

    def test_create_and_switch_branch(self):
        """验证 create_branch + switch_branch 切换分支"""
        self._write_file("f.txt", "f\n")
        self.git.add_all()
        self.git.commit("init for branch")
        self.assertTrue(self.git.create_branch("feature"))
        self.assertTrue(self.git.switch_branch("feature"))
        self.assertEqual(self.git.get_current_branch(), "feature")
        logger.info("已切换到 feature 分支")
        print("[PASS] 创建并切换分支成功")

    def test_get_log_empty(self):
        """验证无提交时 get_log 返回空列表"""
        log = self.git.get_log()
        logger.info("空日志: %s", log)
        self.assertEqual(log, [])
        print("[PASS] 无提交日志为空")

    def test_add_all(self):
        """验证 add_all 暂存全部文件"""
        self._write_file("g.txt", "g\n")
        self._write_file("h.txt", "h\n")
        self.assertTrue(self.git.add_all())
        staged = self.git.get_staged_files()
        logger.info("暂存文件: %s", staged)
        self.assertIn("g.txt", staged)
        self.assertIn("h.txt", staged)
        print("[PASS] add_all 暂存成功")

    def test_get_diff_after_change(self):
        """验证提交后改动产生 diff 输出"""
        self._write_file("i.txt", "initial\n")
        self.git.add_all()
        self.git.commit("init i")
        # 修改文件产生 diff
        with open(os.path.join(self.repo_dir, "i.txt"), "w", encoding="utf-8") as f:
            f.write("modified\n")
        diff = self.git.get_diff("i.txt")
        logger.info("diff 长度: %d", len(diff))
        self.assertIn("modified", diff)
        print("[PASS] get_diff 输出正确")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 git_functions 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
