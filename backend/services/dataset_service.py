"""
Dataset Service - Business logic for dataset management

Provides methods for:
- Dataset listing with filters
- Dataset field queries
- Dataset sync operations
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from backend.services.base import BaseService
from backend.models import DatasetMetadata, DataField

logger = logging.getLogger("services.dataset")


@dataclass
class DatasetInfo:
    """Dataset information for responses."""
    dataset_id: str
    name: Optional[str]
    region: str
    universe: str
    category: Optional[str]
    subcategory: Optional[str]
    description: Optional[str]
    field_count: int
    alpha_success_count: int
    alpha_fail_count: int
    mining_weight: float
    last_synced_at: Optional[datetime]
    # Extended fields
    date_coverage: Optional[float] = None
    themes: Optional[List[Any]] = None
    resources: Optional[List[Any]] = None
    value_score: Optional[int] = None
    alpha_count: Optional[int] = None
    pyramid_multiplier: Optional[float] = None
    coverage: Optional[float] = None


@dataclass
class DataFieldInfo:
    """
    Data field information for responses.
    
    Matches real BRAIN API structure from get_datafields.
    """
    field_id: str
    field_name: str
    description: Optional[str]
    dataset_id: Optional[str]
    region: str
    universe: str
    delay: int
    is_active: bool
    # Extended fields from API
    field_type: Optional[str] = None  # MATRIX, VECTOR, GROUP
    date_coverage: Optional[float] = None
    coverage: Optional[float] = None
    pyramid_multiplier: Optional[float] = None
    user_count: Optional[int] = None
    alpha_count: Optional[int] = None
    # Category info (API returns nested objects)
    category: Optional[str] = None
    category_name: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory_name: Optional[str] = None
    themes: Optional[List[Any]] = None


@dataclass
class PaginatedResult:
    """Paginated result container."""
    total: int
    items: List[Any] = field(default_factory=list)


@dataclass
class DatasetListFilters:
    """Filters for listing datasets."""
    region: Optional[str] = None
    category: Optional[str] = None
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


class DatasetService(BaseService):
    """
    Service for dataset-related operations.
    
    Provides a clean interface for dataset management,
    abstracting database operations from routers.
    """
    
    # =========================================================================
    # List Operations
    # =========================================================================
    
    async def list_datasets(
        self,
        filters: DatasetListFilters,
    ) -> PaginatedResult:
        """
        List datasets with optional filtering.
        
        Args:
            filters: Dataset list filters
            
        Returns:
            PaginatedResult with DatasetInfo items
        """
        # Build base query
        query = select(DatasetMetadata)
        
        if filters.region:
            query = query.where(DatasetMetadata.region == filters.region)
        
        if filters.category:
            query = query.where(DatasetMetadata.category == filters.category)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(or_(
                DatasetMetadata.dataset_id.ilike(search_term),
                DatasetMetadata.description.ilike(search_term)
            ))
        
        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Apply pagination
        query = query.order_by(DatasetMetadata.mining_weight.desc())
        query = query.limit(filters.limit).offset(filters.offset)
        
        result = await self.db.execute(query)
        datasets = result.scalars().all()
        
        items = [self._to_dataset_info(d) for d in datasets]
        
        return PaginatedResult(total=total, items=items)
    
    def _to_dataset_info(self, d: DatasetMetadata) -> DatasetInfo:
        """Convert DatasetMetadata to DatasetInfo."""
        return DatasetInfo(
            dataset_id=d.dataset_id,
            name=d.name,
            region=d.region,
            universe=d.universe,
            category=d.category,
            subcategory=d.subcategory,
            description=d.description,
            field_count=d.field_count or 0,
            alpha_success_count=d.alpha_success_count or 0,
            alpha_fail_count=d.alpha_fail_count or 0,
            mining_weight=d.mining_weight or 1.0,
            last_synced_at=d.last_synced_at,
            date_coverage=d.date_coverage,
            themes=d.themes,
            resources=d.resources,
            value_score=d.value_score,
            alpha_count=d.alpha_count,
            pyramid_multiplier=d.pyramid_multiplier,
            coverage=d.coverage,
        )
    
    async def list_categories(self) -> List[str]:
        """
        Get list of all unique dataset categories.
        
        Returns:
            Sorted list of category names
        """
        stmt = select(DatasetMetadata.category).distinct().where(
            DatasetMetadata.category != None
        )
        result = await self.db.execute(stmt)
        categories = result.scalars().all()
        return sorted([c for c in categories if c])
    
    # =========================================================================
    # Field Operations
    # =========================================================================
    
    async def get_dataset_fields(
        self,
        dataset_id: str,
        region: str = "USA",
        universe: str = "TOP3000",
        delay: int = 1,
        limit: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """
        Get fields for a specific dataset.
        
        Args:
            dataset_id: Dataset identifier
            region: Region filter
            universe: Universe filter
            delay: Delay filter
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            PaginatedResult with DataFieldInfo items
            
        Raises:
            ValueError if dataset not found
        """
        # Resolve dataset
        ds_stmt = select(DatasetMetadata).where(
            DatasetMetadata.dataset_id == dataset_id,
            DatasetMetadata.region == region,
            DatasetMetadata.universe == universe,
            DatasetMetadata.delay == delay,
        )
        ds_result = await self.db.execute(ds_stmt)
        dataset = ds_result.scalar_one_or_none()
        
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Query fields
        query = select(DataField).where(DataField.dataset_id == dataset.id)
        
        # Get total
        count_stmt = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        fields = result.scalars().all()
        
        items = [
            DataFieldInfo(
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
                user_count=getattr(f, 'user_count', None),
                alpha_count=f.alpha_count,
                category=getattr(f, 'category', None),
                category_name=getattr(f, 'category_name', None),
                subcategory=getattr(f, 'subcategory', None),
                subcategory_name=getattr(f, 'subcategory_name', None),
                themes=getattr(f, 'themes', None),
            )
            for f in fields
        ]
        
        return PaginatedResult(total=total, items=items)
    
    # =========================================================================
    # Sync Operations
    # =========================================================================
    
    def trigger_dataset_sync(
        self,
        region: str,
        universe: str = "TOP3000",
    ) -> str:
        """
        Trigger background sync of datasets.
        
        Args:
            region: Region to sync
            universe: Universe to sync
            
        Returns:
            Celery task ID
        """
        from backend.tasks import sync_datasets_from_brain
        task = sync_datasets_from_brain.delay(region=region, universe=universe)
        return str(task.id)
    
    def trigger_field_sync(
        self,
        dataset_id: str,
        region: str = "USA",
        universe: str = "TOP3000",
        delay: int = 1,
    ) -> str:
        """
        Trigger background sync of dataset fields.
        
        Args:
            dataset_id: Dataset to sync
            region: Region
            universe: Universe
            delay: Delay
            
        Returns:
            Celery task ID
        """
        from backend.tasks import sync_fields_from_brain
        task = sync_fields_from_brain.delay(
            dataset_id=dataset_id,
            region=region,
            universe=universe,
            delay=delay,
        )
        return str(task.id)
