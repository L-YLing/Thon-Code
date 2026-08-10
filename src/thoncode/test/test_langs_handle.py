#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - langs_handle",
    "Path": ".main.test.test_langs_handle",
    "Entrance": "main.py"
}

import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

import libs.langs_handle as langs_handle

logger = get_logger("test_langs_handle")


class LangsHandleTests(unittest.TestCase):
    """langs_handle 语言处理类的测试集"""

    def setUp(self):
        """引导模块已确保 assets/config.json 与语言资源可用"""
        self.h = langs_handle.langs_handle()
        print("[setUp] langs_handle 实例已创建")

    def test_default_language(self):
        """验证 default_language 返回成功状态与语言代码"""
        ret = self.h.default_language()
        logger.info("default_language 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertEqual(ret["code"], 200)
        self.assertIn(ret["data"], ("zh_cn", "en_us", "en_uk"))
        print(f"[PASS] default_language = {ret['data']}")

    def test_key_languages_known_key(self):
        """验证 key_languages 能读取已知键"""
        ret = self.h.key_languages("main.menu.file")
        logger.info("key_languages(main.menu.file) 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertIsInstance(ret["data"], str)
        self.assertTrue(len(ret["data"]) > 0)
        print(f"[PASS] key_languages(main.menu.file) = {ret['data']}")

    def test_key_languages_missing_key(self):
        """验证 key_languages 对不存在键返回错误"""
        ret = self.h.key_languages("not.exist.key")
        logger.info("key_languages(不存在) 返回: %s", ret)
        self.assertEqual(ret["status"], "error")
        print("[PASS] key_languages 不存在键返回 error")

    def test_load_full_language(self):
        """验证 load_full_language 返回非空字典"""
        data = self.h.load_full_language()
        logger.info("load_full_language 键数: %d", len(data))
        self.assertIsInstance(data, dict)
        self.assertGreater(len(data), 0)
        self.assertIn("main.menu.file", data)
        print(f"[PASS] load_full_language 加载 {len(data)} 个键")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 langs_handle 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
