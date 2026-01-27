#!/bin/bash

echo "=========================================="
echo "       AIAC 2.0 Alpha-GPT Startup"
echo "=========================================="

# 1. Config Environment
if [ ! -f ".env" ]; then
    echo "[INFO] .env not found. Creating from .env.example..."
    cp .env.example .env
    echo "[IMPORTANT] Please edit .env file to configure your credentials!"
    ${EDITOR:-nano} .env
fi

# 2. Auto-detect and install dependencies if needed
if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Creating..."
    python3 -m venv venv
fi

source venv/bin/activate

# Check if key packages are installed
if ! pip show fastapi > /dev/null 2>&1; then
    echo "[INFO] Installing backend dependencies..."
    pip install -r requirements.txt
else
    echo "[OK] Backend dependencies already installed."
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    cd frontend && npm install && cd ..
else
    echo "[OK] Frontend dependencies already installed."
fi

# 3. Auto-detect database
echo "[INFO] Checking database connection..."
python3 -c "
from backend.config import settings
import psycopg2
try:
    conn = psycopg2.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database='postgres'
    )
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM pg_database WHERE datname=%s', (settings.POSTGRES_DB,))
    exists = cur.fetchone()
    conn.close()
    exit(0 if exists else 1)
except:
    exit(1)
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "[INFO] Database not found or connection failed. Attempting to create..."
    python backend/migrations/init_database.py
else
    echo "[OK] Database connection verified."
fi

# 4. Start Services
PORT=8001

echo ""
echo "[INFO] Starting services..."
echo ""

echo "[INFO] Starting Backend on port $PORT..."
uvicorn backend.main:app --reload --port $PORT &
BACKEND_PID=$!

echo "[INFO] Starting Frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo "[INFO] Starting Celery Worker..."
celery -A backend.celery_app worker --loglevel=info &
CELERY_PID=$!

echo ""
echo "=========================================="
echo "            Services Started!"
echo "=========================================="
echo ""
echo "  Backend:  http://localhost:$PORT"
echo "  API Docs: http://localhost:$PORT/docs"
echo "  Frontend: http://localhost:5174"
echo ""
echo "  Press Ctrl+C to stop all services..."
echo "=========================================="

# Handle graceful shutdown
trap "echo ''; echo '[INFO] Stopping services...'; kill $BACKEND_PID $FRONTEND_PID $CELERY_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for any process to exit
wait
