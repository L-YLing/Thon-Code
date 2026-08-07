# libs/font_loader.py
import os
import urllib.request
import tkinter.font as tkfont

FONT_DIR = "assets/fonts"
FONT_FILE = "FiraCode-Regular.ttf"
FONT_URL = "https://cdnjs.cloudflare.com/ajax/libs/fira-code/6.2.0/FiraCode-Regular.ttf"

def ensure_font():
    """确保字体文件存在，若不存在则下载"""
    os.makedirs(FONT_DIR, exist_ok=True)
    font_path = os.path.join(FONT_DIR, FONT_FILE)
    if not os.path.exists(font_path):
        print("正在下载 Fira Code 字体...")
        try:
            urllib.request.urlretrieve(FONT_URL, font_path)
            print("下载完成")
        except Exception as e:
            print(f"下载失败: {e}，将使用系统默认等宽字体")
            return None
    return font_path

def load_fira_code_font(master, size=12, ligatures=True):
    """
    加载 Fira Code 字体，返回 tkinter.font.Font 对象
    master: 父窗口（用于 font 对象）
    ligatures: 保留参数，但 tkinter 无法控制连字开关，实际使用 Fira Code 即支持连字
    """
    font_path = ensure_font()
    if font_path is None:
        return tkfont.Font(family="Courier New", size=size)

    # 尝试从文件加载
    try:
        font = tkfont.Font(family="Fira Code", size=size, file=os.path.abspath(font_path))
        # 验证是否加载成功
        if "Fira" not in font.actual()["family"]:
            font = tkfont.Font(family="Fira Code", size=size)
        return font
    except Exception as e:
        print(f"从文件加载字体失败: {e}，尝试系统字体")
        try:
            return tkfont.Font(family="Fira Code", size=size)
        except:
            return tkfont.Font(family="Courier New", size=size)