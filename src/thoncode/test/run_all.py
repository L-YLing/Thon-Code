#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test Runner",
    "Path": ".main.test.run_all",
    "Entrance": "run_all.py"
}

import os
import sys
import time
import unittest

# 引导模块：配置 sys.path / 工作目录 / 日志
import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("run_all")

# 需要执行的后端模块测试列表 (每个后端模块独立文件)
TEST_MODULES: list = [
    "test_cfg_handle",
    "test_json_handle",
    "test_changelog_handle",
    "test_struct_handle",
    "test_langs_handle",
    "test_langs_loader",
    "test_license_handle",
    "test_font_loader",
    "test_git_functions",
]


def run_all() -> int:
    """加载并运行全部后端模块测试，返回失败用例总数

    Returns:
        int: 失败用例数，0 表示全部通过
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for mod_name in TEST_MODULES:
        try:
            module = __import__(mod_name)
            suite.addTests(loader.loadTestsFromModule(module))
            logger.info("已加载测试模块: %s", mod_name)
        except Exception as e:
            logger.error("加载测试模块 %s 失败: %s", mod_name, e)
            print(f"[ERROR] 加载 {mod_name} 失败: {e}")

    total = suite.countTestCases()
    print("=" * 60)
    print(f"开始运行 Thon Code 后端测试，共 {total} 个用例")
    print("=" * 60)
    logger.info("测试用例总数: %d", total)

    start = time.time()
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    elapsed = time.time() - start

    print("=" * 60)
    print(f"运行结束: 用时 {elapsed:.2f}s")
    print(f"  运行: {result.testsRun}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    print(f"  跳过: {len(result.skipped)}")
    print("=" * 60)
    logger.info("结果: 运行=%d 失败=%d 错误=%d 跳过=%d 用时=%.2fs",
                result.testsRun, len(result.failures), len(result.errors),
                len(result.skipped), elapsed)

    return len(result.failures) + len(result.errors)


if __name__ == "__main__":
    sys.exit(0 if run_all() == 0 else 1)
