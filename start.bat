@echo off
setlocal

echo ==========================================
echo       AIAC 2.0 Alpha-GPT Startup
echo ==========================================

REM 1. Config Environment
if not exist ".env" (
    echo [INFO] .env not found. Creating from .env.example...
    copy .env.example .env
    echo [IMPORTANT] Please edit .env file to configure your credentials!
    pause
)

REM 2. Install Dependencies
set /p install_deps="Install dependencies? (y/n) [n]: "
if /i "%install_deps%"=="y" (
    echo [INFO] Installing backend dependencies...
    pip install -r requirements.txt
    
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM 3. Database Setup (optional - tables are auto-created on app start)
set /p init_db="Create database if not exists? (y/n) [n]: "
if /i "%init_db%"=="y" (
    echo [INFO] Creating database if not exists...
    echo [NOTE] Make sure PostgreSQL is running and credentials are set in .env file.
    python backend/migrations/init_database.py
)
:skip_init

REM 4. Start Server
set /p port="Enter Backend Port (default 8001): "
if "%port%"=="" set port=8001

echo [INFO] Starting Backend on port %port%...
start "AIAC Backend" cmd /k "uvicorn backend.main:app --reload --port %port%"

echo [INFO] Starting Frontend...
cd frontend
start "AIAC Frontend" cmd /k "npm run dev"
cd ..

echo [SUCCESS] Services started!
echo Backend: http://localhost:%port%
echo Frontend: http://localhost:5174
echo.

echo [INFO] Starting Celery Worker...
start "AIAC Celery Worker" cmd /k "celery -A backend.celery_app worker --loglevel=info --pool=solo"
pause
