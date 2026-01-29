"""
Repositories Module - Data Access Layer

This module provides repository classes that abstract database operations,
following the Repository pattern for clean separation between business
logic and data access.

All repositories implement protocols defined in backend.protocols.repository_protocol.
"""

from backend.repositories.base_repository import BaseRepository
from backend.repositories.alpha_repository import AlphaRepository
from backend.repositories.task_repository import TaskRepository
from backend.repositories.knowledge_repository import KnowledgeRepository

__all__ = [
    "BaseRepository",
    "AlphaRepository",
    "TaskRepository",
    "KnowledgeRepository",
]
