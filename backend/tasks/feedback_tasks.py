"""
Feedback Tasks - Background tasks for feedback analysis and learning

Contains tasks for:
- Daily feedback analysis
- Operator statistics updates
- Learning from successful alphas
"""

from sqlalchemy import select
from loguru import logger

from backend.celery_app import celery_app
from backend.database import AsyncSessionLocal
from backend.agents import FeedbackAgent
from backend.tasks import run_async


@celery_app.task(name="backend.tasks.run_daily_feedback")
def run_daily_feedback():
    """
    Run daily feedback analysis (scheduled).
    
    Analyzes recent alpha failures and successes to update
    the knowledge base.
    """
    logger.info("Running daily feedback analysis...")
    
    async def _run():
        async with AsyncSessionLocal() as db:
            feedback_agent = FeedbackAgent(db)
            result = await feedback_agent.run_daily_feedback()
            logger.info(f"Feedback analysis complete: {result}")
            return result
    
    return run_async(_run())


@celery_app.task(name="backend.tasks.update_operator_stats")
def update_operator_stats():
    """
    Update operator usage statistics (scheduled).
    
    Analyzes operator usage patterns and updates success rates.
    """
    logger.info("Updating operator stats...")
    
    async def _run():
        async with AsyncSessionLocal() as db:
            feedback_agent = FeedbackAgent(db)
            result = await feedback_agent.update_operator_stats()
            logger.info(f"Operator stats updated: {len(result)} operators")
            return {"operators_updated": len(result)}
    
    return run_async(_run())


@celery_app.task(name="backend.tasks.learn_from_alpha")
def learn_from_alpha(alpha_id: int):
    """
    Learn from a successful/liked alpha.
    
    Extracts patterns from a successful alpha and adds them
    to the knowledge base.
    
    Args:
        alpha_id: The alpha ID to learn from
    """
    logger.info(f"Learning from alpha {alpha_id}...")
    
    async def _run():
        async with AsyncSessionLocal() as db:
            from backend.models import Alpha
            
            query = select(Alpha).where(Alpha.id == alpha_id)
            result = await db.execute(query)
            alpha = result.scalar_one_or_none()
            
            if not alpha:
                return {"error": "Alpha not found"}
            
            feedback_agent = FeedbackAgent(db)
            result = await feedback_agent.learn_from_success(alpha)
            return result
    
    return run_async(_run())
