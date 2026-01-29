"""
Base Service - Foundation for all service classes

Provides common database operations, transaction management,
and utility methods for service implementations.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from contextlib import asynccontextmanager
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from backend.database import get_db

logger = logging.getLogger("services")

# Type variable for model types
T = TypeVar("T")


def transactional(func):
    """
    Decorator to wrap a method in a transaction.
    
    Automatically commits on success, rolls back on exception.
    
    Usage:
        @transactional
        async def create_item(self, data):
            # ... database operations
            return item
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            result = await func(self, *args, **kwargs)
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Transaction failed in {func.__name__}: {e}")
            raise
    return wrapper


class BaseService:
    """
    Base service class providing common database operations.
    
    All service classes should inherit from this to get:
    - Database session management
    - Transaction handling with commit/rollback
    - Common CRUD operations
    - Query helpers
    
    Usage:
        class MyService(BaseService):
            async def my_operation(self):
                # Use self.db for database operations
                result = await self.db.execute(select(MyModel))
                return result.scalars().all()
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the service with a database session.
        
        Args:
            db: Async database session for all operations
        """
        self.db = db

    async def commit(self):
        """
        Commit the current transaction.
        
        Automatically rolls back on error and logs the failure.
        """
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Database commit failed: {e}")
            raise

    async def rollback(self):
        """Roll back the current transaction."""
        await self.db.rollback()
    
    async def flush(self):
        """
        Flush pending changes without committing.
        
        Useful for getting auto-generated IDs before commit.
        """
        await self.db.flush()
    
    async def refresh(self, entity: Any):
        """
        Refresh an entity from the database.
        
        Args:
            entity: The entity to refresh
        """
        await self.db.refresh(entity)
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for explicit transaction control.
        
        Usage:
            async with self.transaction():
                await self.create(item1)
                await self.create(item2)
                # Commits if no exception, rolls back otherwise
        """
        try:
            yield
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
    
    # =========================================================================
    # Generic CRUD Operations
    # =========================================================================
    
    async def get_by_id(
        self,
        model_class: Type[T],
        id: int,
        load_relations: List[str] = None,
    ) -> Optional[T]:
        """
        Get an entity by ID.
        
        Args:
            model_class: The SQLAlchemy model class
            id: The entity ID
            load_relations: List of relation names to eager load
            
        Returns:
            The entity if found, None otherwise
        """
        query = select(model_class).where(model_class.id == id)
        
        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(model_class, relation)))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        model_class: Type[T],
        limit: int = 100,
        offset: int = 0,
        order_by: str = None,
        order_desc: bool = True,
    ) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            model_class: The SQLAlchemy model class
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Column name to order by
            order_desc: Whether to order descending
            
        Returns:
            List of entities
        """
        query = select(model_class)
        
        if order_by and hasattr(model_class, order_by):
            col = getattr(model_class, order_by)
            query = query.order_by(col.desc() if order_desc else col.asc())
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count(self, model_class: Type[T]) -> int:
        """
        Get total count of entities.
        
        Args:
            model_class: The SQLAlchemy model class
            
        Returns:
            Total count
        """
        query = select(func.count()).select_from(model_class)
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: The entity to create
            
        Returns:
            The created entity with ID populated
        """
        self.db.add(entity)
        await self.flush()
        await self.refresh(entity)
        return entity
    
    async def create_many(self, entities: List[T]) -> List[T]:
        """
        Create multiple entities.
        
        Args:
            entities: List of entities to create
            
        Returns:
            List of created entities
        """
        self.db.add_all(entities)
        await self.flush()
        for entity in entities:
            await self.refresh(entity)
        return entities
    
    async def update_by_id(
        self,
        model_class: Type[T],
        id: int,
        values: Dict[str, Any],
    ) -> bool:
        """
        Update an entity by ID.
        
        Args:
            model_class: The SQLAlchemy model class
            id: The entity ID
            values: Dict of column name -> new value
            
        Returns:
            True if entity was updated, False if not found
        """
        stmt = (
            update(model_class)
            .where(model_class.id == id)
            .values(**values)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def delete_by_id(self, model_class: Type[T], id: int) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            model_class: The SQLAlchemy model class
            id: The entity ID
            
        Returns:
            True if entity was deleted, False if not found
        """
        stmt = delete(model_class).where(model_class.id == id)
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def exists(self, model_class: Type[T], id: int) -> bool:
        """
        Check if an entity exists by ID.
        
        Args:
            model_class: The SQLAlchemy model class
            id: The entity ID
            
        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).select_from(model_class).where(model_class.id == id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
    
    # =========================================================================
    # Query Helpers
    # =========================================================================
    
    async def find_by(
        self,
        model_class: Type[T],
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """
        Find entities matching filters.
        
        Args:
            model_class: The SQLAlchemy model class
            filters: Dict of column name -> value
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching entities
        """
        query = select(model_class)
        
        for column, value in filters.items():
            if hasattr(model_class, column):
                query = query.where(getattr(model_class, column) == value)
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def find_one_by(
        self,
        model_class: Type[T],
        filters: Dict[str, Any],
    ) -> Optional[T]:
        """
        Find a single entity matching filters.
        
        Args:
            model_class: The SQLAlchemy model class
            filters: Dict of column name -> value
            
        Returns:
            The first matching entity, or None
        """
        query = select(model_class)
        
        for column, value in filters.items():
            if hasattr(model_class, column):
                query = query.where(getattr(model_class, column) == value)
        
        query = query.limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def count_by(
        self,
        model_class: Type[T],
        filters: Dict[str, Any],
    ) -> int:
        """
        Count entities matching filters.
        
        Args:
            model_class: The SQLAlchemy model class
            filters: Dict of column name -> value
            
        Returns:
            Count of matching entities
        """
        query = select(func.count()).select_from(model_class)
        
        for column, value in filters.items():
            if hasattr(model_class, column):
                query = query.where(getattr(model_class, column) == value)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
