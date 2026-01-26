# 1. 配置环境
cp .env.example .env
# 编辑 .env 填入凭证

# 2. 安装依赖
pip install -r requirements.txt
cd frontend && npm install

# 3. 初始化数据库
psql -U postgres -c "CREATE DATABASE alpha_gpt;"
psql -U postgres -d alpha_gpt -f backend/migrations/001_initial_schema.sql

# 4. 启动
uvicorn backend.main:app --reload  # 后端
cd frontend && npm run dev          # 前端


celery -A backend.celery_app worker --loglevel=info