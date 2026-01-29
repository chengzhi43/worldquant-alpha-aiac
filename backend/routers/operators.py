"""
Operators Router - Operator management

Uses OperatorService for all business logic.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.services.operator_service import OperatorService, OperatorListFilters

router = APIRouter(
    prefix="/operators",
    tags=["operators"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

def get_operator_service(db: AsyncSession = Depends(get_db)) -> OperatorService:
    """Get OperatorService instance with injected dependencies."""
    return OperatorService(db)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

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


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=List[OperatorResponse])
async def list_operators(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    service: OperatorService = Depends(get_operator_service),
):
    """List available operators with filtering."""
    filters = OperatorListFilters(
        category=category,
        search=search,
        limit=limit,
        offset=offset,
    )
    
    operators = await service.list_operators(filters)
    
    return [
        OperatorResponse(
            id=op.id,
            name=op.name,
            category=op.category,
            description=op.description,
            param_count=op.param_count,
            is_active=op.is_active,
            created_at=op.created_at,
        )
        for op in operators
    ]


@router.post("/sync", response_model=SyncResponse)
async def sync_operators(
    service: OperatorService = Depends(get_operator_service),
):
    """Trigger manual synchronization of operators from BRAIN platform."""
    task_id = service.trigger_operator_sync()
    return SyncResponse(
        message="Operator sync started",
        task_id=task_id,
    )
