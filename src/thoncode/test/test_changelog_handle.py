#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - changelog_handle",
    "Path": ".main.test.test_changelog_handle",
    "Entrance": "main.py"
}

import os
import json
import shutil
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

from libs.changelog_handle import ChangelogHandle, ChangelogEntry

logger = get_logger("test_changelog_handle")


SAMPLE_CHANGELOG = """# Changelog

## [1.0.0] - 2024-01-01
### Added
- Initial release
- Core editor support

### Fixed
- Startup crash

## [Unreleased]
### Added
- New test suite
"""


class ChangelogHandleTests(unittest.TestCase):
    """ChangelogHandle 更新日志处理类的测试集"""

    def setUp(self):
        """每个用例使用独立临时项目目录"""
        self.tmp_dir = tempfile.mkdtemp(prefix="changelog_test_")
        logger.debug("setUp: 临时目录 %s", self.tmp_dir)
        print(f"[setUp] 使用临时目录: {self.tmp_dir}")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        logger.debug("tearDown: 已清理 %s", self.tmp_dir)

    def test_parse_changelog(self):
        """验证 parse_changelog 能解析版本与分区"""
        h = ChangelogHandle(self.tmp_dir)
        entries = h.parse_changelog(SAMPLE_CHANGELOG)
        logger.info("解析到 %d 条记录", len(entries))
        self.assertEqual(len(entries), 2)
        versions = [e.version for e in entries]
        self.assertIn("1.0.0", versions)
        self.assertIn("Unreleased", versions)
        # parse_changelog 返回列表但不修改 self.entries，从返回值中查找
        e = next((x for x in entries if x.version == "1.0.0"), None)
        self.assertIsNotNone(e)
        self.assertIn("Added", e.sections)
        self.assertIn("Initial release", e.sections["Added"])
        print("[PASS] parse_changelog 解析版本与分区成功")

    def test_generate_markdown_roundtrip(self):
        """验证解析后再生成的 markdown 包含关键结构"""
        h = ChangelogHandle(self.tmp_dir)
        h.entries = h.parse_changelog(SAMPLE_CHANGELOG)
        md = h.generate_markdown()
        logger.info("生成 markdown 长度: %d", len(md))
        self.assertIn("## [1.0.0]", md)
        self.assertIn("### Added", md)
        self.assertIn("Initial release", md)
        print("[PASS] generate_markdown 往返结构正确")

    def test_add_and_remove_entry(self):
        """验证 add_entry 新增与 remove_entry 删除流程"""
        h = ChangelogHandle(self.tmp_dir)
        h.add_entry("0.9.0", "2023-12-01", {"Added": ["Beta"]})
        self.assertIn("0.9.0", h.get_versions())
        logger.info("当前版本: %s", h.get_versions())
        self.assertTrue(h.remove_entry("0.9.0"))
        self.assertNotIn("0.9.0", h.get_versions())
        print("[PASS] add/remove entry 流程成功")

    def test_add_entry_updates_existing(self):
        """验证 add_entry 对已存在版本执行更新"""
        h = ChangelogHandle(self.tmp_dir)
        h.add_entry("1.0.0", "2024-01-01", {"Added": ["first"]})
        h.add_entry("1.0.0", "2024-01-02", {"Added": ["second"]})
        e = h.get_entry("1.0.0")
        logger.info("更新后 entry: %s", e.sections)
        self.assertEqual(e.date, "2024-01-02")
        self.assertEqual(e.sections["Added"], ["second"])
        print("[PASS] add_entry 更新已存在版本成功")

    def test_get_latest_version(self):
        """验证 get_latest_version 跳过 Unreleased 返回最新正式版本"""
        h = ChangelogHandle(self.tmp_dir)
        h.entries = h.parse_changelog(SAMPLE_CHANGELOG)
        latest = h.get_latest_version()
        logger.info("latest_version: %s", latest)
        self.assertEqual(latest, "1.0.0")
        print("[PASS] get_latest_version 正确")

    def test_export_import_json(self):
        """验证 export_to_json 与 import_from_json 往返一致"""
        h = ChangelogHandle(self.tmp_dir)
        h.entries = h.parse_changelog(SAMPLE_CHANGELOG)
        export_path = os.path.join(self.tmp_dir, "out.json")
        self.assertTrue(h.export_to_json(export_path))
        with open(export_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("导出条目数: %d", len(data))
        self.assertEqual(len(data), 2)

        h2 = ChangelogHandle(self.tmp_dir)
        self.assertTrue(h2.import_from_json(export_path))
        self.assertEqual(h2.get_versions(), h.get_versions())
        print("[PASS] export/import JSON 往返一致")

    def test_get_template(self):
        """验证 get_template 包含 Unreleased 与分区头"""
        h = ChangelogHandle(self.tmp_dir)
        tpl = h.get_template()
        logger.info("模板片段: %s", tpl[:80])
        self.assertIn("[Unreleased]", tpl)
        self.assertIn("### Added", tpl)
        print("[PASS] get_template 结构正确")

    def test_create_empty_changelog(self):
        """验证 create_empty_changelog 创建文件并解析条目"""
        h = ChangelogHandle(self.tmp_dir)
        self.assertTrue(h.create_empty_changelog())
        self.assertTrue(os.path.exists(h.changelog_path))
        self.assertTrue(len(h.entries) > 0)
        print("[PASS] create_empty_changelog 成功")

    def test_generate_release_notes(self):
        """验证 generate_release_notes 能为指定版本生成发布说明"""
        h = ChangelogHandle(self.tmp_dir)
        h.entries = h.parse_changelog(SAMPLE_CHANGELOG)
        notes = h.generate_release_notes("1.0.0")
        logger.info("release notes 片段: %s", notes[:80] if notes else None)
        self.assertIsNotNone(notes)
        self.assertIn("1.0.0", notes)
        self.assertIn("Initial release", notes)
        print("[PASS] generate_release_notes 成功")

    def test_get_changelog_preview(self):
        """验证 get_changelog_preview 返回近期变更预览"""
        h = ChangelogHandle(self.tmp_dir)
        h.entries = h.parse_changelog(SAMPLE_CHANGELOG)
        preview = h.get_changelog_preview(max_entries=2)
        logger.info("preview 片段: %s", preview[:80])
        self.assertIn("Recent Changes", preview)
        print("[PASS] get_changelog_preview 成功")

    def test_load_save_changelog(self):
        """验证 load_changelog 与 save_changelog 文件读写流程"""
        h = ChangelogHandle(self.tmp_dir)
        h.entries = h.parse_changelog(SAMPLE_CHANGELOG)
        self.assertTrue(h.save_changelog())
        h2 = ChangelogHandle(self.tmp_dir)
        self.assertTrue(h2.load_changelog())
        logger.info("加载版本: %s", h2.get_versions())
        self.assertEqual(h2.get_versions(), h.get_versions())
        print("[PASS] load/save changelog 流程成功")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 changelog_handle 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
