"""
Unit Tests - Service Layer

Tests for AlphaService, DashboardService, and MiningService.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from backend.services import AlphaService, AlphaListFilters, DashboardService
from backend.models import Alpha, MiningTask


class TestAlphaService:
    """Tests for AlphaService."""
    
    @pytest.mark.asyncio
    async def test_list_alphas_empty(self, alpha_service):
        """Test listing alphas when none exist."""
        filters = AlphaListFilters()
        
        items, total = await alpha_service.list_alphas(filters)
        
        assert isinstance(items, list)
        assert total >= 0
    
    @pytest.mark.asyncio
    async def test_list_alphas_with_data(self, alpha_service, sample_alpha):
        """Test listing alphas with data."""
        filters = AlphaListFilters()
        
        items, total = await alpha_service.list_alphas(filters)
        
        assert total >= 1
        assert len(items) >= 1
    
    @pytest.mark.asyncio
    async def test_list_alphas_with_filters(self, alpha_service, sample_alpha):
        """Test listing alphas with filters."""
        filters = AlphaListFilters(region="USA")
        
        items, total = await alpha_service.list_alphas(filters)
        
        assert all(item.region == "USA" for item in items)
    
    @pytest.mark.asyncio
    async def test_get_alpha(self, alpha_service, sample_alpha):
        """Test getting alpha by ID."""
        alpha = await alpha_service.get_alpha(sample_alpha.id)
        
        assert alpha is not None
        assert alpha.id == sample_alpha.id
        assert alpha.expression == sample_alpha.expression
    
    @pytest.mark.asyncio
    async def test_get_alpha_not_found(self, alpha_service):
        """Test getting non-existent alpha."""
        alpha = await alpha_service.get_alpha(99999)
        
        assert alpha is None
    
    @pytest.mark.asyncio
    async def test_get_alpha_by_brain_id(self, alpha_service, sample_alpha):
        """Test getting alpha by BRAIN ID."""
        alpha = await alpha_service.get_alpha_by_brain_id(sample_alpha.alpha_id)
        
        assert alpha is not None
        assert alpha.alpha_id == sample_alpha.alpha_id
    
    @pytest.mark.asyncio
    async def test_submit_feedback(self, alpha_service, sample_alpha):
        """Test submitting feedback."""
        success = await alpha_service.submit_feedback(
            alpha_id=sample_alpha.id,
            rating="LIKED",
            comment="Great alpha!",
        )
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_submit_feedback_invalid_rating(self, alpha_service, sample_alpha):
        """Test submitting invalid feedback."""
        with pytest.raises(ValueError):
            await alpha_service.submit_feedback(
                alpha_id=sample_alpha.id,
                rating="INVALID",
            )
    
    @pytest.mark.asyncio
    async def test_submit_feedback_not_found(self, alpha_service):
        """Test submitting feedback for non-existent alpha."""
        success = await alpha_service.submit_feedback(
            alpha_id=99999,
            rating="LIKED",
        )
        
        assert success is False


class TestDashboardService:
    """Tests for DashboardService."""
    
    @pytest.mark.asyncio
    async def test_get_daily_stats(self, dashboard_service):
        """Test getting daily stats."""
        stats = await dashboard_service.get_daily_stats()
        
        assert stats is not None
        assert stats.date is not None
        assert isinstance(stats.goal, int)
        assert isinstance(stats.total_simulations, int)
    
    @pytest.mark.asyncio
    async def test_get_daily_stats_specific_date(self, dashboard_service):
        """Test getting daily stats for specific date."""
        from datetime import date
        
        yesterday = date.today() - timedelta(days=1)
        stats = await dashboard_service.get_daily_stats(yesterday)
        
        assert stats.date == yesterday.isoformat()
    
    @pytest.mark.asyncio
    async def test_get_active_tasks_empty(self, dashboard_service):
        """Test getting active tasks when none running."""
        tasks = await dashboard_service.get_active_tasks()
        
        assert isinstance(tasks, list)
    
    @pytest.mark.asyncio
    async def test_get_kpi_metrics(self, dashboard_service):
        """Test getting KPI metrics."""
        kpi = await dashboard_service.get_kpi_metrics()
        
        assert kpi is not None
        assert isinstance(kpi.today_simulations, int)
        assert isinstance(kpi.today_success_rate, float)
        assert isinstance(kpi.week_total_alphas, int)
    
    @pytest.mark.asyncio
    async def test_get_recent_trace_steps(self, dashboard_service):
        """Test getting recent trace steps."""
        steps = await dashboard_service.get_recent_trace_steps()
        
        assert isinstance(steps, list)
    
    @pytest.mark.asyncio
    async def test_get_task_status_counts(self, dashboard_service, sample_task):
        """Test getting task status counts."""
        counts = await dashboard_service.get_task_status_counts()
        
        assert isinstance(counts, dict)
