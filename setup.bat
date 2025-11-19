@echo off
echo ========================================
echo SCRIBE - Setup and Installation
echo ========================================
echo.

REM Update repository if it's a git repo
if exist ".git\" (
    echo Updating repository...
    git pull
    echo.
)

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\Lib\site-packages\praw\" (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

REM Check if .env exists
if not exist ".env" (
    if exist ".env.example" (
        echo .env file not found, copying .env.example...
        copy ".env.example" ".env"
        echo WARNING: Please edit the .env file with your credentials before running.
        echo.
        pause
    ) else (
        echo ERROR: .env and .env.example files not found!
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Setup complete! Running tests...
echo ========================================
echo.

REM Run configuration tests
python tests/test_connections.py

echo.
echo ========================================
echo You can now run: run_ai_trends.bat
echo ========================================
echo.
pause
