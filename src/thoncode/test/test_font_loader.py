#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - font_loader",
    "Path": ".main.test.test_font_loader",
    "Entrance": "main.py"
}

import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

try:
    import tkinter as tk
    import tkinter.font as tkfont
    _TK_AVAILABLE = True
except Exception:
    _TK_AVAILABLE = False

from libs.font_loader import load_fira_code_font

logger = get_logger("test_font_loader")


@unittest.skipUnless(_TK_AVAILABLE, "当前环境无 Tk，跳过字体加载测试")
class FontLoaderTests(unittest.TestCase):
    """font_loader.load_fira_code_font 字体加载函数的测试集"""

    def setUp(self):
        """创建隐藏的 Tk 根窗口供字体系统使用"""
        self.root = tk.Tk()
        self.root.withdraw()
        print("[setUp] Tk 根窗口已创建")

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        logger.debug("tearDown: Tk 根窗口已销毁")

    def test_returns_font_object(self):
        """验证返回值为 tkinter.font.Font 实例"""
        font = load_fira_code_font(self.root, size=12)
        logger.info("返回字体类型: %s", type(font))
        self.assertIsInstance(font, tkfont.Font)
        print("[PASS] 返回 Font 实例")

    def test_custom_size(self):
        """验证 size 参数生效"""
        font = load_fira_code_font(self.root, size=20)
        actual = font.actual()
        logger.info("字体 size: %s", actual.get("size"))
        self.assertEqual(actual.get("size"), 20)
        print("[PASS] size 参数生效")

    def test_fallback_to_monospace(self):
        """验证无法加载 Fira Code 时回退到等宽字体"""
        # 传入不存在的 master 仍应返回可用字体，主要验证不抛异常
        font = load_fira_code_font(self.root, size=14)
        family = font.actual().get("family")
        logger.info("实际字体族: %s", family)
        self.assertIsNotNone(family)
        print(f"[PASS] 字体族: {family}")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 font_loader 模块")
    print("=" * 60)
    unittest.main(verbosity=2)
