@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo   ThonCode Nuitka 打包
echo ====================================
echo 正在使用 Nuitka 打包（请耐心等待，可能需要5-15分钟）...
echo.

nuitka --standalone ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=src/thoncode/assets/icon.ico ^
    --include-data-dir=assets=assets ^
    --include-package=libs ^
    --include-package=libs.code_editor ^
    --include-package=libs.cfg_handle ^
    --include-package=libs.font_loader ^
    --include-package=libs.json_handle ^
    --include-package=libs.langs_handle ^
    --include-module=customtkinter ^
    --include-module=PIL ^
    --include-module=PIL.Image ^
    --include-module=PIL.ImageTk ^
    --enable-plugin=tk-inter ^
    --output-dir=dist ^
    src/thoncode/main.py

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