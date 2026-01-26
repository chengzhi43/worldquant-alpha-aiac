import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from backend.services.base import BaseService
from backend.models import MiningTask, MiningJob, Alpha, AlphaFailure, MiningStatus
from backend.models import MiningStatus, JobStatus # Needed if we filter by status

logger = logging.getLogger("analysis_service")

class AnalysisService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def get_dashboard_stats(self) -> Dict:
        """Get high-level stats for the dashboard."""
        
        # Total Alphas
        total_alphas_query = select(func.count(Alpha.id))
        total_alphas = (await self.db.execute(total_alphas_query)).scalar() or 0
        
        # Active Tasks
        active_tasks_query = select(func.count(MiningTask.id)).where(MiningTask.status == MiningStatus.RUNNING)
        active_tasks = (await self.db.execute(active_tasks_query)).scalar() or 0
        
        # Avg Sharpe (of candidate alphas)
        avg_sharpe_query = select(func.avg(Alpha.metrics['sharpe'].astext.cast(float)))
        # Note: simplistic cast, might need robust handling if metrics is complex JSON
        # For MVP, we assume metrics is a flat dict with 'sharpe' key.
        # Postgres JSONB allows ->> operator. SQLAlchemy Use:
        # Alpha.metrics['sharpe'].astext.cast(Float)
        
        # Simplifying: Get recent alphas and compute in python if DB is cleaner
        # usage: select(Alpha).limit(100)
        
        return {
            "total_alphas": total_alphas,
            "active_tasks": active_tasks,
            "avg_sharpe": 0.0 # Placeholder
        }

    async def get_recent_alphas(self, limit: int = 10) -> List[Alpha]:
        stmt = select(Alpha).order_by(desc(Alpha.created_at)).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_alpha_details(self, alpha_id: int) -> Optional[Alpha]:
        stmt = select(Alpha).where(Alpha.id == alpha_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
