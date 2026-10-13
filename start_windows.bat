@echo off
rem Double-click to launch uTesla Reader.
rem First run creates a local virtual environment in .venv and installs pyserial.
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto run

where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
if not exist ".venv\Scripts\python.exe" (
    echo Could not create a virtual environment. Install Python 3.9+ from https://www.python.org/downloads/windows/
    echo and tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt

:run
".venv\Scripts\python.exe" -m utesla_reader %*
if errorlevel 1 pause
