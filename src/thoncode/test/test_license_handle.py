#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - license_handle",
    "Path": ".main.test.test_license_handle",
    "Entrance": "main.py"
}

import os
import shutil
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

from libs.license_handle import LicenseHandle

logger = get_logger("test_license_handle")


class LicenseHandleTests(unittest.TestCase):
    """LicenseHandle 许可证处理类的测试集"""

    def setUp(self):
        """使用临时目录作为 license_dir，避免污染项目 assets"""
        self.tmp_dir = tempfile.mkdtemp(prefix="license_test_")
        self.h = LicenseHandle()
        # 覆盖实例的 license_dir 指向临时目录，保持测试隔离
        self.h.license_dir = self.tmp_dir
        logger.debug("setUp: 临时 license_dir %s", self.tmp_dir)
        print(f"[setUp] 使用临时目录: {self.tmp_dir}")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        logger.debug("tearDown: 已清理 %s", self.tmp_dir)

    def test_get_available_licenses_empty(self):
        """验证空目录时 get_available_licenses 返回空列表"""
        result = self.h.get_available_licenses()
        logger.info("空目录 licenses: %s", result)
        self.assertEqual(result, [])
        print("[PASS] 空目录返回空列表")

    def test_add_and_get_license(self):
        """验证 add_license 新增与 get_license_content 读取"""
        content = "# MIT License\n\nCopyright (c) 2024 Test"
        self.assertTrue(self.h.add_license("MIT", content))
        result = self.h.get_available_licenses()
        logger.info("可用 licenses: %s", result)
        self.assertIn("MIT", result)
        got = self.h.get_license_content("MIT")
        self.assertEqual(got, content)
        print("[PASS] add/get license 成功")

    def test_get_license_content_missing(self):
        """验证读取不存在的许可证返回 None"""
        result = self.h.get_license_content("NotExistent")
        logger.info("不存在许可证返回: %s", result)
        self.assertIsNone(result)
        print("[PASS] 不存在许可证返回 None")

    def test_get_license_path(self):
        """验证 get_license_path 返回正确路径"""
        self.h.add_license("Apache", "# Apache")
        path = self.h.get_license_path("Apache")
        logger.info("Apache 路径: %s", path)
        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))
        print("[PASS] get_license_path 正确")

    def test_get_license_path_missing(self):
        """验证不存在许可证路径返回 None"""
        path = self.h.get_license_path("Missing")
        self.assertIsNone(path)
        print("[PASS] 不存在路径返回 None")

    def test_delete_license(self):
        """验证 delete_license 删除模板"""
        self.h.add_license("GPL", "# GPL")
        self.assertTrue(self.h.delete_license("GPL"))
        self.assertNotIn("GPL", self.h.get_available_licenses())
        print("[PASS] delete_license 成功")

    def test_delete_license_missing(self):
        """验证删除不存在的许可证返回 False"""
        self.assertFalse(self.h.delete_license("Nope"))
        print("[PASS] 删除不存在返回 False")

    def test_add_license_empty_name(self):
        """验证空名称 add_license 返回 False"""
        self.assertFalse(self.h.add_license("", "content"))
        print("[PASS] 空名称拒绝创建")

    def test_apply_license_to_project(self):
        """验证 apply_license_to_project 写入 LICENSE 文件并替换变量"""
        self.h.add_license("MIT", "Copyright (c) [year] [author]")
        proj = tempfile.mkdtemp(prefix="license_proj_")
        try:
            ok = self.h.apply_license_to_project(
                proj, "MIT", custom_vars={"year": "2024", "author": "Thon"}
            )
            self.assertTrue(ok)
            license_file = os.path.join(proj, "LICENSE")
            self.assertTrue(os.path.exists(license_file))
            with open(license_file, "r", encoding="utf-8") as f:
                txt = f.read()
            logger.info("生成 LICENSE: %s", txt)
            self.assertIn("2024", txt)
            self.assertIn("Thon", txt)
            self.assertNotIn("[year]", txt)
            print("[PASS] apply_license_to_project 变量替换成功")
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_apply_license_missing_template(self):
        """验证应用不存在的许可证模板返回 False"""
        proj = tempfile.mkdtemp(prefix="license_proj_")
        try:
            ok = self.h.apply_license_to_project(proj, "Missing")
            self.assertFalse(ok)
            print("[PASS] 不存在模板应用返回 False")
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_read_project_license(self):
        """验证 read_project_license 读取项目 LICENSE 文件"""
        proj = tempfile.mkdtemp(prefix="license_proj_")
        try:
            license_file = os.path.join(proj, "LICENSE")
            with open(license_file, "w", encoding="utf-8") as f:
                f.write("Custom License Text")
            content = self.h.read_project_license(proj)
            logger.info("读取项目 LICENSE: %s", content)
            self.assertEqual(content, "Custom License Text")
            print("[PASS] read_project_license 成功")
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_read_project_license_missing(self):
        """验证项目无 LICENSE 时 read_project_license 返回 None"""
        proj = tempfile.mkdtemp(prefix="license_proj_")
        try:
            content = self.h.read_project_license(proj)
            self.assertIsNone(content)
            print("[PASS] 无 LICENSE 返回 None")
        finally:
            shutil.rmtree(proj, ignore_errors=True)


if __name__ == "__main__":
    print("=" * 60)
    print("测试 license_handle 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
