# libs/font_loader.py
import tkinter.font as tkfont

def load_fira_code_font(master, size=12, ligatures=True):
    """
    加载 Fira Code 字体（需系统已安装），否则回退到 Courier New
    master: 父窗口（仅用于接口兼容，实际未使用）
    ligatures: 保留参数（Tkinter 无法控制连字）
    """
    # 尝试标准字体名 "Fira Code"
    try:
        font = tkfont.Font(family="Fira Code", size=size)
        if "Fira" in font.actual()["family"]:
            return font
    except:
        pass

    # 尝试备选名称 "Fira Code Regular"
    try:
        font = tkfont.Font(family="Fira Code Regular", size=size)
        if "Fira" in font.actual()["family"]:
            return font
    except:
        pass

    # 最终回退到系统等宽字体
    return tkfont.Font(family="Courier New", size=size)