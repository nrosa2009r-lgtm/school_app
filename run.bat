@echo off
REM ============================================================
REM  School Catering Application - Launcher (Windows)
REM  Automatyczne pobieranie, instalacja i start w 2 oknach.
REM  Wersja: 2.0 Enterprise
REM ============================================================
setlocal enabledelayedexpansion

echo.
echo  =======================================================
echo    SCHOOL CATERING APPLICATION v2.0 - ENTERPRISE
echo    Uruchamianie serwera...
echo  =======================================================
echo.

REM Sprawdz czy Python jest dostepny
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [BLAD] Python nie jest zainstalowany lub nie jest w PATH.
    echo Pobierz Python 3.10+ z https://python.org i uruchom ponownie.
    pause
    exit /b 1
)

REM Sprawdz czy venv istnieje, jesli nie - utworz
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Tworzenie srodowiska wirtualnego Python...
    python -m venv venv
    echo [OK] Srodowisko utworzone.
)

REM Aktywuj venv i zainstaluj zaleznosci
call venv\Scripts\activate.bat

echo [INFO] Sprawdzanie zaleznosci...
pip install -r requirements.txt --quiet 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Instalacja zaleznosci...
    pip install fastapi uvicorn pydantic pydantic-settings email-validator sqlalchemy aiosqlite flet cryptography bcrypt pyjwt slowapi fastapi-mail httpx pytest pytest-asyncio python-multipart qrcode pillow python-dotenv --quiet
)

echo.
echo [OK] Zaleznosci zainstalowane. Uruchamianie aplikacji...
echo.

REM Uruchom main.py (inicjalizacja bazy) najpierw
python main.py --init-only 2>nul

REM Sprawdz czy jest flaga --setup lub --check-or-setup
if "%1"=="--setup" goto :setup_mode
if "%1"=="--check-or-setup" goto :check_setup_mode

REM Normalny start: FastAPI w jednym oknie, Flet UI w drugim
echo [INFO] Startowanie FastAPI (backend)...
start "School Catering - API Server" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [INFO] Startowanie Flet UI (frontend)...
start "School Catering - UI Client" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && venv\Scripts\flet.exe run ui\front.py"

echo.
echo [OK] Aplikacja uruchomiona!
echo    API:  http://localhost:8000
echo    Docs: http://localhost:8000/docs
echo    UI:   drugie okno (Flet)
echo.
echo    Aby zatrzymac, zamknij oba okna terminala.
goto :end

:setup_mode
echo [SETUP] Uruchamianie kreatora konfiguracji krok po kroku...
python main.py --setup
goto :end

:check_setup_mode
echo [CHECK] Sprawdzanie czy konfiguracja jest juz ukonczona...
python main.py --check-or-setup
if %ERRORLEVEL% EQU 0 (
    echo [OK] Konfiguracja ukonczona. Przechodze do normalnego startu...
    goto :normal_start
) else (
    echo [INFO] Konfiguracja nieukonczona. Uruchamiam kreator...
    goto :setup_mode
)

:normal_start
goto :normal_start_impl

:normal_start_impl
echo [INFO] Startowanie FastAPI...
start "School Catering - API Server" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak >nul
echo [INFO] Startowanie Flet UI...
start "School Catering - UI Client" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && venv\Scripts\flet.exe run ui\front.py"
echo [OK] Aplikacja uruchomiona!

:end
endlocal
