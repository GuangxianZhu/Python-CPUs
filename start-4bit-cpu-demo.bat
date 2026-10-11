@echo off
chcp 65001 >nul
setlocal
title 4 位 CPU 互动教学
cd /d "%~dp04bit-cpu-demo"

rem ---- 找 Python：先试 py 启动器，再试 python ----
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo.
    echo [错误] 没有找到 Python 3.8 或更新的版本。
    echo.
    echo 请到 https://www.python.org/downloads/ 下载安装 Python，
    echo 安装时勾选 "Add python.exe to PATH"，装好后再双击本文件。
    echo （从应用商店弹出的那个 "python" 只是占位，不算安装好。）
    echo.
    pause
    exit /b 1
)

rem ---- 检查 tkinter ----
%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 找到了 Python，但它缺少 tkinter（画界面用的组件）。
    echo.
    echo 重新运行 Python 安装程序，选 "Modify"，
    echo 勾选 "tcl/tk and IDLE"，完成后再双击本文件。
    echo.
    pause
    exit /b 1
)

echo 正在启动 4 位 CPU 互动教学……（关闭程序窗口即可退出）
%PY% cpu_demo.py
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，上面是错误信息。截图发给老师或开发者即可。
    pause
    exit /b 1
)
endlocal
