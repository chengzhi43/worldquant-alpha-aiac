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
    notepad .env
    pause
)

REM 2. Auto-detect and install dependencies if needed
if not exist "venv" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
)

call venv\Scripts\activate

REM Check if key packages are installed
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing backend dependencies...
    pip install -r requirements.txt
) else (
    echo [OK] Backend dependencies already installed.
)

if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
) else (
    echo [OK] Frontend dependencies already installed.
)

REM 3. Auto-detect database
echo [INFO] Checking database connection...
python -c "from backend.config import settings; import psycopg2; conn = psycopg2.connect(host=settings.POSTGRES_SERVER, port=settings.POSTGRES_PORT, user=settings.POSTGRES_USER, password=settings.POSTGRES_PASSWORD, database='postgres'); cur = conn.cursor(); cur.execute('SELECT 1 FROM pg_database WHERE datname=%s', (settings.POSTGRES_DB,)); exists = cur.fetchone(); conn.close(); exit(0 if exists else 1)" 2>nul
if errorlevel 1 (
    echo [INFO] Database not found or connection failed. Attempting to create...
    python backend/migrations/init_database.py
) else (
    echo [OK] Database connection verified.
)

REM 4. Start Services
set port=8001

echo.
echo [INFO] Starting services...
echo.

echo [INFO] Starting Backend on port %port%...
start "AIAC Backend" cmd /k "call venv\Scripts\activate && uvicorn backend.main:app --reload --port %port%"

echo [INFO] Starting Frontend...
cd frontend
start "AIAC Frontend" cmd /k "npm run dev"
cd ..

echo [INFO] Starting Celery Worker...
start "AIAC Celery Worker" cmd /k "call venv\Scripts\activate && celery -A backend.celery_app worker --loglevel=info --pool=solo"

echo.
echo ==========================================
echo             Services Started!
echo ==========================================
echo.
echo   Backend:  http://localhost:%port%
echo   API Docs: http://localhost:%port%/docs
echo   Frontend: http://localhost:5174
echo.
echo   Press any key to exit this window...
echo   (Services will continue running)
echo ==========================================
pause >nul
