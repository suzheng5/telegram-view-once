@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo 未找到 Python。请先安装 Python 3.10+，并勾选 Add Python to PATH。
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo 正在创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo 创建虚拟环境失败。
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import PySide6, telethon, qrcode, PIL" >nul 2>nul
if errorlevel 1 (
    echo 正在安装依赖...
    ".venv\Scripts\python.exe" -m pip install -U pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo 安装依赖失败。
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
