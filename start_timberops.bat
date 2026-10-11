@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

rem TimberOps v1.0.0 one-click local development launcher.
rem Put this file in the TimberOps repository root and double-click it.

cd /d "%~dp0"
set "ROOT=%CD%"

echo ==================================================
echo   TimberOps v1.0.0 - One-click Start
echo ==================================================
echo.

rem Check .env
if not exist "%ROOT%\.env" (
    echo [ERROR] .env not found.
    echo Copying .env.example to .env ...
    copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo.
    echo Please edit .env first, especially:
    echo   POSTGRES_PASSWORD
    echo   DATABASE_URL
    echo   DATABASE_URL_DOCKER
    echo   JWT_SECRET_KEY
    echo.
    pause
    exit /b 1
)

rem Check Docker Engine
echo [1/5] Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Engine is not running. Trying to start Docker Desktop...

    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo [ERROR] Docker Desktop was not found.
        echo Please start Docker Desktop manually and run this script again.
        pause
        exit /b 1
    )

    call :WAIT_DOCKER
    if errorlevel 1 (
        echo [ERROR] Docker Engine did not become ready within 120 seconds.
        echo Please check Docker Desktop, then run this script again.
        pause
        exit /b 1
    )
)

echo Docker is ready.

rem Start PostgreSQL
echo.
echo [2/5] Starting PostgreSQL...
docker compose up -d db
if errorlevel 1 (
    echo [ERROR] Failed to start PostgreSQL.
    pause
    exit /b 1
)

call :WAIT_DB
if errorlevel 1 (
    echo [WARN] PostgreSQL did not report healthy within 60 seconds.
    echo Backend will still be started so you can inspect the error.
) else (
    echo PostgreSQL is ready.
)

rem Check backend virtual environment
echo.
echo [3/5] Checking backend environment...
if not exist "%ROOT%\backend\.venv\Scripts\python.exe" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found in PATH.
        pause
        exit /b 1
    )

    echo Backend virtual environment not found. Creating it...
    cd /d "%ROOT%\backend"
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create Python virtual environment.
        pause
        exit /b 1
    )

    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
    cd /d "%ROOT%"
)

rem Check frontend dependencies
echo.
echo [4/5] Checking frontend environment...
if not exist "%ROOT%\frontend\node_modules" (
    where npm >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] npm was not found in PATH.
        pause
        exit /b 1
    )

    echo Frontend dependencies not found. Running npm install...
    cd /d "%ROOT%\frontend"
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
    cd /d "%ROOT%"
)

rem Start backend and frontend in separate windows
echo.
echo [5/5] Starting TimberOps services...

start "TimberOps Backend" cmd /k "cd /d ""%ROOT%\backend"" && call .venv\Scripts\activate.bat && python -m alembic upgrade head && python -m uvicorn app.main:app --reload"

timeout /t 2 /nobreak >nul

start "TimberOps Frontend" cmd /k "cd /d ""%ROOT%\frontend"" && npm run dev"

echo.
echo ==================================================
echo TimberOps is starting.
echo.
echo Frontend: http://localhost:5173
echo Backend : http://127.0.0.1:8000
echo Health  : http://127.0.0.1:8000/health
echo Ready   : http://127.0.0.1:8000/ready
echo ==================================================
echo.

echo Opening browser in a few seconds...
timeout /t 5 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo Keep the Backend and Frontend windows open while using TimberOps.
echo You may close this launcher window.
echo.
pause
exit /b 0


:WAIT_DOCKER
echo Waiting for Docker Engine...
for /L %%I in (1,1,40) do (
    docker info >nul 2>&1
    if not errorlevel 1 exit /b 0
    timeout /t 3 /nobreak >nul
)
exit /b 1


:WAIT_DB
set "DB_CONTAINER="
for /f "delims=" %%C in ('docker compose ps -q db 2^>nul') do set "DB_CONTAINER=%%C"

if not defined DB_CONTAINER exit /b 1

for /L %%I in (1,1,30) do (
    set "DB_HEALTH="
    for /f "delims=" %%H in ('docker inspect --format="{{.State.Health.Status}}" !DB_CONTAINER! 2^>nul') do set "DB_HEALTH=%%H"
    if /I "!DB_HEALTH!"=="healthy" exit /b 0
    timeout /t 2 /nobreak >nul
)
exit /b 1
