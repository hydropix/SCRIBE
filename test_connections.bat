@echo off
title SCRIBE - Configuration Test

echo.
echo ============================================================
echo   SCRIBE - Configuration and Connection Test
echo ============================================================
echo.

REM Check if venv folder exists
if not exist "venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found.
    echo     Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [-] Error creating venv
        goto :end
    )
    if not exist "venv\Scripts\activate.bat" (
        echo [-] Failed to create virtual environment
        goto :end
    )
    echo [+] Virtual environment created.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [-] Error activating venv
    goto :end
)
echo [+] Virtual environment activated.
echo.

REM Check if all required dependencies are installed
echo Checking dependencies...
set "MISSING_DEPS=0"

REM Check core dependencies
pip show python-dotenv >nul 2>&1 || set "MISSING_DEPS=1"
pip show praw >nul 2>&1 || set "MISSING_DEPS=1"
pip show scikit-learn >nul 2>&1 || set "MISSING_DEPS=1"
pip show google-api-python-client >nul 2>&1 || set "MISSING_DEPS=1"
pip show ollama >nul 2>&1 || set "MISSING_DEPS=1"

if "%MISSING_DEPS%"=="1" (
    echo [!] Missing dependencies detected. Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [-] Error installing dependencies
        goto :end
    )
    echo [+] Dependencies installed.
    echo.
) else (
    echo [+] All dependencies are installed.
    echo.
)

REM Run the test script
echo Running configuration tests...
echo.
python tests/test_connections.py

:end
echo.
echo ============================================================
echo   Test completed - Press any key to close
echo ============================================================
pause >nul
