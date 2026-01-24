"""
Alphas Router - Alpha Lab functionality with feedback support
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import Alpha, TraceStep
from backend.tasks import sync_user_alphas

router = APIRouter(
    prefix="/alphas",
    tags=["alphas"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AlphaListItem(BaseModel):
    id: int
    alpha_id: Optional[str] = None
    type: Optional[str] = "REGULAR"
    name: Optional[str] = None
    expression: str
    region: Optional[str] = None
    dataset_id: Optional[str] = None
    quality_status: str
    human_feedback: str
    sharpe: Optional[float] = None
    returns: Optional[float] = None
    turnover: Optional[float] = None
    drawdown: Optional[float] = None
    margin: Optional[float] = None
    fitness: Optional[float] = None
    created_at: Optional[datetime] = None
    date_created: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlphaDetailResponse(BaseModel):
    id: int
    alpha_id: Optional[str] = None
    task_id: Optional[int] = None
    expression: str
    hypothesis: Optional[str] = None
    logic_explanation: Optional[str] = None
    
    # Metadata
    region: Optional[str] = None
    universe: Optional[str] = None
    dataset_id: Optional[str] = None
    fields_used: List[str] = []
    operators_used: List[str] = []
    
    # Status
    simulation_status: str
    quality_status: str
    diversity_status: str
    human_feedback: str
    feedback_comment: Optional[str] = None
    
    # Metrics
    metrics: dict = {}
    pnl_data: dict = {}
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeedbackRequest(BaseModel):
    rating: str  # LIKED or DISLIKED
    comment: Optional[str] = None


class SyncResponse(BaseModel):
    message: str
    task_id: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/sync", response_model=SyncResponse)
async def sync_alphas(background_tasks: BackgroundTasks = None):
    """
    Trigger background sync of ALL user alphas from Brain.
    Includes IS and OS stages, with full metadata.
    """
    task = sync_user_alphas.delay()
    return SyncResponse(
        message="Alpha sync started",
        task_id=str(task.id)
    )

class AlphaListResponse(BaseModel):
    items: List[AlphaListItem]
    total: int

@router.get("", response_model=AlphaListResponse)
async def list_alphas(
    region: Optional[str] = Query(None),
    quality_status: Optional[str] = Query(None),
    human_feedback: Optional[str] = Query(None),
    dataset_id: Optional[str] = Query(None),
    sort_by: str = Query("date_created", description="Field to sort by"),
    sort_order: str = Query("desc", description="asc or desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List alphas with filtering and sorting.
    """
    query = select(Alpha)
    
    # Apply filters
    if region:
        query = query.where(Alpha.region == region)
    if quality_status:
        query = query.where(Alpha.quality_status == quality_status)
    if human_feedback:
        query = query.where(Alpha.human_feedback == human_feedback)
    if dataset_id:
        query = query.where(Alpha.dataset_id == dataset_id)

    # Get total count (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply sorting
    sort_column = getattr(Alpha, sort_by, Alpha.date_created)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    alphas = result.scalars().all()
    
    items = [AlphaListItem(
        id=a.id,
        alpha_id=a.alpha_id,
        type=a.type,
        name=a.name,
        expression=(a.expression or "N/A")[:100] + "..." if len(a.expression or "N/A") > 100 else (a.expression or "N/A"),
        region=a.region,
        dataset_id=a.dataset_id,
        quality_status=a.quality_status,
        human_feedback=a.human_feedback,
        sharpe=a.is_sharpe,
        returns=a.is_returns,
        turnover=a.is_turnover,
        drawdown=a.is_drawdown,
        margin=a.is_metrics.get("margin") if a.is_metrics else None,
        fitness=a.is_fitness,
        created_at=a.date_created
    ) for a in alphas]

    return AlphaListResponse(items=items, total=total)


