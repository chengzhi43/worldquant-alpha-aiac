"""
Datasets Router - Dataset management

Uses DatasetService for all business logic.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any, TypeVar, Generic
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.services.dataset_service import (
    DatasetService,
    DatasetListFilters,
)

router = APIRouter(
    prefix="/datasets",
    tags=["datasets"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

def get_dataset_service(db: AsyncSession = Depends(get_db)) -> DatasetService:
    """Get DatasetService instance with injected dependencies."""
    return DatasetService(db)


# =============================================================================
# MODELS
# =============================================================================

class DatasetResponse(BaseModel):
    dataset_id: str
    name: Optional[str] = None
    region: str
    universe: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    field_count: int = 0
    alpha_success_count: int = 0
    alpha_fail_count: int = 0
    mining_weight: float = 1.0
    last_synced_at: Optional[datetime] = None
    # Extended fields
    date_coverage: Optional[float] = None
    themes: Optional[List[Any]] = None
    resources: Optional[List[Any]] = None
    value_score: Optional[int] = None
    alpha_count: Optional[int] = None
    pyramid_multiplier: Optional[float] = None
    coverage: Optional[float] = None
    
    class Config:
        from_attributes = True


class DataFieldResponse(BaseModel):
    field_id: str
    field_name: str
    description: Optional[str] = None
    dataset_id: Optional[str] = None
    region: str
    universe: str
    delay: int
    is_active: bool
    # Extended fields
    field_type: Optional[str] = None
    date_coverage: Optional[float] = None
    coverage: Optional[float] = None
    pyramid_multiplier: Optional[float] = None
    alpha_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    message: str
    task_id: str


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    results: List[T]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    region: Optional[str] = Query(None, description="Filter by region (USA, CHN, etc.)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by ID or description"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: DatasetService = Depends(get_dataset_service),
):
    """List available datasets with optional filtering."""
    filters = DatasetListFilters(
        region=region,
        category=category,
        search=search,
        limit=limit,
        offset=offset,
    )
    
    result = await service.list_datasets(filters)
    
    results_list = [
        DatasetResponse(
            dataset_id=d.dataset_id,
            name=d.name,
            region=d.region,
            universe=d.universe,
            category=d.category,
            subcategory=d.subcategory,
            description=d.description,
            field_count=d.field_count,
            alpha_success_count=d.alpha_success_count,
            alpha_fail_count=d.alpha_fail_count,
            mining_weight=d.mining_weight,
            last_synced_at=d.last_synced_at,
            date_coverage=d.date_coverage,
            themes=d.themes,
            resources=d.resources,
            value_score=d.value_score,
            alpha_count=d.alpha_count,
            pyramid_multiplier=d.pyramid_multiplier,
            coverage=d.coverage,
        )
        for d in result.items
    ]
    
    return PaginatedResponse(total=result.total, results=results_list)


@router.get("/categories", response_model=List[str])
async def list_dataset_categories(
    service: DatasetService = Depends(get_dataset_service),
):
    """Get list of all unique dataset categories."""
    return await service.list_categories()


@router.post("/sync", response_model=SyncResponse)
async def sync_datasets(
    region: str = Query(..., description="Region to sync (USA, CHN, etc)"),
    universe: str = Query("TOP3000"),
    service: DatasetService = Depends(get_dataset_service),
):
    """Trigger background sync of datasets list from Brain."""
    task_id = service.trigger_dataset_sync(region=region, universe=universe)
    return SyncResponse(
        message=f"Dataset sync started for {region}",
        task_id=task_id,
    )


@router.get("/{dataset_id}/fields", response_model=PaginatedResponse[DataFieldResponse])
async def list_dataset_fields(
    dataset_id: str,
    region: str = Query("USA"),
    universe: str = Query("TOP3000"),
    delay: int = Query(1),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    service: DatasetService = Depends(get_dataset_service),
):
    """List fields for a specific dataset."""
    try:
        result = await service.get_dataset_fields(
            dataset_id=dataset_id,
            region=region,
            universe=universe,
            delay=delay,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    responses = [
        DataFieldResponse(
            field_id=f.field_id,
            field_name=f.field_name,
            description=f.description,
            dataset_id=f.dataset_id,
            region=f.region,
            universe=f.universe,
            delay=f.delay,
            is_active=f.is_active,
            field_type=f.field_type,
            date_coverage=f.date_coverage,
            coverage=f.coverage,
            pyramid_multiplier=f.pyramid_multiplier,
            alpha_count=f.alpha_count,
        )
        for f in result.items
    ]
    
    return PaginatedResponse(total=result.total, results=responses)


@router.post("/{dataset_id}/sync-fields", response_model=SyncResponse)
async def sync_dataset_fields(
    dataset_id: str,
    region: str = Query("USA"),
    universe: str = Query("TOP3000"),
    delay: int = Query(1),
    service: DatasetService = Depends(get_dataset_service),
):
    """Trigger manual sync of fields for a specific dataset."""
    task_id = service.trigger_field_sync(
        dataset_id=dataset_id,
        region=region,
        universe=universe,
        delay=delay,
    )
    
    return SyncResponse(
        message=f"Field sync started for {dataset_id}",
        task_id=task_id,
    )
