@echo off
title J.A.R.V.I.S. PC Control & Security Guard
color 0b

echo ====================================================
echo      J.A.R.V.I.S. INITIALIZATION SEQUENCE          
echo ====================================================
echo.

:: Check python
python --version >copy_test.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.8+ and add it to PATH.
    del copy_test.txt >nul 2>&1
    pause
    exit /b 1
)
del copy_test.txt >nul 2>&1

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies failed to install. We will attempt to run anyway.
)
echo.

:: Check if face model exists
if not exist model\trainer.yml (
    echo [ALERT] No face recognition model detected.
    echo Running face setup registration utility first...
    echo.
    python setup_face.py
    if not exist model\trainer.yml (
        echo [ERROR] Face registration failed or cancelled.
        echo J.A.R.V.I.S. cannot run without a registered owner's face.
        pause
        exit /b 1
    )
)

echo.
echo Starting J.A.R.V.I.S. Core Hub...
start "" http://127.0.0.1:5000
python app.py

pause
