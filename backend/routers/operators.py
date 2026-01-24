from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import Operator
from backend.tasks import sync_operators_from_brain

router = APIRouter(
    prefix="/operators",
    tags=["operators"],
    responses={404: {"description": "Not found"}},
)

class OperatorResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    param_count: int
    is_active: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    message: str
    task_id: str

@router.get("", response_model=List[OperatorResponse])
async def list_operators(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List available operators with filtering.
    """
    query = select(Operator).order_by(Operator.name.asc())
    
    if category:
        query = query.where(Operator.category == category)
        
    if search:
        search_term = f"%{search}%"
        query = query.where(Operator.name.ilike(search_term))
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    operators = result.scalars().all()
    
    return [OperatorResponse.model_validate(op) for op in operators]

@router.post("/sync", response_model=SyncResponse)
async def sync_operators(background_tasks: BackgroundTasks = None):
    """
    Trigger manual synchronization of operators from BRAIN platform.
    """
    task = sync_operators_from_brain.delay()
    return SyncResponse(
        message="Operator sync started",
        task_id=str(task.id)
    )
