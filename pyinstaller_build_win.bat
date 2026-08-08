pyinstaller --name ThonCode ^
    --onedir ^
    --windowed ^
    --icon "src/thoncode/assets/icon.ico" ^
    --add-data "src/thoncode/assets;src/thoncode/assets" ^
    --add-data "src/thoncode/libs;src/thoncode/libs" ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageTk ^
    --hidden-import send2trash ^
    --hidden-import libs ^
    --hidden-import libs.code_editor ^
    --hidden-import libs.cfg_handle ^
    --hidden-import libs.font_loader ^
    --hidden-import libs.json_handle ^
    --hidden-import libs.langs_handle ^
    --collect-all libs ^
    src/thoncode/main.py