#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - json_handle",
    "Path": ".main.test.test_json_handle",
    "Entrance": "main.py"
}

import os
import json
import shutil
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

import libs.json_handle as json_handle

logger = get_logger("test_json_handle")


class JsonHandleTests(unittest.TestCase):
    """json_handle.handle 类的测试集"""

    def setUp(self):
        """每个用例使用独立的临时 JSON 文件"""
        self.tmp_dir = tempfile.mkdtemp(prefix="json_test_")
        self.json_path = os.path.join(self.tmp_dir, "data.json")
        logger.debug("setUp: 临时 JSON %s", self.json_path)
        print(f"[setUp] 使用临时 JSON: {self.json_path}")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        logger.debug("tearDown: 已清理 %s", self.tmp_dir)

    def test_get_json_file_not_found(self):
        """验证文件不存在时 get_json 返回 404 错误"""
        h = json_handle.handle(self.json_path)
        ret = h.get_json()
        logger.info("get_json(不存在) 返回: %s", ret)
        self.assertEqual(ret["status"], "error")
        self.assertEqual(ret["code"], 404)
        print("[PASS] get_json 文件不存在返回 404")

    def test_get_json_invalid_format(self):
        """验证 JSON 格式错误时 get_json 返回 500 错误"""
        with open(self.json_path, "w", encoding="utf-8") as f:
            f.write("{ broken json !!!")
        h = json_handle.handle(self.json_path)
        ret = h.get_json()
        logger.info("get_json(格式错误) 返回: %s", ret)
        self.assertEqual(ret["status"], "error")
        self.assertEqual(ret["code"], 500)
        print("[PASS] get_json 格式错误返回 500")

    def test_get_json_success(self):
        """验证正常读取 JSON 文件"""
        payload = {"name": "thon", "version": "1.0", "items": [1, 2, 3]}
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        h = json_handle.handle(self.json_path)
        ret = h.get_json()
        logger.info("get_json(正常) 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertEqual(ret["code"], 200)
        self.assertEqual(ret["data"]["name"], "thon")
        self.assertEqual(ret["data"]["items"], [1, 2, 3])
        print("[PASS] get_json 正常读取成功")

    def test_write_json_success(self):
        """验证 write_json 能写入数据并返回成功"""
        h = json_handle.handle(self.json_path)
        ret = h.write_json({"key": "value", "num": 42})
        logger.info("write_json 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertEqual(ret["code"], 200)
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["key"], "value")
        self.assertEqual(data["num"], 42)
        print("[PASS] write_json 写入成功")

    def test_write_then_read_roundtrip(self):
        """验证写入后再读取的一致性"""
        h = json_handle.handle(self.json_path)
        payload = {"language": "zh_cn", "nested": {"a": 1}}
        h.write_json(payload)
        ret = h.get_json()
        logger.info("roundtrip 读取: %s", ret)
        self.assertEqual(ret["data"], payload)
        print("[PASS] write/read 往返一致")

    def test_write_json_unicode_preserved(self):
        """验证写入中文内容时 ensure_ascii=False 生效"""
        h = json_handle.handle(self.json_path)
        h.write_json({"greeting": "你好，世界"})
        with open(self.json_path, "r", encoding="utf-8") as f:
            raw = f.read()
        logger.info("unicode 原文: %s", raw)
        self.assertIn("你好，世界", raw)
        print("[PASS] write_json 中文不被转义")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 json_handle 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
