@echo off
echo ========================================
echo SCRIBE - AI Trends Package
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Clean previous raw logs
if exist "data\ai_trends\raw_logs\" (
    echo Cleaning previous raw logs...
    del /Q "data\ai_trends\raw_logs\*.md" 2>nul
    echo.
)

echo ========================================
echo Running SCRIBE - AI Trends Package...
echo ========================================
echo.

REM Run the program with ai_trends package
python main.py --package ai_trends --mode once

echo.
echo ========================================
echo Done!
echo ========================================
