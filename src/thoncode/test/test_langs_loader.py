#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - langs_loader",
    "Path": ".main.test.test_langs_loader",
    "Entrance": "main.py"
}

import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

import libs.langs_loader as langs_loader
from libs.langs_loader import langs

logger = get_logger("test_langs_loader")


class LangsLoaderTests(unittest.TestCase):
    """langs_loader 动态语言加载器的测试集

    langs_loader 在导入时将语言 JSON 的键 (将 '.' 替换为 '_') 设为 langs 类属性，
    本测试集验证该动态属性生成机制。
    """

    def setUp(self):
        print("[setUp] langs_loader 已导入")

    def test_lang_data_loaded(self):
        """验证 _lang_data 已加载非空数据"""
        data = langs._lang_data
        logger.info("_lang_data 键数: %d", len(data))
        self.assertIsInstance(data, dict)
        self.assertGreater(len(data), 0)
        print(f"[PASS] _lang_data 加载 {len(data)} 个键")

    def test_dynamic_attribute_exists(self):
        """验证点号键已转换为下划线类属性"""
        # main.menu.file -> main_menu_file
        self.assertTrue(hasattr(langs, "main_menu_file"))
        val = getattr(langs, "main_menu_file")
        logger.info("langs.main_menu_file = %s", val)
        self.assertIsInstance(val, str)
        self.assertTrue(len(val) > 0)
        print(f"[PASS] langs.main_menu_file = {val}")

    def test_attribute_matches_data(self):
        """验证动态属性值与原始数据一致"""
        data = langs._lang_data
        for key, value in data.items():
            attr = key.replace(".", "_")
            self.assertEqual(getattr(langs, attr), value,
                             f"属性 {attr} 与数据不一致")
        logger.info("全部 %d 个属性与数据一致", len(data))
        print(f"[PASS] {len(data)} 个动态属性与数据一致")

    def test_known_value_content(self):
        """验证已知键的值符合预期语义"""
        # main.menu.exit 应为非空字符串
        self.assertTrue(hasattr(langs, "main_menu_exit"))
        val = getattr(langs, "main_menu_exit")
        logger.info("main_menu_exit = %s", val)
        self.assertTrue(len(val) > 0)
        print(f"[PASS] main_menu_exit = {val}")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 langs_loader 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
