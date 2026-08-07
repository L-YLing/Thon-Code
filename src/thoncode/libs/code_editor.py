# libs/code_editor.py
import customtkinter as ctk
import json
import os
import tkinter.font as tkfont
from libs import font_loader

class CodeEditor:
    def __init__(self, master, language: str = "python", font_ligatures: bool = True):
        self.master = master
        self.language = language
        self.keywords = []          # 简单关键词列表

        # 创建文本控件
        self.textbox = ctk.CTkTextbox(master, wrap="none")
        self._textbox = self.textbox._textbox

        # 加载字体
        self.font = font_loader.load_fira_code_font(master, size=12, ligatures=font_ligatures)
        self._textbox.config(font=self.font)

        # 选中样式
        self._textbox.tag_config("sel", background="#264f78", foreground="white")

        # 快捷键
        self._textbox.bind("<Control-a>", self.select_all)
        self._textbox.bind("<Control-A>", self.select_all)

        # 事件绑定（每次按键立即刷新）
        self._textbox.bind("<KeyRelease>", self.highlight_all)
        self._textbox.bind("<FocusIn>", self.highlight_all)

        # 加载语言配置
        self.load_language(language)

        # 首次高亮
        self.highlight_all()

    def get_widget(self):
        return self.textbox

    def load_language(self, language: str):
        config_dir = "assets/languages"
        os.makedirs(config_dir, exist_ok=True)
        file_path = os.path.join(config_dir, f"{language}.json")

        if not os.path.exists(file_path):
            self._create_default_language_file(language, file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 读取 keywords（兼容旧版）或 groups
            if "groups" in data:
                # 合并所有组的 words
                self.keywords = []
                for group in data["groups"]:
                    self.keywords.extend(group.get("words", []))
            else:
                self.keywords = data.get("keywords", [])

        # 调试：打印关键词数量
        print(f"[CodeEditor] 加载了 {len(self.keywords)} 个关键词")
        # 打印前10个作为示例
        if self.keywords:
            print(f"[CodeEditor] 示例关键词: {self.keywords[:10]}")

    def _create_default_language_file(self, language: str, path: str):
        default = {
            "keywords": [
                "False", "None", "True", "and", "as", "assert", "async", "await",
                "break", "class", "continue", "def", "del", "elif", "else", "except",
                "finally", "for", "from", "global", "if", "import", "in", "is",
                "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
                "try", "while", "with", "yield"
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)

    def highlight_all(self, event=None):
        """高亮整个文档（最简实现）"""
        text_widget = self._textbox

        # 清除所有自定义标签（保留 sel）
        for tag in text_widget.tag_names():
            if tag.startswith("kw_"):
                text_widget.tag_delete(tag)

        # 获取所有文本
        content = text_widget.get("1.0", "end-1c")
        if not content:
            return

        # 重新配置关键词标签（每次确保颜色有效）
        if self.keywords:
            text_widget.tag_config("kw_keyword", foreground="#C678DD")  # 紫色

        # 逐行扫描并添加标签
        lines = content.splitlines(keepends=True)
        line_num = 1
        for line in lines:
            self._highlight_line(text_widget, line_num, line)
            line_num += 1

        # 调试：添加了一个标签后打印一下
        # print("高亮刷新完成")

    def _highlight_line(self, text_widget, line_num, line_text):
        """对单行中的关键词添加标签（忽略字符串/注释）"""
        # 最简单的分词：按非字母数字下划线分割
        # 但为了准确，我们手动扫描单词
        i = 0
        n = len(line_text)
        while i < n:
            ch = line_text[i]
            if ch.isalnum() or ch == '_':
                start = i
                while i < n and (line_text[i].isalnum() or line_text[i] == '_'):
                    i += 1
                word = line_text[start:i]
                if word in self.keywords:
                    start_idx = f"{line_num}.{start}"
                    end_idx = f"{line_num}.{i}"
                    text_widget.tag_add("kw_keyword", start_idx, end_idx)
            else:
                i += 1

    def select_all(self, event=None):
        self._textbox.tag_add("sel", "1.0", "end")
        return "break"