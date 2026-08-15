@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo   ThonCode Nuitka 打包
echo ====================================
echo 正在使用 Nuitka 打包（请耐心等待，可能需要5-15分钟）...
echo.

nuitka --standalone ^
    --windows-icon-from-ico=assets/icon.ico ^
    --include-data-dir=assets=assets ^
    --include-module=libs ^
    --include-module=libs.gui ^
    --include-module=libs.gui.code_editor ^
    --include-module=libs.gui.configure_runtime ^
    --include-module=libs.gui.editor_completion ^
    --include-module=libs.gui.editor_folding ^
    --include-module=libs.gui.editor_highlight ^
    --include-module=libs.gui.editor_manager ^
    --include-module=libs.gui.editor_shortcuts ^
    --include-module=libs.gui.editor_ui ^
    --include-module=libs.gui.project_cfg ^
    --include-module=libs.gui.run_file ^
    --include-module=libs.gui.settings_win ^
    --include-module=libs.gui.tree_manager ^
    --include-module=libs.cfg_handle ^
    --include-module=libs.struct_handle ^
    --include-module=libs.font_loader ^
    --include-module=libs.json_handle ^
    --include-module=libs.langs_handle ^
    --include-module=customtkinter ^
    --include-module=PIL ^
    --include-module=PIL.Image ^
    --include-module=PIL.ImageTk ^
    --enable-plugin=tk-inter ^
    --output-dir=dist ^
    --remove-output ^
    main.py

if exist dist\main.dist\main.exe (
    echo.
    echo ====================================
    echo   打包成功！
    echo ====================================
    echo 输出: dist\main.dist\main.exe
) else (
    echo.
    echo ====================================
    echo   打包失败！
    echo ====================================
)

pause