from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional, Any, TypeVar, Generic
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import DatasetMetadata
from backend.tasks import sync_datasets_from_brain

router = APIRouter(
    prefix="/datasets",
    tags=["datasets"],
    responses={404: {"description": "Not found"}},
)

# =============================================================================
# MODELS
# =============================================================================

class DatasetResponse(BaseModel):
    dataset_id: str
    region: str
    universe: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    field_count: int
    alpha_success_count: int
    alpha_fail_count: int
    mining_weight: float
    last_synced_at: Optional[datetime] = None
    # New fields
    date_coverage: Optional[float] = None
    themes: Optional[List[Any]] = None
    resources: Optional[List[Any]] = None
    value_score: Optional[int] = None
    alpha_count: Optional[int] = None
    pyramid_multiplier: Optional[float] = None
    coverage: Optional[float] = None
    
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

# Update list_datasets to populate new fields
@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    region: Optional[str] = Query(None, description="Filter by region (USA, CHN, etc.)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by ID or description"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List available datasets with optional filtering.
    """
    # 1. Base Query
    query = select(DatasetMetadata)
    
    if region:
        query = query.where(DatasetMetadata.region == region)
    
    if category:
        query = query.where(DatasetMetadata.category == category)
        
    if search:
        search_term = f"%{search}%"
        query = query.where(or_(
            DatasetMetadata.dataset_id.ilike(search_term),
            DatasetMetadata.description.ilike(search_term)
        ))
    
    # 2. Get Total Count
    count_stmt = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # 3. Pagination & Execution
    query = query.order_by(DatasetMetadata.mining_weight.desc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    datasets = result.scalars().all()
    
    results_list = [DatasetResponse(
        dataset_id=d.dataset_id,
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
        # New fields
        date_coverage=d.date_coverage,
        themes=d.themes,
        resources=d.resources,
        value_score=d.value_score,
        alpha_count=d.alpha_count,
        pyramid_multiplier=d.pyramid_multiplier,
        coverage=d.coverage
    ) for d in datasets]
    
    return PaginatedResponse(total=total, results=results_list)

@router.get("/categories", response_model=List[str])
async def list_dataset_categories(db: AsyncSession = Depends(get_db)):
    """
    Get list of all unique dataset categories.
    """
    stmt = select(DatasetMetadata.category).distinct().where(DatasetMetadata.category != None)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return sorted([c for c in categories if c])

@router.post("/sync", response_model=SyncResponse)
async def sync_datasets(
    region: str = Query(..., description="Region to sync (USA, CHN, etc)"),
    universe: str = Query("TOP3000"),
    background_tasks: BackgroundTasks = None
):
    """
    Trigger background sync of datasets list from Brain.
    """
    task = sync_datasets_from_brain.delay(region=region, universe=universe)
    return SyncResponse(
        message=f"Dataset sync started for {region}",
        task_id=str(task.id)
    )

# ... 

class DataFieldResponse(BaseModel):
    field_id: str
    field_name: str
    description: Optional[str] = None
    dataset_id: Optional[str] = None 
    region: str
    universe: str
    delay: int
    is_active: bool
    # New fields
    field_type: Optional[str] = None
    date_coverage: Optional[float] = None
    coverage: Optional[float] = None
    pyramid_multiplier: Optional[float] = None
    alpha_count: Optional[int] = None
    
    class Config:
        from_attributes = True

# Update list_dataset_fields construction
@router.get("/{dataset_id}/fields", response_model=PaginatedResponse[DataFieldResponse])
async def list_dataset_fields(
    dataset_id: str,
    region: str = Query("USA"),
    universe: str = Query("TOP3000"),
    delay: int = Query(1),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    # 1. Resolve Dataset
    ds_stmt = select(DatasetMetadata).where(
        DatasetMetadata.dataset_id == dataset_id, 
        DatasetMetadata.region == region,
        DatasetMetadata.universe == universe,
        DatasetMetadata.delay == delay
    )
    ds_result = await db.execute(ds_stmt)
    dataset = ds_result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # 2. Base Query
    from backend.models import DataField
    query = select(DataField).where(
        DataField.dataset_id == dataset.id
    )

    # 3. Get Total
    count_stmt = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # 4. Pagination
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    fields = result.scalars().all()
    
    responses = []
    for f in fields:
        resp = DataFieldResponse(
            field_id=f.field_id,
            field_name=f.field_name,
            description=f.description,
            dataset_id=dataset_id, 
            region=f.region,
            universe=f.universe,
            delay=f.delay,
            is_active=f.is_active,
            field_type=f.field_type,
            date_coverage=f.date_coverage,
            coverage=f.coverage,
            pyramid_multiplier=f.pyramid_multiplier,
            alpha_count=f.alpha_count
        )
        responses.append(resp)
        
    return PaginatedResponse(total=total, results=responses)

@router.post("/{dataset_id}/sync-fields", response_model=SyncResponse)
async def sync_dataset_fields(
    dataset_id: str,
    region: str = Query("USA"),
    universe: str = Query("TOP3000"),
    delay: int = Query(1),
    background_tasks: BackgroundTasks = None
):
    """
    Trigger manual sync of fields for a specific dataset.
    """
    # We need a task for this. For now, creating a dedicated task or reusing generic one.
    # Note: sync_datasets_from_brain currently syncs DATASETS (metadata), not fields.
    # We need a task sync_fields_from_brain.
    # I will add this task to tasks.py in next step.
    
    # Placeholder response until task is added
    from backend.tasks import sync_fields_from_brain
    task = sync_fields_from_brain.delay(dataset_id=dataset_id, region=region, universe=universe, delay=delay)
    
    return SyncResponse(
        message=f"Field sync started for {dataset_id}",
        task_id=str(task.id)
    )
