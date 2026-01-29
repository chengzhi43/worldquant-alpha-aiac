"""
Operator Service - Business logic for operator management

Provides methods for:
- Operator listing with filters
- Operator sync operations
"""

import logging
from typing import List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.services.base import BaseService
from backend.models import Operator

logger = logging.getLogger("services.operator")


@dataclass
class OperatorInfo:
    """
    Operator information for responses.
    
    Matches real BRAIN API structure from get_operators.
    """
    id: int
    name: str
    category: Optional[str]
    description: Optional[str]
    param_count: int
    is_active: bool
    created_at: Optional[datetime]
    # Extended fields from API
    definition: Optional[str] = None
    scope: Optional[List[str]] = None
    level: Optional[str] = None
    documentation: Optional[str] = None


@dataclass
class OperatorListFilters:
    """Filters for listing operators."""
    category: Optional[str] = None
    search: Optional[str] = None
    limit: int = 100
    offset: int = 0


class OperatorService(BaseService):
    """
    Service for operator-related operations.
    
    Provides a clean interface for operator management,
    abstracting database operations from routers.
    """
    
    # =========================================================================
    # List Operations
    # =========================================================================
    
    async def list_operators(
        self,
        filters: OperatorListFilters,
    ) -> List[OperatorInfo]:
        """
        List operators with optional filtering.
        
        Args:
            filters: Operator list filters
            
        Returns:
            List of OperatorInfo
        """
        query = select(Operator).order_by(Operator.name.asc())
        
        if filters.category:
            query = query.where(Operator.category == filters.category)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(Operator.name.ilike(search_term))
        
        query = query.limit(filters.limit).offset(filters.offset)
        
        result = await self.db.execute(query)
        operators = result.scalars().all()
        
        return [self._to_operator_info(op) for op in operators]
    
    def _to_operator_info(self, op: Operator) -> OperatorInfo:
        """Convert Operator to OperatorInfo."""
        return OperatorInfo(
            id=op.id,
            name=op.name,
            category=op.category,
            description=op.description,
            param_count=op.param_count,
            is_active=op.is_active,
            created_at=op.created_at,
            definition=getattr(op, 'definition', None),
            scope=getattr(op, 'scope', None),
            level=getattr(op, 'level', None),
            documentation=getattr(op, 'documentation', None),
        )
    
    # =========================================================================
    # Sync Operations
    # =========================================================================
    
    def trigger_operator_sync(self) -> str:
        """
        Trigger background sync of operators from BRAIN.
        
        Returns:
            Celery task ID
        """
        from backend.tasks import sync_operators_from_brain
        task = sync_operators_from_brain.delay()
        return str(task.id)
