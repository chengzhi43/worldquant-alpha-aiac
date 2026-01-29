"""
Unit tests for core experiment module.

Tests:
- Hypothesis creation and serialization
- AlphaExperiment lifecycle
- EvoStep relationships
"""

import pytest
from datetime import datetime
from backend.agents.core.experiment import (
    Hypothesis,
    AlphaExperiment,
    EvoStep,
    ExperimentStatus,
    RunningInfo,
)


class TestHypothesis:
    """Tests for Hypothesis dataclass."""
    
    def test_hypothesis_creation(self):
        """Test basic hypothesis creation."""
        hypo = Hypothesis(
            statement="Momentum persists in low volatility stocks",
            rationale="Low vol stocks have less noise",
            expected_signal="momentum",
            key_fields=["close", "volatility_20"],
            confidence="high"
        )
        
        assert hypo.statement == "Momentum persists in low volatility stocks"
        assert hypo.expected_signal == "momentum"
        assert "close" in hypo.key_fields
        assert hypo.confidence == "high"
    
    def test_hypothesis_to_dict(self):
        """Test hypothesis serialization."""
        hypo = Hypothesis(
            statement="Test statement",
            rationale="Test rationale",
            expected_signal="momentum",
            key_fields=["close"],
            suggested_operators=["rank", "ts_mean"],
            confidence="medium",
            novelty="established"
        )
        
        data = hypo.to_dict()
        
        assert data["statement"] == "Test statement"
        assert data["rationale"] == "Test rationale"
        assert data["expected_signal"] == "momentum"
        assert data["key_fields"] == ["close"]
        assert data["suggested_operators"] == ["rank", "ts_mean"]
    
    def test_hypothesis_from_dict(self):
        """Test hypothesis deserialization."""
        data = {
            "statement": "Price momentum predicts returns",
            "rationale": "Trend following works",
            "expected_signal": "momentum",
            "key_fields": ["close", "volume"],
            "confidence": "high"
        }
        
        hypo = Hypothesis.from_dict(data)
        
        assert hypo.statement == "Price momentum predicts returns"
        assert hypo.rationale == "Trend following works"
        assert "volume" in hypo.key_fields
    
    def test_hypothesis_from_dict_with_legacy_field(self):
        """Test hypothesis from dict with 'idea' instead of 'statement'."""
        data = {
            "idea": "Legacy idea field",
            "rationale": "Test"
        }
        
        hypo = Hypothesis.from_dict(data)
        
        assert hypo.statement == "Legacy idea field"
    
    def test_hypothesis_str(self):
        """Test hypothesis string representation."""
        hypo = Hypothesis(
            statement="Test hypothesis",
            rationale="Test reason"
        )
        
        result = str(hypo)
        
        assert "Hypothesis: Test hypothesis" in result
        assert "Test reason" in result  # Could be "Reason:" or "Rationale:"