@router.get("/{alpha_id}", response_model=AlphaDetailResponse)
async def get_alpha(alpha_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get detailed information about an alpha, including PnL data for charting.
    """
    query = select(Alpha).where(Alpha.id == alpha_id)
    result = await db.execute(query)
    alpha = result.scalar_one_or_none()
    
    if not alpha:
        raise HTTPException(status_code=404, detail="Alpha not found")
    
    return AlphaDetailResponse(
        id=alpha.id,
        alpha_id=alpha.alpha_id,
        task_id=alpha.task_id,
        expression=alpha.expression,
        hypothesis=alpha.hypothesis,
        logic_explanation=alpha.logic_explanation,
        region=alpha.region,
        universe=alpha.universe,
        dataset_id=alpha.dataset_id,
        fields_used=alpha.fields_used or [],
        operators_used=alpha.operators_used or [],
        simulation_status=alpha.simulation_status,
        quality_status=alpha.quality_status,
        diversity_status=alpha.diversity_status,
        human_feedback=alpha.human_feedback,
        feedback_comment=alpha.feedback_comment,
        metrics=alpha.metrics or {},
        pnl_data=alpha.pnl_data or {},
        created_at=alpha.created_at
    )


@router.post("/{alpha_id}/feedback")
async def submit_feedback(
    alpha_id: int,
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit human feedback for an alpha (Human-in-the-Loop).
    This feedback is used by the Feedback Agent to improve future mining.
    """
    query = select(Alpha).where(Alpha.id == alpha_id)
    result = await db.execute(query)
    alpha = result.scalar_one_or_none()
    
    if not alpha:
        raise HTTPException(status_code=404, detail="Alpha not found")
    
    if request.rating not in ["LIKED", "DISLIKED"]:
        raise HTTPException(status_code=400, detail="Rating must be LIKED or DISLIKED")
    
    await db.execute(
        update(Alpha)
        .where(Alpha.id == alpha_id)
        .values(
            human_feedback=request.rating,
            feedback_comment=request.comment
        )
    )
    await db.commit()
    
    # TODO: Trigger Feedback Agent to learn from this feedback
    # - If LIKED: Extract pattern and add to SUCCESS_PATTERN
    # - If DISLIKED: Analyze reason and potentially add to FAILURE_PITFALL
    
    return {
        "message": "Feedback submitted",
        "alpha_id": alpha_id,
        "rating": request.rating
    }


@router.get("/{alpha_id}/trace", response_model=dict)
async def get_alpha_trace(alpha_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get the trace step that generated this alpha.
    Shows the full context: RAG query, hypothesis, code generation, etc.
    """
    query = select(Alpha).where(Alpha.id == alpha_id)
    result = await db.execute(query)
    alpha = result.scalar_one_or_none()
    
    if not alpha:
        raise HTTPException(status_code=404, detail="Alpha not found")
    
    if not alpha.trace_step_id:
        return {"message": "No trace step linked to this alpha"}
    
    # Get the trace step
    step_query = select(TraceStep).where(TraceStep.id == alpha.trace_step_id)
    step_result = await db.execute(step_query)
    step = step_result.scalar_one_or_none()
    
    if not step:
        return {"message": "Trace step not found"}
    
    # Get all related trace steps for context (same task, up to this step)
    context_query = select(TraceStep).where(
        TraceStep.task_id == step.task_id,
        TraceStep.step_order <= step.step_order
    ).order_by(TraceStep.step_order)
    
    context_result = await db.execute(context_query)
    context_steps = context_result.scalars().all()
    
    return {
        "alpha_id": alpha_id,
        "trace_step_id": step.id,
        "task_id": step.task_id,
        "context": [
            {
                "step_type": s.step_type,
                "step_order": s.step_order,
                "status": s.status,
                "input": s.input_data,
                "output": s.output_data,
                "duration_ms": s.duration_ms
            }
            for s in context_steps
        ]
    }


@router.get("/by-brain-id/{brain_alpha_id}", response_model=AlphaDetailResponse)
async def get_alpha_by_brain_id(brain_alpha_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get an alpha by its BRAIN platform ID.
    """
    query = select(Alpha).where(Alpha.alpha_id == brain_alpha_id)
    result = await db.execute(query)
    alpha = result.scalar_one_or_none()
    
    if not alpha:
        raise HTTPException(status_code=404, detail="Alpha not found")
    
    return AlphaDetailResponse(
        id=alpha.id,
        alpha_id=alpha.alpha_id,
        task_id=alpha.task_id,
        expression=alpha.expression,
        hypothesis=alpha.hypothesis,
        logic_explanation=alpha.logic_explanation,
        region=alpha.region,
        universe=alpha.universe,
        dataset_id=alpha.dataset_id,
        fields_used=alpha.fields_used or [],
        operators_used=alpha.operators_used or [],
        simulation_status=alpha.simulation_status,
        quality_status=alpha.quality_status,
        diversity_status=alpha.diversity_status,
        human_feedback=alpha.human_feedback,
        feedback_comment=alpha.feedback_comment,
        metrics=alpha.metrics or {},
        pnl_data=alpha.pnl_data or {},
        created_at=alpha.created_at
    )
