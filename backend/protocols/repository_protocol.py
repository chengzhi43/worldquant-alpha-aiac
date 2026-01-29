"""
Repository Protocol - Abstract interfaces for data access layer

This module defines protocols for repository pattern implementation,
allowing for database-agnostic data access and easy testing with
in-memory implementations.
"""

from typing import (
    Protocol,
    TypeVar,
    Generic,
    List,
    Optional,
    Any,
    Dict,
    Sequence,
    runtime_checkable,
)
from dataclasses import dataclass


# Type variable for entity types
T = TypeVar("T")
ID = TypeVar("ID")


@dataclass
class PaginationParams:
    """Pagination parameters for list queries."""
    limit: int = 100
    offset: int = 0
    order_by: Optional[str] = None
    order_desc: bool = True


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated result container."""
    items: List[T]
    total: int
    limit: int
    offset: int
    
    @property
    def has_more(self) -> bool:
        """Check if there are more items available."""
        return self.offset + len(self.items) < self.total
    
    @property
    def page(self) -> int:
        """Get current page number (1-indexed)."""
        return (self.offset // self.limit) + 1 if self.limit > 0 else 1
    
    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1


@runtime_checkable
class RepositoryProtocol(Protocol[T, ID]):
    """
    Base protocol for repository pattern.
    
    Defines the minimal interface for data access operations.
    """
    
    async def get_by_id(self, id: ID) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: The entity ID
            
        Returns:
            The entity if found, None otherwise
        """
        ...
    
    async def exists(self, id: ID) -> bool:
        """
        Check if an entity exists by ID.
        
        Args:
            id: The entity ID
            
        Returns:
            True if exists, False otherwise
        """
        ...


@runtime_checkable
class CRUDRepositoryProtocol(RepositoryProtocol[T, ID], Protocol):
    """
    Extended protocol with full CRUD operations.
    
    Provides create, read, update, delete operations.
    """
    
    async def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: The entity to create
            
        Returns:
            The created entity with ID populated
        """
        ...
    
    async def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: The entity with updated values
            
        Returns:
            The updated entity
        """
        ...
    
    async def delete(self, id: ID) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            id: The entity ID
            
        Returns:
            True if deleted, False if not found
        """
        ...
    
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
        ...
    
    async def count(self) -> int:
        """
        Get total count of entities.
        
        Returns:
            Total number of entities
        """
        ...


class FilterableRepositoryProtocol(CRUDRepositoryProtocol[T, ID], Protocol):
    """
    Extended protocol with filtering capabilities.
    
    Adds methods for querying with filters.
    """
    
    async def find_by(
        self,
        filters: Dict[str, Any],
        pagination: Optional[PaginationParams] = None,
    ) -> PaginatedResult[T]:
        """
        Find entities matching the given filters.
        
        Args:
            filters: Dict of field name -> value to filter by
            pagination: Pagination parameters
            
        Returns:
            Paginated result containing matching entities
        """
        ...
    
    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[T]:
        """
        Find a single entity matching the given filters.
        
        Args:
            filters: Dict of field name -> value to filter by
            
        Returns:
            The first matching entity, or None
        """
        ...
    
    async def count_by(self, filters: Dict[str, Any]) -> int:
        """
        Count entities matching the given filters.
        
        Args:
            filters: Dict of field name -> value to filter by
            
        Returns:
            Count of matching entities
        """
        ...


class BatchRepositoryProtocol(CRUDRepositoryProtocol[T, ID], Protocol):
    """
    Extended protocol with batch operations.
    
    Adds methods for bulk create/update/delete.
    """
    
    async def create_many(self, entities: Sequence[T]) -> List[T]:
        """
        Create multiple entities in a single operation.
        
        Args:
            entities: Sequence of entities to create
            
        Returns:
            List of created entities
        """
        ...
    
    async def update_many(self, entities: Sequence[T]) -> List[T]:
        """
        Update multiple entities in a single operation.
        
        Args:
            entities: Sequence of entities with updated values
            
        Returns:
            List of updated entities
        """
        ...
    
    async def delete_many(self, ids: Sequence[ID]) -> int:
        """
        Delete multiple entities by their IDs.
        
        Args:
            ids: Sequence of entity IDs to delete
            
        Returns:
            Number of entities deleted
        """
        ...


# Specific repository protocols for domain entities

class AlphaRepositoryProtocol(FilterableRepositoryProtocol[Any, int], Protocol):
    """Protocol for Alpha entity repository."""
    
    async def get_by_task_id(
        self,
        task_id: int,
        pagination: Optional[PaginationParams] = None,
    ) -> PaginatedResult[Any]:
        """Get alphas for a specific task."""
        ...
    
    async def get_by_expression_hash(self, expr_hash: str) -> Optional[Any]:
        """Get alpha by expression hash for deduplication."""
        ...
    
    async def get_successful_alphas(
        self,
        task_id: int,
        min_sharpe: Optional[float] = None,
    ) -> List[Any]:
        """Get successful alphas meeting criteria."""
        ...


class TaskRepositoryProtocol(FilterableRepositoryProtocol[Any, int], Protocol):
    """Protocol for MiningTask entity repository."""
    
    async def get_active_tasks(self) -> List[Any]:
        """Get all currently active (RUNNING) tasks."""
        ...
    
    async def get_by_status(self, status: str) -> List[Any]:
        """Get tasks by status."""
        ...
    
    async def update_status(self, task_id: int, status: str) -> bool:
        """Update task status."""
        ...


class KnowledgeRepositoryProtocol(FilterableRepositoryProtocol[Any, int], Protocol):
    """Protocol for KnowledgeEntry entity repository."""
    
    async def get_by_category(
        self,
        category: str,
        min_score: Optional[float] = None,
    ) -> List[Any]:
        """Get knowledge entries by category."""
        ...
    
    async def get_top_patterns(
        self,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Any]:
        """Get top-performing patterns."""
        ...
    
    async def update_score(
        self,
        entry_id: int,
        success: bool,
        delta: float = 0.1,
    ) -> bool:
        """Update pattern score based on usage result."""
        ...
