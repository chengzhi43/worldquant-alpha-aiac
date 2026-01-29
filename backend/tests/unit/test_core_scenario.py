"""
Unit tests for core scenario module.

Tests:
- AlphaMiningScenario creation and methods
- DatasetContext and OperatorContext
"""

import pytest
from backend.agents.core.scenario import (
    AlphaMiningScenario,
    DatasetContext,
    OperatorContext,
)


class TestDatasetContext:
    """Tests for DatasetContext dataclass."""
    
    def test_dataset_context_creation(self):
        """Test basic creation."""
        ctx = DatasetContext(
            dataset_id="fundamental6",
            dataset_name="Fundamental Data 6",
            description="Core fundamental data"
        )
        
        assert ctx.dataset_id == "fundamental6"
        assert ctx.dataset_name == "Fundamental Data 6"
    
    def test_dataset_context_with_fields(self):
        """Test with fields."""
        ctx = DatasetContext(
            dataset_id="test",
            fields=[
                {"id": "close", "description": "Close price"},
                {"id": "volume", "description": "Trading volume"},
                {"id": "market_cap", "description": "Market capitalization"}
            ]
        )
        
        assert len(ctx.fields) == 3
    
    def test_dataset_context_get_field_summary(self):
        """Test field summary generation."""
        ctx = DatasetContext(
            dataset_id="test",
            dataset_name="Test Dataset",
            fields=[
                {"id": "close", "description": "Close price"},
                {"id": "volume", "description": "Trading volume"}
            ]
        )
        
        summary = ctx.get_field_summary()
        
        assert "Test Dataset" in summary
        assert "close" in summary
        assert "volume" in summary
    
    def test_dataset_context_get_field_summary_empty(self):
        """Test field summary with no fields."""
        ctx = DatasetContext(dataset_id="test")
        
        summary = ctx.get_field_summary()
        
        assert "No field information" in summary
    
    def test_dataset_context_get_field_summary_limit(self):
        """Test field summary respects limit."""
        ctx = DatasetContext(
            dataset_id="test",
            fields=[{"id": f"field_{i}", "description": f"Field {i}"} for i in range(30)]
        )
        
        summary = ctx.get_field_summary(max_fields=5)
        
        assert "field_0" in summary
        assert "field_4" in summary
        assert "and 25 more" in summary


class TestOperatorContext:
    """Tests for OperatorContext dataclass."""
    
    def test_operator_context_creation(self):
        """Test basic creation."""
        ctx = OperatorContext()
        
        assert len(ctx.operators) == 0
    
    def test_operator_context_with_operators(self):
        """Test with operators."""
        ctx = OperatorContext(
            operators=[
                {"name": "rank", "description": "Cross-sectional rank"},
                {"name": "ts_mean", "description": "Time series mean"},
            ]
        )
        
        assert len(ctx.operators) == 2
    
    def test_operator_context_get_summary(self):
        """Test operator summary generation."""
        ctx = OperatorContext(
            operators=[
                {"name": "rank", "description": "Cross-sectional rank"},
                {"name": "ts_mean", "description": "Time series mean"},
            ]
        )
        
        summary = ctx.get_operator_summary()
        
        assert "rank" in summary
        assert "ts_mean" in summary
    
    def test_operator_context_get_summary_empty(self):
        """Test operator summary with no operators."""
        ctx = OperatorContext()
        
        summary = ctx.get_operator_summary()
        
        assert "No operator information" in summary


class TestAlphaMiningScenario:
    """Tests for AlphaMiningScenario class."""
    
    @pytest.fixture
    def basic_scenario(self):
        """Create basic scenario."""
        return AlphaMiningScenario(
            region="USA",
            universe="TOP3000"
        )
    
    @pytest.fixture
    def full_scenario(self):
        """Create full scenario with context."""
        return AlphaMiningScenario(
            region="USA",
            universe="TOP3000",
            dataset_context=DatasetContext(
                dataset_id="fundamental6",
                fields=[{"id": "close", "description": "Price"}]
            ),
            operator_context=OperatorContext(
                operators=[{"name": "rank", "description": "Rank"}]
            )
        )
    
    def test_scenario_creation_basic(self, basic_scenario):
        """Test basic scenario creation."""
        assert basic_scenario.region == "USA"
        assert basic_scenario.universe == "TOP3000"
    
    def test_scenario_background(self, basic_scenario):
        """Test background property."""
        bg = basic_scenario.background
        
        assert "WorldQuant BRAIN" in bg
        assert "Alpha" in bg
        assert "Sharpe" in bg
    
    def test_scenario_source_data(self, full_scenario):
        """Test source_data property."""
        data = full_scenario.source_data
        
        assert "USA" in data
        assert "TOP3000" in data
        assert "fundamental6" in data or "close" in data
    
    def test_scenario_rich_style_description(self, basic_scenario):
        """Test rich style description."""
        desc = basic_scenario.rich_style_description
        
        assert "USA" in desc
        assert "TOP3000" in desc
        assert "Sharpe" in desc
    
    def test_scenario_get_scenario_all_desc(self, full_scenario):
        """Test complete scenario description."""
        desc = full_scenario.get_scenario_all_desc()
        
        assert "WorldQuant BRAIN" in desc or "Alpha" in desc
        assert "USA" in desc
    
    def test_scenario_get_scenario_all_desc_simple_background(self, basic_scenario):
        """Test scenario description with simple background."""
        desc = basic_scenario.get_scenario_all_desc(simple_background=True)
        
        assert len(desc) < len(basic_scenario.get_scenario_all_desc(simple_background=False))
    
    def test_scenario_get_scenario_all_desc_filtered(self, full_scenario):
        """Test scenario description with filter."""
        desc_hypo = full_scenario.get_scenario_all_desc(filtered_tag="hypothesis_only")
        desc_full = full_scenario.get_scenario_all_desc()
        
        # Hypothesis only should be shorter
        assert len(desc_hypo) < len(desc_full)
    
    def test_scenario_get_runtime_environment(self, basic_scenario):
        """Test runtime environment."""
        env = basic_scenario.get_runtime_environment()
        
        assert "USA" in env
        assert "TOP3000" in env
    
    def test_scenario_experiment_setting(self, basic_scenario):
        """Test experiment setting."""
        setting = basic_scenario.experiment_setting
        
        assert setting is not None
        assert "Delay" in setting or "Decay" in setting
    
    def test_scenario_update_dataset(self, basic_scenario):
        """Test updating dataset."""
        new_fields = [
            {"id": "new_field", "description": "New field"}
        ]
        
        basic_scenario.update_dataset("new_dataset", new_fields)
        
        assert basic_scenario.dataset_context.dataset_id == "new_dataset"
        assert len(basic_scenario.dataset_context.fields) == 1
    
    def test_scenario_update_operators(self, basic_scenario):
        """Test updating operators."""
        new_ops = [
            {"name": "new_op", "description": "New operator"}
        ]
        
        basic_scenario.update_operators(new_ops)
        
        assert len(basic_scenario.operator_context.operators) == 1
    
    def test_scenario_to_dict(self, basic_scenario):
        """Test scenario serialization."""
        data = basic_scenario.to_dict()
        
        assert data["region"] == "USA"
        assert data["universe"] == "TOP3000"
        assert "quality_thresholds" in data
    
    def test_scenario_quality_thresholds(self, basic_scenario):
        """Test quality thresholds."""
        thresholds = basic_scenario.quality_thresholds
        
        assert "min_sharpe" in thresholds
        assert "min_fitness" in thresholds
        assert "max_turnover" in thresholds
        assert thresholds["min_sharpe"] > 1.0
