import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db

logger = logging.getLogger("services")

class BaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def commit(self):
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Database commit failed: {e}")
            raise
