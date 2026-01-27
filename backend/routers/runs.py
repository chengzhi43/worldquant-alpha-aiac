from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import ExperimentRun, TraceStep, Alpha


router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    responses={404: {"description": "Not found"}},
)


class ExperimentRunDetailResponse(BaseModel):
    id: int
    task_id: int
    status: str
    trigger_source: Optional[str] = None
    celery_task_id: Optional[str] = None
    config_snapshot: dict = {}
    prompt_version: Optional[str] = None
    thresholds_version: Optional[str] = None
    strategy_snapshot: dict = {}
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TraceStepResponse(BaseModel):
    id: int
    task_id: int
    run_id: Optional[int] = None
    step_type: str
    step_order: int
    iteration: int = 1
    input_data: dict
    output_data: dict
    duration_ms: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlphaListItem(BaseModel):
    id: int
    alpha_id: Optional[str] = None
    task_id: Optional[int] = None
    run_id: Optional[int] = None
    expression: str
    region: Optional[str] = None
    dataset_id: Optional[str] = None
    quality_status: str
    metrics: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True


class AlphaListResponse(BaseModel):
    items: List[AlphaListItem]
    total: int


@router.get("/{run_id}", response_model=ExperimentRunDetailResponse)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    query = select(ExperimentRun).where(ExperimentRun.id == run_id)
    result = await db.execute(query)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/trace", response_model=List[TraceStepResponse])
async def get_run_trace(run_id: int, db: AsyncSession = Depends(get_db)):
    run_query = select(ExperimentRun).where(ExperimentRun.id == run_id)
    run_res = await db.execute(run_query)
    if not run_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")

    query = (
        select(TraceStep)
        .where(TraceStep.run_id == run_id)
        .order_by(TraceStep.step_order)
    )
    result = await db.execute(query)
    steps = result.scalars().all()
    return list(steps)


@router.get("/{run_id}/alphas", response_model=AlphaListResponse)
async def get_run_alphas(
    run_id: int,
    quality_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    run_query = select(ExperimentRun).where(ExperimentRun.id == run_id)
    run_res = await db.execute(run_query)
    if not run_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")

    query = select(Alpha).where(Alpha.run_id == run_id)
    if quality_status:
        query = query.where(Alpha.quality_status == quality_status)

    count_query = select(Alpha.id).where(Alpha.run_id == run_id)
    if quality_status:
        count_query = count_query.where(Alpha.quality_status == quality_status)

    total = len((await db.execute(count_query)).scalars().all())

    query = query.order_by(Alpha.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    alphas = result.scalars().all()

    items: List[AlphaListItem] = []
    for a in alphas:
        items.append(
            AlphaListItem(
                id=a.id,
                alpha_id=a.alpha_id,
                task_id=a.task_id,
                run_id=a.run_id,
                expression=a.expression,
                region=a.region,
                dataset_id=a.dataset_id,
                quality_status=a.quality_status,
                metrics=a.metrics or {},
                created_at=a.created_at,
            )
        )

    return AlphaListResponse(items=items, total=total)
