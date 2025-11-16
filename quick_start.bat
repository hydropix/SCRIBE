@echo off
echo ========================================
echo VeilleAuto - Demarrage rapide
echo ========================================
echo.

REM Verifier si l'environnement virtuel existe
if not exist "venv\" (
    echo Creation de l'environnement virtuel...
    python -m venv venv
    echo.
)

REM Activer l'environnement virtuel
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Installer les dependances si necessaire
if not exist "venv\Lib\site-packages\praw\" (
    echo Installation des dependances...
    pip install -r requirements.txt
    echo.
)

REM Verifier si .env existe
if not exist ".env" (
    echo ATTENTION: Fichier .env non trouve!
    echo Veuillez copier .env.example vers .env et le remplir avec vos credentials.
    echo.
    pause
    exit /b 1
)

REM Supprimer les logs de donnees brutes precedents
if exist "data\raw_logs\" (
    echo Nettoyage des logs de donnees brutes precedents...
    del /Q "data\raw_logs\*.md" 2>nul
    echo.
)

echo ========================================
echo Lancement de VeilleAuto...
echo ========================================
echo.

REM Executer le programme
python main.py --mode once

echo.
echo ========================================
echo Termine!
echo ========================================
