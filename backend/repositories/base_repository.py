"""
Base Repository - Foundation for all repository classes

Provides common CRUD operations and query helpers for database access.
Implements CRUDRepositoryProtocol for type safety and testability.
"""

import logging
from typing import (
    Generic,
    TypeVar,
    Type,
    List,
    Optional,
    Dict,
    Any,
    Sequence,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from backend.protocols.repository_protocol import (
    PaginationParams,
    PaginatedResult,
)

logger = logging.getLogger("repositories")

# Type variable for model types
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.
    
    All repository classes should inherit from this to get:
    - Standard CRUD operations (create, read, update, delete)
    - Pagination support
    - Query helpers
    
    Usage:
        class MyRepository(BaseRepository[MyModel]):
            def __init__(self, db: AsyncSession):
                super().__init__(db, MyModel)
    """
    
    def __init__(self, db: AsyncSession, model_class: Type[T]):
        """
        Initialize the repository.
        
        Args:
            db: Async database session
            model_class: The SQLAlchemy model class this repository manages
        """
        self.db = db
        self.model_class = model_class
    
    # =========================================================================
    # Read Operations
    # =========================================================================
    
    async def get_by_id(
        self,
        id: int,
        load_relations: List[str] = None,
    ) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: The entity ID
            load_relations: List of relation names to eager load
            
        Returns:
            The entity if found, None otherwise
        """
        query = select(self.model_class).where(self.model_class.id == id)
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model_class, relation):
                    query = query.options(selectinload(getattr(self.model_class, relation)))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def exists(self, id: int) -> bool:
        """
        Check if an entity exists by ID.
        
        Args:
            id: The entity ID
            
        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).select_from(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
    
    async def get_all(
        self,
        pagination: Optional[PaginationParams] = None,
    ) -> PaginatedResult[T]:
        """
        Get all entities with optional pagination.
        
        Args:
            pagination: Pagination parameters
            
        Returns:
            Paginated result containing entities
        """
        if pagination is None:
            pagination = PaginationParams()
        
        # Get total count
        count_query = select(func.count()).select_from(self.model_class)
        total = (await self.db.execute(count_query)).scalar() or 0
        
        # Build query
        query = select(self.model_class)
        
        if pagination.order_by and hasattr(self.model_class, pagination.order_by):
            col = getattr(self.model_class, pagination.order_by)
            query = query.order_by(col.desc() if pagination.order_desc else col.asc())
        
        query = query.limit(pagination.limit).offset(pagination.offset)
        
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        
        return PaginatedResult(
            items=items,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    
    async def count(self) -> int:
        """
        Get total count of entities.
        
        Returns:
            Total count
        """
        query = select(func.count()).select_from(self.model_class)
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    # =========================================================================
    # Create Operations
    # =========================================================================
    
    async def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: The entity to create
            
        Returns:
            The created entity with ID populated
        """
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity
    
    async def create_many(self, entities: Sequence[T]) -> List[T]:
        """
        Create multiple entities.
        
        Args:
            entities: Sequence of entities to create
            
        Returns:
            List of created entities
        """
        self.db.add_all(entities)
        await self.db.flush()
        for entity in entities:
            await self.db.refresh(entity)
        return list(entities)
    
    # =========================================================================
    # Update Operations
    # =========================================================================
    
    async def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: The entity with updated values
            
        Returns:
            The updated entity
        """
        await self.db.flush()
        await self.db.refresh(entity)
        return entity
    
    async def update_by_id(
        self,
        id: int,
        values: Dict[str, Any],
    ) -> bool:
        """
        Update an entity by ID.
        
        Args:
            id: The entity ID
            values: Dict of column name -> new value
            
        Returns:
            True if entity was updated, False if not found
        """
        stmt = (
            update(self.model_class)
            .where(self.model_class.id == id)
            .values(**values)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def update_many(self, entities: Sequence[T]) -> List[T]:
        """
        Update multiple entities.
        
        Args:
            entities: Sequence of entities with updated values
            
        Returns:
            List of updated entities
        """
        await self.db.flush()
        for entity in entities:
            await self.db.refresh(entity)
        return list(entities)
    
    # =========================================================================
    # Delete Operations
    # =========================================================================
    
    async def delete(self, id: int) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            id: The entity ID
            
        Returns:
            True if entity was deleted, False if not found
        """
        stmt = delete(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def delete_many(self, ids: Sequence[int]) -> int:
        """
        Delete multiple entities by their IDs.
        
        Args:
            ids: Sequence of entity IDs to delete
            
        Returns:
            Number of entities deleted
        """
        if not ids:
            return 0
        stmt = delete(self.model_class).where(self.model_class.id.in_(ids))
        result = await self.db.execute(stmt)
        return result.rowcount
    
    # =========================================================================
    # Query Helpers
    # =========================================================================
    
    async def find_by(
        self,
        filters: Dict[str, Any],
        pagination: Optional[PaginationParams] = None,
    ) -> PaginatedResult[T]:
        """
        Find entities matching filters.
        
        Args:
            filters: Dict of column name -> value
            pagination: Pagination parameters
            
        Returns:
            Paginated result containing matching entities
        """
        if pagination is None:
            pagination = PaginationParams()
        
        # Build base query
        base_query = select(self.model_class)
        count_query = select(func.count()).select_from(self.model_class)
        
        for column, value in filters.items():
            if hasattr(self.model_class, column):
                base_query = base_query.where(getattr(self.model_class, column) == value)
                count_query = count_query.where(getattr(self.model_class, column) == value)
        
        # Get total count
        total = (await self.db.execute(count_query)).scalar() or 0
        
        # Apply pagination
        if pagination.order_by and hasattr(self.model_class, pagination.order_by):
            col = getattr(self.model_class, pagination.order_by)
            base_query = base_query.order_by(col.desc() if pagination.order_desc else col.asc())
        
        base_query = base_query.limit(pagination.limit).offset(pagination.offset)
        
        result = await self.db.execute(base_query)
        items = list(result.scalars().all())
        
        return PaginatedResult(
            items=items,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    
    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[T]:
        """
        Find a single entity matching filters.
        
        Args:
            filters: Dict of column name -> value
            
        Returns:
            The first matching entity, or None
        """
        query = select(self.model_class)
        
        for column, value in filters.items():
            if hasattr(self.model_class, column):
                query = query.where(getattr(self.model_class, column) == value)
        
        query = query.limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def count_by(self, filters: Dict[str, Any]) -> int:
        """
        Count entities matching filters.
        
        Args:
            filters: Dict of column name -> value
            
        Returns:
            Count of matching entities
        """
        query = select(func.count()).select_from(self.model_class)
        
        for column, value in filters.items():
            if hasattr(self.model_class, column):
                query = query.where(getattr(self.model_class, column) == value)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
