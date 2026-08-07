#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.cfg_handle",
    "Entrance": "main.py"
}

import customtkinter as ctk
import libs.cfg_handle as cfg_handle

from libs.code_editor import CodeEditor

class MainWindow:
    def __init__(self) -> None:
        self.root = ctk.CTk()
        self.root.title("Thon Code")
        self.root.geometry("1200x675")

        # 配置网格权重（必须在grid之前设置）
        self._configure_grid_weights()

    def _configure_grid_weights(self) -> None:
        """设置行/列的拉伸权重，实现四边固定"""
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=0)

    def menu_bar(self) -> None:
        self.menu_bar = ctk.CTkFrame(self.root, height=40, fg_color="gray20")

    def sidebar_left(self) -> None:
        self.sidebar_left = ctk.CTkFrame(self.root, width=200, fg_color="gray25")

    def editor(self) -> None:
        """主编辑区：自定义 CodeEditor"""
        # 从配置中读取 font_ligatures 设置（先加载配置）
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        ligatures = cfg.get("font_ligatures", True)
        self.editor = CodeEditor(self.root, language="python", font_ligatures=ligatures)
        self.editor_widget = self.editor.get_widget()

    def sidebar_right(self) -> None:
        self.sidebar_right = ctk.CTkFrame(self.root, width=150, fg_color="gray25")

    def status_bar(self) -> None:
        self.status_bar = ctk.CTkLabel(
            self.root,
            text="就绪",
            anchor="w",
            height=25
        )

    def grid(self) -> None:
        """统一执行布局"""
        self.menu_bar.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.sidebar_left.grid(row=1, column=0, sticky="ns")
        # 使用 editor_widget 进行布局
        self.editor_widget.grid(row=1, column=1, sticky="nsew")
        self.sidebar_right.grid(row=1, column=2, sticky="ns")
        self.status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

if __name__ == "__main__":
    cfg_handle.cfg_handle().check_cfg_file()
    main_window = MainWindow()

    main_window.menu_bar()
    main_window.sidebar_left()
    main_window.editor()
    main_window.sidebar_right()
    main_window.status_bar()

    main_window.grid()
    main_window.root.mainloop()