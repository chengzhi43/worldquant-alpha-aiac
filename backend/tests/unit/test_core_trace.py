"""
Unit tests for core trace module.

Tests:
- ExperimentTrace DAG structure
- Parent-child relationships
- Knowledge integration
- SOTA tracking
"""

import pytest
from backend.agents.core.experiment import (
    Hypothesis,
    AlphaExperiment,
    ExperimentStatus,
)
from backend.agents.core.feedback import (
    HypothesisFeedback,
    AttributionType,
)
from backend.agents.core.trace import ExperimentTrace


class TestExperimentTrace:
    """Tests for ExperimentTrace class."""
    
    @pytest.fixture
    def empty_trace(self):
        """Create empty trace."""
        return ExperimentTrace(
            dataset_id="fundamental6",
            region="USA",
            universe="TOP3000"
        )
    
    @pytest.fixture
    def sample_experiment(self):
        """Create sample experiment."""
        hypo = Hypothesis(statement="Test hypothesis", rationale="Test")
        return AlphaExperiment(
            id="exp_001",
            hypothesis=hypo,
            expression="rank(close)",
            status=ExperimentStatus.COMPLETED,
            metrics={"sharpe": 1.5},
            quality_status="PASS"
        )
    
    @pytest.fixture
    def sample_feedback(self):
        """Create sample feedback."""
        return HypothesisFeedback(
            observations="Success",
            hypothesis_evaluation="Supported",
            decision=True,
            reason="Good metrics"
        )
    
    def test_trace_creation(self, empty_trace):
        """Test basic trace creation."""
        assert empty_trace.dataset_id == "fundamental6"
        assert empty_trace.region == "USA"
        assert len(empty_trace) == 0
    
    def test_trace_add_experiment_root(self, empty_trace, sample_experiment, sample_feedback):
        """Test adding root experiment."""
        idx = empty_trace.add_experiment(
            sample_experiment,
            sample_feedback,
            parent_idx=None  # Root
        )
        
        assert idx == 0
        assert len(empty_trace) == 1
        assert empty_trace.is_root(0)
    
    def test_trace_add_experiment_with_parent(self, empty_trace, sample_experiment, sample_feedback):
        """Test adding experiment with parent."""
        # Add root
        idx1 = empty_trace.add_experiment(sample_experiment, sample_feedback, parent_idx=None)
        
        # Add child
        child_exp = AlphaExperiment(
            id="exp_002",
            expression="rank(ts_mean(close, 5))",
            status=ExperimentStatus.COMPLETED
        )
        child_fb = HypothesisFeedback(
            observations="Test",
            hypothesis_evaluation="Test",
            decision=True,
            reason="Test"
        )
        idx2 = empty_trace.add_experiment(child_exp, child_fb, parent_idx=idx1)
        
        assert idx2 == 1
        assert not empty_trace.is_root(1)
    
    def test_trace_get_lineage(self, empty_trace, sample_experiment, sample_feedback):
        """Test getting experiment lineage."""
        # Create chain: exp1 -> exp2 -> exp3
        idx1 = empty_trace.add_experiment(sample_experiment, sample_feedback, parent_idx=None)
        
        exp2 = AlphaExperiment(id="exp_002", expression="test2")
        fb2 = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=True, reason="")
        idx2 = empty_trace.add_experiment(exp2, fb2, parent_idx=idx1)
        
        exp3 = AlphaExperiment(id="exp_003", expression="test3")
        fb3 = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=True, reason="")
        idx3 = empty_trace.add_experiment(exp3, fb3, parent_idx=idx2)
        
        lineage = empty_trace.get_lineage(idx3)
        
        assert len(lineage) == 3
        assert lineage[0][0].id == "exp_001"
        assert lineage[1][0].id == "exp_002"
        assert lineage[2][0].id == "exp_003"
    
    def test_trace_get_parents(self, empty_trace, sample_experiment, sample_feedback):
        """Test get_parents method."""
        idx1 = empty_trace.add_experiment(sample_experiment, sample_feedback, parent_idx=None)
        
        exp2 = AlphaExperiment(id="exp_002", expression="test2")
        fb2 = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=True, reason="")
        idx2 = empty_trace.add_experiment(exp2, fb2, parent_idx=idx1)
        
        parents = empty_trace.get_parents(idx2)
        
        assert len(parents) == 2  # Including self
        assert 0 in parents  # Parent
        assert 1 in parents  # Self
    
    def test_trace_get_children(self, empty_trace, sample_experiment, sample_feedback):
        """Test get_children method."""
        idx1 = empty_trace.add_experiment(sample_experiment, sample_feedback, parent_idx=None)
        
        # Add two children
        for i in range(2):
            exp = AlphaExperiment(id=f"child_{i}", expression=f"test{i}")
            fb = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=True, reason="")
            empty_trace.add_experiment(exp, fb, parent_idx=idx1)
        
        children = empty_trace.get_children(idx1)
        
        assert len(children) == 2
    
    def test_trace_get_sota(self, empty_trace):
        """Test SOTA (state of the art) retrieval."""
        # Add failed experiment
        fail_exp = AlphaExperiment(
            id="exp_fail",
            expression="fail",
            quality_status="FAIL"
        )
        fail_fb = HypothesisFeedback(
            observations="Failed",
            hypothesis_evaluation="",
            decision=False,
            reason=""
        )
        empty_trace.add_experiment(fail_exp, fail_fb)
        
        # Add successful experiment
        success_exp = AlphaExperiment(
            id="exp_success",
            expression="success",
            metrics={"sharpe": 2.0},
            quality_status="PASS"
        )
        success_fb = HypothesisFeedback(
            observations="Success",
            hypothesis_evaluation="",
            decision=True,
            reason=""
        )
        empty_trace.add_experiment(success_exp, success_fb)
        
        sota = empty_trace.get_sota()
        
        assert sota is not None
        assert sota[0].id == "exp_success"
    
    def test_trace_get_sota_empty(self, empty_trace):
        """Test SOTA when trace is empty or all failed."""
        assert empty_trace.get_sota() is None
    
    def test_trace_get_sota_hypothesis_and_experiment(self, empty_trace, sample_experiment, sample_feedback):
        """Test get_sota_hypothesis_and_experiment."""
        empty_trace.add_experiment(sample_experiment, sample_feedback)
        
        hypo, exp = empty_trace.get_sota_hypothesis_and_experiment()
        
        assert hypo.statement == "Test hypothesis"
        assert exp.id == "exp_001"
    
    def test_trace_get_successful_experiments(self, empty_trace):
        """Test get_successful_experiments."""
        # Add mix of successful and failed
        for i, success in enumerate([True, False, True, False]):
            exp = AlphaExperiment(id=f"exp_{i}", expression=f"test{i}")
            fb = HypothesisFeedback(
                observations="",
                hypothesis_evaluation="",
                decision=success,
                reason=""
            )
            empty_trace.add_experiment(exp, fb)
        
        successful = empty_trace.get_successful_experiments()
        
        assert len(successful) == 2
    
    def test_trace_get_failed_experiments(self, empty_trace):
        """Test get_failed_experiments."""
        for i, success in enumerate([True, False, True, False]):
            exp = AlphaExperiment(id=f"exp_{i}", expression=f"test{i}")
            fb = HypothesisFeedback(
                observations="",
                hypothesis_evaluation="",
                decision=success,
                reason=""
            )
            empty_trace.add_experiment(exp, fb)
        
        failed = empty_trace.get_failed_experiments()
        
        assert len(failed) == 2
    
    def test_trace_get_recent_experiments(self, empty_trace):
        """Test get_recent_experiments."""
        for i in range(10):
            exp = AlphaExperiment(id=f"exp_{i}", expression=f"test{i}")
            fb = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=True, reason="")
            empty_trace.add_experiment(exp, fb)
        
        recent = empty_trace.get_recent_experiments(3)
        
        assert len(recent) == 3
        assert recent[0][0].id == "exp_7"  # Most recent 3
    
    def test_trace_should_abandon_hypothesis_no_failures(self, empty_trace, sample_experiment, sample_feedback):
        """Test should_abandon_hypothesis with no prior failures."""
        empty_trace.add_experiment(sample_experiment, sample_feedback)
        
        should_abandon, reason = empty_trace.should_abandon_hypothesis("Completely different hypothesis")
        
        assert not should_abandon
    
    def test_trace_should_abandon_hypothesis_with_failures(self, empty_trace):
        """Test should_abandon_hypothesis with many failures."""
        hypo = Hypothesis(statement="This hypothesis fails", rationale="")
        
        # Add multiple failures for same hypothesis
        for i in range(4):
            exp = AlphaExperiment(
                id=f"exp_{i}",
                hypothesis=hypo,
                expression=f"test{i}",
            )
            fb = HypothesisFeedback(
                observations="Failed",
                hypothesis_evaluation="Refuted",
                attribution=AttributionType.HYPOTHESIS,  # Attributed to hypothesis
                decision=False,
                reason="Hypothesis doesn't work"
            )
            empty_trace.add_experiment(exp, fb)
        
        should_abandon, reason = empty_trace.should_abandon_hypothesis("This hypothesis fails")
        
        assert should_abandon
        assert "4" in reason or "failed" in reason.lower()
    
    def test_trace_update_feedback(self, empty_trace, sample_experiment, sample_feedback):
        """Test updating feedback for existing experiment."""
        idx = empty_trace.add_experiment(sample_experiment, sample_feedback)
        
        # Update feedback
        new_feedback = HypothesisFeedback(
            observations="Updated observation",
            hypothesis_evaluation="Updated",
            decision=False,
            reason="Changed mind"
        )
        empty_trace.update_feedback(idx, new_feedback)
        
        exp, fb = empty_trace.hist[idx]
        assert fb.observations == "Updated observation"
        assert not fb.decision
    
    def test_trace_get_stats(self, empty_trace):
        """Test get_stats method."""
        # Add some experiments
        for i, success in enumerate([True, False, True]):
            exp = AlphaExperiment(id=f"exp_{i}", expression=f"test{i}")
            fb = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=success, reason="")
            empty_trace.add_experiment(exp, fb)
        
        stats = empty_trace.get_stats()
        
        assert stats["total_experiments"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert abs(stats["success_rate"] - 0.666) < 0.01
    
    def test_trace_to_prompt_context(self, empty_trace, sample_experiment, sample_feedback):
        """Test to_prompt_context method."""
        empty_trace.add_experiment(sample_experiment, sample_feedback)
        
        context = empty_trace.to_prompt_context()
        
        assert "Recent Experiment History" in context
        assert "exp_001" in context or "Test hypothesis" in context
    
    def test_trace_query_knowledge(self, empty_trace, sample_experiment, sample_feedback):
        """Test query_knowledge method."""
        # Add experiment with knowledge
        sample_feedback.knowledge_extracted = ["If using rank, then normalize first"]
        empty_trace.add_experiment(sample_experiment, sample_feedback)
        
        knowledge = empty_trace.query_knowledge()
        
        # Should return QueriedKnowledge object
        assert knowledge is not None
    
    def test_trace_branching(self, empty_trace, sample_experiment, sample_feedback):
        """Test creating branches in trace."""
        # Add root
        idx1 = empty_trace.add_experiment(sample_experiment, sample_feedback, parent_idx=None)
        
        # Add first branch from root
        branch1_exp = AlphaExperiment(id="branch1", expression="branch1")
        branch1_fb = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=True, reason="")
        idx2 = empty_trace.add_experiment(branch1_exp, branch1_fb, parent_idx=idx1)
        
        # Add second branch from root (parallel exploration)
        branch2_exp = AlphaExperiment(id="branch2", expression="branch2")
        branch2_fb = HypothesisFeedback(observations="", hypothesis_evaluation="", decision=True, reason="")
        idx3 = empty_trace.add_experiment(branch2_exp, branch2_fb, parent_idx=idx1)
        
        # Both branches should have root as parent
        assert empty_trace.get_parents(idx2)[0] == 0  # First is root
        assert empty_trace.get_parents(idx3)[0] == 0  # First is root
        
        # Root should have two children
        children = empty_trace.get_children(idx1)
        assert len(children) == 2
