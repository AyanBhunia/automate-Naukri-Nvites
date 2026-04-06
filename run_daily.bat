@echo off
:: Get the directory where the batch file is located
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Activate the virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment 'venv' not found in %PROJECT_DIR%
    pause
    exit /b 1
)

:: Run the automation script
python naukri_automation.py

:: Pause at the end so you can see output/errors if the script exits
pause