class TestAlphaExperiment:
    """Tests for AlphaExperiment dataclass."""
    
    def test_experiment_creation(self):
        """Test basic experiment creation."""
        exp = AlphaExperiment(
            id="exp_001",
            expression="rank(close)",
            explanation="Simple price rank"
        )
        
        assert exp.id == "exp_001"
        assert exp.expression == "rank(close)"
        assert exp.status == ExperimentStatus.PENDING
    
    def test_experiment_with_hypothesis(self):
        """Test experiment with hypothesis link."""
        hypo = Hypothesis(
            statement="Price momentum works",
            rationale="Trend following"
        )
        
        exp = AlphaExperiment(
            id="exp_002",
            hypothesis=hypo,
            expression="rank(ts_mean(close, 20))",
            status=ExperimentStatus.COMPLETED,
            metrics={"sharpe": 1.8, "fitness": 0.45},
            quality_status="PASS"
        )
        
        assert exp.hypothesis.statement == "Price momentum works"
        assert exp.is_success()
        assert exp.get_sharpe() == 1.8
    
    def test_experiment_is_optimizable(self):
        """Test is_optimizable check."""
        exp = AlphaExperiment(
            id="exp_003",
            expression="rank(close)",
            quality_status="OPTIMIZE"
        )
        
        assert exp.is_optimizable()
        assert not exp.is_success()
    
    def test_experiment_get_metrics(self):
        """Test metric accessors."""
        exp = AlphaExperiment(
            id="exp_004",
            expression="rank(close)",
            metrics={
                "sharpe": 1.5,
                "fitness": 0.4,
                "turnover": 0.3
            }
        )
        
        assert exp.get_sharpe() == 1.5
        assert exp.get_fitness() == 0.4
    
    def test_experiment_to_dict(self):
        """Test experiment serialization."""
        hypo = Hypothesis(statement="Test", rationale="Test")
        exp = AlphaExperiment(
            id="exp_005",
            hypothesis=hypo,
            expression="rank(close)",
            status=ExperimentStatus.COMPLETED,
            metrics={"sharpe": 1.2},
            quality_status="PASS"
        )
        
        data = exp.to_dict()
        
        assert data["id"] == "exp_005"
        assert data["expression"] == "rank(close)"
        assert data["hypothesis"]["statement"] == "Test"
        assert data["status"] == "completed"
    
    def test_experiment_failed_state(self):
        """Test experiment in failed state."""
        exp = AlphaExperiment(
            id="exp_006",
            expression="invalid_expression",
            status=ExperimentStatus.FAILED,
            error_type="SYNTAX_ERROR",
            error_message="Unknown function"
        )
        
        assert exp.status == ExperimentStatus.FAILED
        assert not exp.is_success()
        assert exp.error_type == "SYNTAX_ERROR"
    
    def test_experiment_get_brief_info(self):
        """Test brief info string."""
        hypo = Hypothesis(statement="Test hypothesis", rationale="Test")
        exp = AlphaExperiment(
            id="exp_007",
            hypothesis=hypo,
            expression="rank(close)",
            metrics={"sharpe": 1.5, "fitness": 0.4},
            quality_status="PASS"
        )
        
        info = exp.get_brief_info()
        
        assert "exp_007" in info
        assert "Test hypothesis" in info
        assert "PASS" in info


class TestEvoStep:
    """Tests for EvoStep dataclass."""
    
    def test_evostep_creation(self):
        """Test basic EvoStep creation."""
        exp = AlphaExperiment(id="exp_001", expression="rank(close)")
        
        step = EvoStep(
            experiment=exp,
            parent_indices=()
        )
        
        assert step.experiment.id == "exp_001"
        assert step.is_root()
    
    def test_evostep_with_parent(self):
        """Test EvoStep with parent reference."""
        exp = AlphaExperiment(id="exp_002", expression="rank(close)")
        
        step = EvoStep(
            experiment=exp,
            parent_indices=(0,)
        )
        
        assert not step.is_root()
        assert step.parent_indices == (0,)
    
    def test_evostep_get_hypothesis(self):
        """Test getting hypothesis from EvoStep."""
        hypo = Hypothesis(statement="Test", rationale="Test")
        exp = AlphaExperiment(id="exp_003", hypothesis=hypo, expression="rank(close)")
        
        step = EvoStep(experiment=exp)
        
        assert step.get_hypothesis() == hypo
    
    def test_evostep_was_successful(self):
        """Test success check with feedback."""
        from backend.agents.core.feedback import HypothesisFeedback
        
        exp = AlphaExperiment(
            id="exp_004",
            expression="rank(close)",
            quality_status="PASS"
        )
        
        feedback = HypothesisFeedback(
            observations="Success",
            hypothesis_evaluation="Supported",
            decision=True,
            reason="Good metrics"
        )
        
        step = EvoStep(
            experiment=exp,
            feedback=feedback
        )
        
        assert step.was_successful()


class TestExperimentStatus:
    """Tests for ExperimentStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert ExperimentStatus.PENDING.value == "pending"
        assert ExperimentStatus.RUNNING.value == "running"
        assert ExperimentStatus.COMPLETED.value == "completed"
        assert ExperimentStatus.FAILED.value == "failed"
        assert ExperimentStatus.SKIPPED.value == "skipped"


class TestRunningInfo:
    """Tests for RunningInfo dataclass."""
    
    def test_running_info_default(self):
        """Test default RunningInfo."""
        info = RunningInfo()
        
        assert info.result is None
        assert info.running_time_ms is None
        assert info.started_at is None
        assert info.completed_at is None
    
    def test_running_info_with_data(self):
        """Test RunningInfo with data."""
        info = RunningInfo(
            result={"sharpe": 1.5},
            running_time_ms=1500,
            started_at=datetime.now()
        )
        
        assert info.result["sharpe"] == 1.5
        assert info.running_time_ms == 1500
