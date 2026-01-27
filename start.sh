#!/bin/bash

echo "=========================================="
echo "       AIAC 2.0 Alpha-GPT Startup"
echo "=========================================="

# 1. Config Environment
if [ ! -f ".env" ]; then
    echo "[INFO] .env not found. Creating from .env.example..."
    cp .env.example .env
    echo "[IMPORTANT] Please edit .env file to configure your credentials!"
    read -p "Press Enter to continue after editing .env..."
fi

# 2. Install Dependencies
read -p "Install dependencies? (y/n) [n]: " install_deps
if [ "$install_deps" = "y" ] || [ "$install_deps" = "Y" ]; then
    echo "[INFO] Installing backend dependencies..."
    pip install -r requirements.txt
    
    echo "[INFO] Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# 3. Database Setup (optional - tables are auto-created on app start)
read -p "Create database if not exists? (y/n) [n]: " init_db
if [ "$init_db" = "y" ] || [ "$init_db" = "Y" ]; then
    echo "[INFO] Creating database if not exists..."
    echo "[NOTE] Make sure PostgreSQL is running and credentials are set in .env file."
    python backend/migrations/init_database.py
fi

# 4. Start Server
read -p "Enter Backend Port (default 8001): " port
if [ -z "$port" ]; then
    port=8001
fi

echo "[INFO] Starting Backend on port $port..."
uvicorn backend.main:app --reload --port $port &
BACKEND_PID=$!

echo "[INFO] Starting Frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo "[INFO] Starting Celery Worker..."
celery -A backend.celery_app worker --loglevel=info &
CELERY_PID=$!

echo ""
echo "[SUCCESS] Services started!"
echo "Backend: http://localhost:$port"
echo "Frontend: http://localhost:5174"
echo ""
echo "[NOTE] Tables will be auto-created by SQLAlchemy on first request."
echo "Press Ctrl+C to stop all services..."

# Handle graceful shutdown
trap "kill $BACKEND_PID $FRONTEND_PID $CELERY_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for any process to exit
wait
