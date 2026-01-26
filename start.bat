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

REM 3. Database Init
set /p init_db="Initialize Database? (y/n) [n]: "
if /i "%init_db%"=="y" (
    echo [INFO] initializing database...
    echo [NOTE] Make sure PostgreSQL is running and password is set in .env or PGPASSWORD env var.
    psql -U postgres -c "CREATE DATABASE alpha_gpt;"
    psql -U postgres -d alpha_gpt -f backend/migrations/001_initial_schema.sql
)

REM 4. Start Server
set /p port="Enter Backend Port (default 8001): "
if "%port%"=="" set port=8001

echo [INFO] Starting Backend on port %port%...
start "AIAC Backend" cmd /k "uvicorn backend.main:app --reload --port %port%"

celery -A backend.celery_app worker --loglevel=info --pool=solo

echo [INFO] Starting Frontend...
cd frontend
start "AIAC Frontend" cmd /k "npm run dev"
cd ..

echo [SUCCESS] Services started!
echo Backend: http://localhost:%port%
echo Frontend: http://localhost:5174
echo.
pause
