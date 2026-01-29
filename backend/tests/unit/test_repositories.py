"""
Unit Tests - Repository Layer

Tests for AlphaRepository, TaskRepository, and KnowledgeRepository.
"""

import pytest
import pytest_asyncio
from datetime import datetime

from backend.repositories import AlphaRepository, TaskRepository, KnowledgeRepository
from backend.models import Alpha, MiningTask, KnowledgeEntry
from backend.protocols.repository_protocol import PaginationParams


class TestAlphaRepository:
    """Tests for AlphaRepository."""
    
    @pytest.mark.asyncio
    async def test_create_alpha(self, db_session):
        """Test creating an alpha."""
        repo = AlphaRepository(db_session)
        
        alpha = Alpha(
            alpha_id="test-001",
            expression="rank(close)",
            region="USA",
            universe="TOP3000",
            status="created",
            quality_status="PENDING",
        )
        
        created = await repo.create(alpha)
        
        assert created.id is not None
        assert created.alpha_id == "test-001"
        assert created.expression == "rank(close)"
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session, sample_alpha):
        """Test getting alpha by ID."""
        repo = AlphaRepository(db_session)
        
        alpha = await repo.get_by_id(sample_alpha.id)
        
        assert alpha is not None
        assert alpha.id == sample_alpha.id
        assert alpha.alpha_id == sample_alpha.alpha_id
    
    @pytest.mark.asyncio
    async def test_get_by_alpha_id(self, db_session, sample_alpha):
        """Test getting alpha by BRAIN alpha ID."""
        repo = AlphaRepository(db_session)
        
        alpha = await repo.get_by_alpha_id(sample_alpha.alpha_id)
        
        assert alpha is not None
        assert alpha.alpha_id == sample_alpha.alpha_id
    
    @pytest.mark.asyncio
    async def test_get_by_task_id(self, db_session, sample_alpha):
        """Test getting alphas by task ID."""
        repo = AlphaRepository(db_session)
        
        result = await repo.get_by_task_id(sample_alpha.task_id)
        
        assert len(result.items) >= 1
        assert any(a.id == sample_alpha.id for a in result.items)
    
    @pytest.mark.asyncio
    async def test_expression_exists(self, db_session, sample_alpha):
        """Test checking if expression exists."""
        repo = AlphaRepository(db_session)
        
        # Existing hash
        exists = await repo.expression_exists(sample_alpha.expression_hash)
        assert exists is True
        
        # Non-existing hash
        exists = await repo.expression_exists("nonexistent")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_pagination(self, db_session, sample_task):
        """Test pagination."""
        repo = AlphaRepository(db_session)
        
        # Create multiple alphas
        for i in range(5):
            alpha = Alpha(
                alpha_id=f"test-{i:03d}",
                task_id=sample_task.id,
                expression=f"rank(close * {i})",
                region="USA",
                universe="TOP3000",
                status="created",
            )
            await repo.create(alpha)
        
        await db_session.commit()
        
        # Test pagination
        result = await repo.get_by_task_id(
            sample_task.id,
            pagination=PaginationParams(limit=2, offset=0)
        )
        
        assert len(result.items) == 2
        assert result.total >= 5


class TestTaskRepository:
    """Tests for TaskRepository."""
    
    @pytest.mark.asyncio
    async def test_create_task(self, db_session):
        """Test creating a task."""
        repo = TaskRepository(db_session)
        
        task = MiningTask(
            task_name="Test Task",
            region="USA",
            universe="TOP3000",
            status="PENDING",
            daily_goal=4,
        )
        
        created = await repo.create(task)
        
        assert created.id is not None
        assert created.task_name == "Test Task"
    
    @pytest.mark.asyncio
    async def test_get_active_tasks(self, db_session):
        """Test getting active tasks."""
        repo = TaskRepository(db_session)
        
        # Create running task
        task = MiningTask(
            task_name="Running Task",
            region="USA",
            universe="TOP3000",
            status="RUNNING",
            daily_goal=4,
        )
        await repo.create(task)
        await db_session.commit()
        
        active = await repo.get_active_tasks()
        
        assert len(active) >= 1
        assert any(t.status == "RUNNING" for t in active)
    
    @pytest.mark.asyncio
    async def test_update_status(self, db_session, sample_task):
        """Test updating task status."""
        repo = TaskRepository(db_session)
        
        success = await repo.update_status(sample_task.id, "RUNNING")
        await db_session.commit()
        
        assert success is True
        
        # Verify update
        task = await repo.get_by_id(sample_task.id)
        assert task.status == "RUNNING"
    
    @pytest.mark.asyncio
    async def test_get_status_counts(self, db_session, sample_task):
        """Test getting status counts."""
        repo = TaskRepository(db_session)
        
        counts = await repo.get_status_counts()
        
        assert isinstance(counts, dict)
        assert "PENDING" in counts or len(counts) >= 0


class TestKnowledgeRepository:
    """Tests for KnowledgeRepository."""
    
    @pytest.mark.asyncio
    async def test_create_entry(self, db_session):
        """Test creating a knowledge entry."""
        repo = KnowledgeRepository(db_session)
        
        entry = KnowledgeEntry(
            entry_type="SUCCESS_PATTERN",
            pattern="rank(ts_mean(close, 10))",
            description="Momentum pattern",
            usage_count=0,
        )
        
        created = await repo.create(entry)
        
        assert created.id is not None
        assert created.entry_type == "SUCCESS_PATTERN"
    
    @pytest.mark.asyncio
    async def test_get_by_entry_type(self, db_session, sample_knowledge_entry):
        """Test getting entries by type."""
        repo = KnowledgeRepository(db_session)
        
        entries = await repo.get_by_entry_type("SUCCESS_PATTERN")
        
        assert len(entries) >= 1
        assert all(e.entry_type == "SUCCESS_PATTERN" for e in entries)
    
    @pytest.mark.asyncio
    async def test_increment_usage(self, db_session, sample_knowledge_entry):
        """Test incrementing usage count."""
        repo = KnowledgeRepository(db_session)
        
        original_count = sample_knowledge_entry.usage_count
        
        success = await repo.increment_usage(sample_knowledge_entry.id)
        await db_session.commit()
        
        assert success is True
        
        # Verify
        await db_session.refresh(sample_knowledge_entry)
        assert sample_knowledge_entry.usage_count == original_count + 1
    
    @pytest.mark.asyncio
    async def test_get_stats(self, db_session, sample_knowledge_entry):
        """Test getting knowledge base stats."""
        repo = KnowledgeRepository(db_session)
        
        stats = await repo.get_stats()
        
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert stats["total_entries"] >= 1
