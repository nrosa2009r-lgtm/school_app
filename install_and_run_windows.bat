@echo off
REM ============================================================
REM  School Catering Application - Installer & First Run
REM  Pobiera repozytorium z GitHub i uruchamia aplikacje.
REM  Wersja: 2.0 Enterprise
REM ============================================================
setlocal enabledelayedexpansion

echo.
echo  =======================================================
echo    SCHOOL CATERING APP - INSTALATOR ENTERPRISE
echo    Pobieranie z GitHub i pierwsze uruchomienie
echo  =======================================================
echo.

REM Sprawdz czy git jest dostepny
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [BLAD] Git nie jest zainstalowany. Pobierz z https://git-scm.com/
    pause
    exit /b 1
)

REM Sprawdz czy Python jest dostepny
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [BLAD] Python nie jest zainstalowany.
    echo Pobierz Python 3.10+ z https://python.org i uruchom ponownie.
    pause
    exit /b 1
)

set REPO_URL=https://github.com/nrosa2009r-lgtm/school_app.git
set APP_DIR=%USERPROFILE%\school_app

echo [1/4] Pobieranie repozytorium...
if exist "%APP_DIR%" (
    echo [INFO] Katalog juz istnieje. Aktualizowanie...
    cd /d "%APP_DIR%"
    git pull origin main
) else (
    git clone %REPO_URL% "%APP_DIR%"
    cd /d "%APP_DIR%"
)

echo.
echo [2/4] Tworzenie srodowiska wirtualnego...
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo [3/4] Instalacja zaleznosci Python...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Instalacja z uzyciem alternatywnej metody...
    pip install fastapi uvicorn pydantic pydantic-settings email-validator sqlalchemy aiosqlite flet cryptography bcrypt pyjwt slowapi fastapi-mail httpx pytest pytest-asyncio python-multipart qrcode pillow python-dotenv
)

echo.
echo [4/4] Uruchamianie kreatora pierwszego uruchomienia...
echo.
python main.py --check-or-setup

echo.
echo [OK] Instalacja zakonczona!
echo Uruchamiam aplikacje...
echo.

REM Uruchom aplikacje
call run.bat

endlocal
