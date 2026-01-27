"""
Dashboard Router - Stats and live feed for the control center
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import json

from backend.database import get_db
from backend.models import MiningTask, Alpha, TraceStep, AlphaFailure

router = APIRouter(
    prefix="/stats",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

from pydantic import BaseModel
from typing import List


class DailyStatsResponse(BaseModel):
    date: str
    goal: int
    current: int
    success_rate: float
    avg_sharpe: float
    total_simulations: int
    total_failures: int


class TaskStatusSummary(BaseModel):
    id: int
    task_name: str
    region: str
    status: str
    progress: str  # "2/4"
    current_step: Optional[str] = None
    current_dataset: Optional[str] = None


class KPIMetrics(BaseModel):
    today_simulations: int
    today_success_rate: float
    today_avg_sharpe: float
    week_total_alphas: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/daily", response_model=DailyStatsResponse)
async def get_daily_stats(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily mining statistics for the dashboard.
    """
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = datetime.now().date()
    
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)
    
    # Get today's tasks
    tasks_query = select(MiningTask).where(
        MiningTask.created_at >= start_of_day,
        MiningTask.created_at < end_of_day
    )
    tasks_result = await db.execute(tasks_query)
    tasks = tasks_result.scalars().all()
    
    total_goal = sum(t.daily_goal for t in tasks) if tasks else 4
    total_current = sum(t.progress_current for t in tasks) if tasks else 0
    
    # Get today's alphas
    alphas_query = select(Alpha).where(
        Alpha.created_at >= start_of_day,
        Alpha.created_at < end_of_day,
        Alpha.quality_status == "PASS"
    )
    alphas_result = await db.execute(alphas_query)
    alphas = alphas_result.scalars().all()
    
    # Calculate metrics
    total_sims_query = select(func.count(Alpha.id)).where(
        Alpha.created_at >= start_of_day,
        Alpha.created_at < end_of_day
    )
    total_sims = (await db.execute(total_sims_query)).scalar() or 0
    
    failures_query = select(func.count(AlphaFailure.id)).where(
        AlphaFailure.created_at >= start_of_day,
        AlphaFailure.created_at < end_of_day
    )
    total_failures = (await db.execute(failures_query)).scalar() or 0
    
    success_rate = len(alphas) / total_sims if total_sims > 0 else 0.0
    
    # Average Sharpe of passed alphas
    avg_sharpe = 0.0
    if alphas:
        sharpes = [
            (a.metrics.get("sharpe") if a.metrics.get("sharpe") is not None else a.metrics.get("is_sharpe", 0))
            for a in alphas
            if a.metrics
        ]
        avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0.0
    
    return DailyStatsResponse(
        date=target_date.isoformat(),
        goal=total_goal,
        current=total_current,
        success_rate=round(success_rate, 4),
        avg_sharpe=round(avg_sharpe, 2),
        total_simulations=total_sims,
        total_failures=total_failures
    )


@router.get("/active-tasks", response_model=List[TaskStatusSummary])
async def get_active_tasks(db: AsyncSession = Depends(get_db)):
    """
    Get currently active mining tasks.
    """
    query = select(MiningTask).where(
        MiningTask.status.in_(["RUNNING", "PAUSED"])
    ).order_by(MiningTask.created_at.desc())
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    summaries = []
    for task in tasks:
        # Get the latest trace step
        step_query = select(TraceStep).where(
            TraceStep.task_id == task.id
        ).order_by(TraceStep.step_order.desc()).limit(1)
        step_result = await db.execute(step_query)
        latest_step = step_result.scalar_one_or_none()
        
        summaries.append(TaskStatusSummary(
            id=task.id,
            task_name=task.task_name,
            region=task.region,
            status=task.status,
            progress=f"{task.progress_current}/{task.daily_goal}",
            current_step=latest_step.step_type if latest_step else None,
            current_dataset=latest_step.input_data.get("dataset_id") if latest_step and latest_step.input_data else None
        ))
    
    return summaries


@router.get("/kpi", response_model=KPIMetrics)
async def get_kpi_metrics(db: AsyncSession = Depends(get_db)):
    """
    Get key performance indicators for dashboard cards.
    """
    today = datetime.now().date()
    start_of_today = datetime.combine(today, datetime.min.time())
    start_of_week = start_of_today - timedelta(days=today.weekday())
    
    # Today's simulations
    today_sims_query = select(func.count(Alpha.id)).where(
        Alpha.created_at >= start_of_today
    )
    today_sims = (await db.execute(today_sims_query)).scalar() or 0
    
    # Today's passed alphas
    today_passed_query = select(func.count(Alpha.id)).where(
        Alpha.created_at >= start_of_today,
        Alpha.quality_status == "PASS"
    )
    today_passed = (await db.execute(today_passed_query)).scalar() or 0
    
    success_rate = today_passed / today_sims if today_sims > 0 else 0.0
    
    # Today's average Sharpe
    today_sharpe_query = select(Alpha).where(
        Alpha.created_at >= start_of_today,
        Alpha.quality_status == "PASS"
    )
    today_alphas = (await db.execute(today_sharpe_query)).scalars().all()
    
    avg_sharpe = 0.0
    if today_alphas:
        sharpes = [a.metrics.get("sharpe", 0) for a in today_alphas if a.metrics]
        avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0.0
    
    # Week's total alphas
    week_total_query = select(func.count(Alpha.id)).where(
        Alpha.created_at >= start_of_week,
        Alpha.quality_status == "PASS"
    )
    week_total = (await db.execute(week_total_query)).scalar() or 0
    
    return KPIMetrics(
        today_simulations=today_sims,
        today_success_rate=round(success_rate, 4),
        today_avg_sharpe=round(avg_sharpe, 2),
        week_total_alphas=week_total
    )


@router.get("/live-feed")
async def live_feed(db: AsyncSession = Depends(get_db)):
    """
    Server-Sent Events endpoint for live activity feed.
    Returns the latest trace steps and alpha events.
    """
    async def event_generator():
        last_id = 0
        while True:
            # Fetch new trace steps since last check
            query = select(TraceStep).where(
                TraceStep.id > last_id
            ).order_by(TraceStep.created_at.desc()).limit(10)
            
            async with db.begin():
                result = await db.execute(query)
                steps = result.scalars().all()
            
            for step in reversed(steps):  # Oldest first
                last_id = max(last_id, step.id)
                event_data = {
                    "type": "trace_step",
                    "task_id": step.task_id,
                    "step_type": step.step_type,
                    "status": step.status,
                    "timestamp": step.created_at.isoformat() if step.created_at else None,
                    "message": _format_step_message(step)
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            await asyncio.sleep(2)  # Poll every 2 seconds
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


def _format_step_message(step: TraceStep) -> str:
    """Format a trace step into a human-readable message."""
    messages = {
        "RAG_QUERY": f"Mining Agent 检索知识库...",
        "HYPOTHESIS": f"Mining Agent 生成假设...",
        "CODE_GEN": f"Mining Agent 生成 Alpha 表达式...",
        "VALIDATE": f"静态校验表达式...",
        "SIMULATE": f"提交 BRAIN 模拟...",
        "SELF_CORRECT": f"自我修正错误表达式...",
        "EVALUATE": f"Analysis Agent 评估质量..."
    }
    
    base_msg = messages.get(step.step_type, f"执行步骤: {step.step_type}")
    
    if step.status == "SUCCESS":
        return f"✅ {base_msg} 完成"
    elif step.status == "FAILED":
        return f"❌ {base_msg} 失败"
    else:
        return f"⏳ {base_msg}"
