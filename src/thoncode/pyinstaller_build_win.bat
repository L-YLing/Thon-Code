pyinstaller --name ThonCode ^
    --onedir ^
    --windowed ^
    --icon "assets/icon.ico" ^
    --add-data "assets;assets" ^
    --add-data "libs;libs" ^
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
    main.py