# libs/font_loader.py
import tkinter.font as tkfont

def load_fira_code_font(master, size=12, ligatures=True):
    try:
        font = tkfont.Font(family="Fira Code", size=size)
        if "Fira" in font.actual()["family"]:
            return font
    except:
        pass

    try:
        font = tkfont.Font(family="Fira Code Regular", size=size)
        if "Fira" in font.actual()["family"]:
            return font
    except:
        pass

    return tkfont.Font(family="Courier New", size=size)