@echo off
:: Navigate to the correct directory
cd /d "C:\Temp_data\automate_N"

:: Activate the virtual environment
call venv\Scripts\activate

:: Run the automation script
python naukri_automation.py

:: Pause at the end so you can see output/errors if the script exits
pause
