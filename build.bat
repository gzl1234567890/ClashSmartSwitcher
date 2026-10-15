@echo off
setlocal
cd /d "%~dp0"
set "TASK_PYTHON=%~dp0.conda\clash-smart-switcher\python.exe"
if not exist "%TASK_PYTHON%" set "TASK_PYTHON=python"
"%TASK_PYTHON%" -m pip install -r requirements-dev.txt
if errorlevel 1 exit /b 1
"%TASK_PYTHON%" -m pytest -q
if errorlevel 1 exit /b 1
"%TASK_PYTHON%" scripts\make_icon.py
if errorlevel 1 exit /b 1
"%TASK_PYTHON%" -m PyInstaller --noconfirm --clean ClashSmartSwitcher.spec
if errorlevel 1 exit /b 1
"%TASK_PYTHON%" scripts\package_release.py
if errorlevel 1 exit /b 1
echo Build complete: dist\ClashSmartSwitcher-1.1.0-windows-x64.zip
