#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - struct_handle",
    "Path": ".main.test.test_struct_handle",
    "Entrance": "main.py"
}

import os
import json
import shutil
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

from libs.struct_handle import get_dir_structure

logger = get_logger("test_struct_handle")


class StructHandleTests(unittest.TestCase):
    """struct_handle.get_dir_structure 目录结构扫描函数的测试集"""

    def setUp(self):
        """构造临时目录树用于扫描"""
        self.root = tempfile.mkdtemp(prefix="struct_test_")
        # 子目录与文件
        os.makedirs(os.path.join(self.root, "pkg", "sub"))
        with open(os.path.join(self.root, "pkg", "__init__.py"), "w", encoding="utf-8") as f:
            f.write("# init\n")
        with open(os.path.join(self.root, "pkg", "sub", "a.py"), "w", encoding="utf-8") as f:
            f.write("print('a')\n")
        with open(os.path.join(self.root, "README.md"), "w", encoding="utf-8") as f:
            f.write("# README\n")
        logger.debug("setUp: 临时目录树 %s", self.root)
        print(f"[setUp] 构造目录树: {self.root}")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        logger.debug("tearDown: 已清理 %s", self.root)

    def test_str_output_format(self):
        """验证 str 输出格式包含树形连接符与目录名"""
        result = get_dir_structure(self.root, output_format="str")
        logger.info("str 输出片段:\n%s", result[:120])
        self.assertIsInstance(result, str)
        self.assertIn("pkg/", result)
        self.assertIn("README.md", result)
        print("[PASS] str 输出格式正确")

    def test_json_output_format(self):
        """验证 json 输出格式返回结构化字典"""
        result = get_dir_structure(self.root, output_format="json")
        logger.info("json 顶层 keys: %s", list(result.keys()))
        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "dir")
        self.assertIn("children", result)
        names = [c["name"] for c in result["children"]]
        self.assertIn("pkg", names)
        self.assertIn("README.md", names)
        print("[PASS] json 输出格式正确")

    def test_invalid_format_raises(self):
        """验证不支持的输出格式抛出 ValueError"""
        with self.assertRaises(ValueError):
            get_dir_structure(self.root, output_format="xml")
        logger.info("非法格式正确抛出 ValueError")
        print("[PASS] 非法格式抛出 ValueError")

    def test_nonexistent_path_raises(self):
        """验证不存在的路径抛出 FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            get_dir_structure(os.path.join(self.root, "no_such_dir"))
        logger.info("不存在路径正确抛出 FileNotFoundError")
        print("[PASS] 不存在路径抛出 FileNotFoundError")

    def test_max_depth_limit(self):
        """验证 max_depth 限制递归深度

        max_depth=0 时根目录的直接子项仍列出，但不递归进入子目录，
        即 pkg 作为目录出现但其 children 为空。
        """
        result = get_dir_structure(self.root, output_format="json", max_depth=0)
        children = result["children"]
        logger.info("max_depth=0 children 数: %d", len(children))
        # 直接子项 (文件 + 目录) 仍应列出
        self.assertGreaterEqual(len(children), 2)
        # pkg 子目录不应再递归，children 必须为空
        pkg_node = next((c for c in children if c["name"] == "pkg"), None)
        self.assertIsNotNone(pkg_node)
        self.assertEqual(pkg_node["children"], [])
        print("[PASS] max_depth 限制生效")

    def test_include_file_content(self):
        """验证 include_file_content 能读取 .py 文件内容"""
        result = get_dir_structure(self.root, output_format="json", include_file_content=True)
        # 在 children 中查找 a.py
        def find_file(node, name):
            if node.get("name") == name:
                return node
            for c in node.get("children", []):
                found = find_file(c, name)
                if found:
                    return found
            return None
        a_node = find_file(result, "a.py")
        logger.info("a.py 节点: %s", a_node)
        self.assertIsNotNone(a_node)
        self.assertIn("content", a_node)
        self.assertIn("print('a')", a_node["content"])
        print("[PASS] include_file_content 读取文件内容成功")

    def test_str_output_to_file(self):
        """验证 output_file 参数能将 str 结果写入文件"""
        out_file = os.path.join(self.root, "tree.txt")
        # 注意: 输出文件本身也会被扫描，先扫描再写到外部
        out_file = os.path.join(tempfile.gettempdir(), "struct_tree_out.txt")
        get_dir_structure(self.root, output_format="str", output_file=out_file)
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info("输出文件长度: %d", len(content))
        self.assertTrue(os.path.exists(out_file))
        self.assertIn("pkg/", content)
        os.remove(out_file)
        print("[PASS] output_file 写入成功")

    def test_json_output_to_file(self):
        """验证 output_file 参数能将 json 结果写入文件"""
        out_file = os.path.join(tempfile.gettempdir(), "struct_tree_out.json")
        get_dir_structure(self.root, output_format="json", output_file=out_file)
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("json 文件 type: %s", data.get("type"))
        self.assertEqual(data["type"], "dir")
        os.remove(out_file)
        print("[PASS] json output_file 写入成功")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 struct_handle 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
