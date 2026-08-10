#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - cfg_handle",
    "Path": ".main.test.test_cfg_handle",
    "Entrance": "main.py"
}

import os
import sys
import json
import shutil
import tempfile
import unittest

# 引导模块：配置 sys.path / 工作目录 / 日志
import _bootstrap  # noqa: F401
from _bootstrap import get_logger

import libs.cfg_handle as cfg_handle

logger = get_logger("test_cfg_handle")


class CfgHandleTests(unittest.TestCase):
    """cfg_handle 配置读写类的测试集"""

    def setUp(self):
        """每个用例使用独立的临时配置文件，避免污染真实配置"""
        self.tmp_dir = tempfile.mkdtemp(prefix="cfg_test_")
        self.cfg_path = os.path.join(self.tmp_dir, "config.json")
        logger.debug("setUp: 临时配置 %s", self.cfg_path)
        print(f"[setUp] 使用临时配置: {self.cfg_path}")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        logger.debug("tearDown: 已清理 %s", self.tmp_dir)

    def test_make_cfg_file(self):
        """验证 make_cfg_file 能创建配置文件并返回成功状态"""
        h = cfg_handle.cfg_handle(self.cfg_path)
        ret = h.make_cfg_file()
        logger.info("make_cfg_file 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertEqual(ret["code"], 200)
        self.assertTrue(os.path.exists(self.cfg_path))
        print("[PASS] make_cfg_file 创建配置文件成功")

    def test_check_cfg_file_create_when_missing(self):
        """验证配置文件缺失时 check_cfg_file 会自动创建"""
        h = cfg_handle.cfg_handle(self.cfg_path)
        ret = h.check_cfg_file()
        logger.info("check_cfg_file(缺失) 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertTrue(os.path.exists(self.cfg_path))
        print("[PASS] check_cfg_file 缺失时自动创建成功")

    def test_check_cfg_file_existing(self):
        """验证配置文件已存在时 check_cfg_file 返回 201"""
        h = cfg_handle.cfg_handle(self.cfg_path)
        h.make_cfg_file()
        ret = h.check_cfg_file()
        logger.info("check_cfg_file(存在) 返回: %s", ret)
        self.assertEqual(ret["code"], 201)
        print("[PASS] check_cfg_file 识别已存在文件成功")

    def test_read_cfg(self):
        """验证 read_cfg 能正确读取配置数据"""
        h = cfg_handle.cfg_handle(self.cfg_path)
        h.make_cfg_file({"language": "zh_cn", "theme": "dark"})
        ret = h.read_cfg()
        logger.info("read_cfg 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertEqual(ret["data"]["language"], "zh_cn")
        self.assertEqual(ret["data"]["theme"], "dark")
        print("[PASS] read_cfg 读取配置数据成功")

    def test_read_cfg_regenerates_when_corrupt(self):
        """验证配置文件损坏时 read_cfg 能自动重建"""
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json !!!")
        h = cfg_handle.cfg_handle(self.cfg_path)
        ret = h.read_cfg()
        logger.info("read_cfg(损坏) 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        self.assertIn("language", ret["data"])
        print("[PASS] read_cfg 损坏文件自动重建成功")

    def test_write_cfg(self):
        """验证 write_cfg 能写入配置并返回成功"""
        h = cfg_handle.cfg_handle(self.cfg_path)
        ret = h.write_cfg({"language": "en_us", "theme": "light"})
        logger.info("write_cfg 返回: %s", ret)
        self.assertEqual(ret["status"], "success")
        with open(self.cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["language"], "en_us")
        print("[PASS] write_cfg 写入配置成功")

    def test_get_project_config_creates_default(self):
        """验证 get_project_config 在无配置时创建默认项目配置"""
        proj_dir = os.path.join(self.tmp_dir, "proj")
        os.makedirs(proj_dir)
        h = cfg_handle.cfg_handle(self.cfg_path)
        data = h.get_project_config(proj_dir)
        logger.info("get_project_config 返回: %s", data)
        self.assertIn("python_path", data)
        self.assertIn("dependencies", data)
        self.assertTrue(os.path.exists(os.path.join(proj_dir, ".thoncode", "project.json")))
        print("[PASS] get_project_config 创建默认配置成功")

    def test_save_project_config(self):
        """验证 save_project_config 能保存项目配置"""
        proj_dir = os.path.join(self.tmp_dir, "proj")
        os.makedirs(proj_dir)
        h = cfg_handle.cfg_handle(self.cfg_path)
        h.save_project_config(proj_dir, {"python_path": "/usr/bin/python3", "dependencies": ["pytest"]})
        cfg_file = os.path.join(proj_dir, ".thoncode", "project.json")
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("save_project_config 写入: %s", data)
        self.assertEqual(data["python_path"], "/usr/bin/python3")
        self.assertEqual(data["dependencies"], ["pytest"])
        print("[PASS] save_project_config 保存成功")

    def test_recent_projects_flow(self):
        """验证 add_recent_project 去重置顶与 get_recent_projects 读取"""
        h = cfg_handle.cfg_handle(self.cfg_path)
        h.make_cfg_file()
        h.add_recent_project("/path/a")
        h.add_recent_project("/path/b")
        h.add_recent_project("/path/a")  # 重复添加应置顶
        recent = h.get_recent_projects()
        logger.info("recent_projects: %s", recent)
        self.assertEqual(recent[0], "/path/a")
        self.assertEqual(recent[1], "/path/b")
        self.assertEqual(len(recent), 2)
        print("[PASS] recent_projects 去重置顶流程成功")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 cfg_handle 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
