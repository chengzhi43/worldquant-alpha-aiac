"""
Knowledge Router - CoSTEER Knowledge Base management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import KnowledgeEntry

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class KnowledgeEntryResponse(BaseModel):
    id: int
    entry_type: str
    pattern: Optional[str] = None
    description: Optional[str] = None
    meta_data: dict = {}
    usage_count: int
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class KnowledgeCreateRequest(BaseModel):
    entry_type: str  # SUCCESS_PATTERN, FAILURE_PITFALL, FIELD_BLACKLIST, OPERATOR_STAT
    pattern: Optional[str] = None
    description: Optional[str] = None
    meta_data: dict = {}


class KnowledgeUpdateRequest(BaseModel):
    pattern: Optional[str] = None
    description: Optional[str] = None
    meta_data: Optional[dict] = None
    is_active: Optional[bool] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=List[KnowledgeEntryResponse])
async def list_knowledge(
    entry_type: Optional[str] = Query(None, description="Filter by type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List knowledge base entries with optional filters.
    """
    query = select(KnowledgeEntry).order_by(KnowledgeEntry.usage_count.desc())
    
    if entry_type:
        query = query.where(KnowledgeEntry.entry_type == entry_type)
    if is_active is not None:
        query = query.where(KnowledgeEntry.is_active == is_active)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return [KnowledgeEntryResponse(
        id=e.id,
        entry_type=e.entry_type,
        pattern=e.pattern,
        description=e.description,
        meta_data=e.meta_data or {},
        usage_count=e.usage_count,
        is_active=e.is_active,
        created_by=e.created_by,
        created_at=e.created_at,
        updated_at=e.updated_at
    ) for e in entries]


@router.get("/success-patterns", response_model=List[KnowledgeEntryResponse])
async def get_success_patterns(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get successful alpha patterns for RAG retrieval.
    These are used as few-shot examples for the Mining Agent.
    """
    query = select(KnowledgeEntry).where(
        KnowledgeEntry.entry_type == "SUCCESS_PATTERN",
        KnowledgeEntry.is_active == True
    ).order_by(KnowledgeEntry.usage_count.desc()).limit(limit)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return [KnowledgeEntryResponse(
        id=e.id,
        entry_type=e.entry_type,
        pattern=e.pattern,
        description=e.description,
        meta_data=e.meta_data or {},
        usage_count=e.usage_count,
        is_active=e.is_active,
        created_by=e.created_by,
        created_at=e.created_at,
        updated_at=e.updated_at
    ) for e in entries]


@router.get("/failure-pitfalls", response_model=List[KnowledgeEntryResponse])
async def get_failure_pitfalls(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get failure pitfalls for the feedback loop.
    These are used to generate negative constraints in prompts.
    """
    query = select(KnowledgeEntry).where(
        KnowledgeEntry.entry_type == "FAILURE_PITFALL",
        KnowledgeEntry.is_active == True
    ).order_by(KnowledgeEntry.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return [KnowledgeEntryResponse(
        id=e.id,
        entry_type=e.entry_type,
        pattern=e.pattern,
        description=e.description,
        meta_data=e.meta_data or {},
        usage_count=e.usage_count,
        is_active=e.is_active,
        created_by=e.created_by,
        created_at=e.created_at,
        updated_at=e.updated_at
    ) for e in entries]


@router.get("/field-blacklist", response_model=List[KnowledgeEntryResponse])
async def get_field_blacklist(
    region: Optional[str] = Query(None, description="Filter by region"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get blacklisted fields that should not be used in alpha expressions.
    """
    query = select(KnowledgeEntry).where(
        KnowledgeEntry.entry_type == "FIELD_BLACKLIST",
        KnowledgeEntry.is_active == True
    )
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Filter by region if specified
    if region:
        entries = [e for e in entries if e.meta_data.get("region") == region]
    
    return [KnowledgeEntryResponse(
        id=e.id,
        entry_type=e.entry_type,
        pattern=e.pattern,
        description=e.description,
        meta_data=e.meta_data or {},
        usage_count=e.usage_count,
        is_active=e.is_active,
        created_by=e.created_by,
        created_at=e.created_at,
        updated_at=e.updated_at
    ) for e in entries]


@router.post("", response_model=KnowledgeEntryResponse)
async def create_knowledge_entry(
    request: KnowledgeCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new knowledge entry (manually add a pattern or pitfall).
    """
    entry = KnowledgeEntry(
        entry_type=request.entry_type,
        pattern=request.pattern,
        description=request.description,
        meta_data=request.meta_data,
        created_by="USER"
    )
    
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    return KnowledgeEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        pattern=entry.pattern,
        description=entry.description,
        meta_data=entry.meta_data or {},
        usage_count=entry.usage_count,
        is_active=entry.is_active,
        created_by=entry.created_by,
        created_at=entry.created_at,
        updated_at=entry.updated_at
    )


@router.put("/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_knowledge_entry(
    entry_id: int,
    request: KnowledgeUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a knowledge entry.
    """
    query = select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    result = await db.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    
    update_data = {}
    if request.pattern is not None:
        update_data["pattern"] = request.pattern
    if request.description is not None:
        update_data["description"] = request.description
    if request.meta_data is not None:
        update_data["meta_data"] = request.meta_data
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    
    if update_data:
        await db.execute(
            update(KnowledgeEntry)
            .where(KnowledgeEntry.id == entry_id)
            .values(**update_data)
        )
        await db.commit()
        await db.refresh(entry)
    
    return KnowledgeEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        pattern=entry.pattern,
        description=entry.description,
        meta_data=entry.meta_data or {},
        usage_count=entry.usage_count,
        is_active=entry.is_active,
        created_by=entry.created_by,
        created_at=entry.created_at,
        updated_at=entry.updated_at
    )


@router.delete("/{entry_id}")
async def delete_knowledge_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a knowledge entry (or deactivate it).
    """
    query = select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    result = await db.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    
    # Soft delete by deactivating
    await db.execute(
        update(KnowledgeEntry)
        .where(KnowledgeEntry.id == entry_id)
        .values(is_active=False)
    )
    await db.commit()
    
    return {"message": "Knowledge entry deactivated", "id": entry_id}
