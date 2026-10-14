@echo off
cd /d "%~dp0"
set "TASK_PYTHON=%~dp0.conda\clash-smart-switcher\python.exe"
if not exist "%TASK_PYTHON%" set "TASK_PYTHON=python"
"%TASK_PYTHON%" main.py
