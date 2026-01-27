from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

from sqlalchemy.pool import NullPool

SQLAlchemyBase = declarative_base()

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False, # Set to False in production
    future=True,
    poolclass=NullPool
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(SQLAlchemyBase.metadata.drop_all) # WARNING: Dev only
        await conn.run_sync(SQLAlchemyBase.metadata.create_all)

        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS experiment_runs (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL REFERENCES mining_tasks(id),
                status VARCHAR(50) DEFAULT 'RUNNING',
                trigger_source VARCHAR(50) DEFAULT 'API',
                celery_task_id VARCHAR(100),
                config_snapshot JSONB DEFAULT '{}'::jsonb,
                prompt_version VARCHAR(100),
                thresholds_version VARCHAR(100),
                strategy_snapshot JSONB DEFAULT '{}'::jsonb,
                started_at TIMESTAMP DEFAULT NOW(),
                finished_at TIMESTAMP,
                error_message TEXT
            );
            """,
            "ALTER TABLE trace_steps ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES experiment_runs(id);",
            "ALTER TABLE alphas ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES experiment_runs(id);",
            "ALTER TABLE alpha_failures ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES experiment_runs(id);",
        ]

        for stmt in ddl_statements:
            try:
                await conn.exec_driver_sql(stmt)
            except Exception:
                continue
