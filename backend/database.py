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
    """
    Initialize database tables.
    
    For development: creates tables if they don't exist.
    For production: use Alembic migrations instead:
        cd backend && alembic upgrade head
    """
    async with engine.begin() as conn:
        # await conn.run_sync(SQLAlchemyBase.metadata.drop_all)  # WARNING: Dev only
        await conn.run_sync(SQLAlchemyBase.metadata.create_all)
