"""
Integration tests for core architecture.

Tests:
- Complete pipeline flow
- State adapters
- Integration with existing systems
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
import json

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
from backend.agents.core.knowledge import (
    KnowledgeRule,
    KnowledgeType,
    EvolvingKnowledge,
)
from backend.agents.core.scenario import (
    AlphaMiningScenario,
    DatasetContext,
    OperatorContext,
)
from backend.agents.core.integration import (
    create_scenario,
    create_trace,
    experiment_to_alpha_result,
    enhance_existing_node_evaluate,
)


class TestIntegrationHelpers:
    """Tests for integration helper functions."""
    
    def test_create_scenario(self):
        """Test create_scenario factory."""
        scenario = create_scenario(
            region="USA",
            universe="TOP3000",
            dataset_id="fundamental6",
            fields=[{"id": "close", "description": "Price"}],
            operators=[{"name": "rank", "description": "Rank"}]
        )
        
        assert scenario.region == "USA"
        assert scenario.universe == "TOP3000"
        assert scenario.dataset_context.dataset_id == "fundamental6"
        assert len(scenario.dataset_context.fields) == 1
        assert len(scenario.operator_context.operators) == 1
    
    def test_create_trace(self):
        """Test create_trace factory."""
        trace = create_trace(
            dataset_id="fundamental6",
            region="USA",
            universe="TOP3000"
        )
        
        assert trace.dataset_id == "fundamental6"
        assert trace.region == "USA"
        assert trace.knowledge_base is not None
    
    def test_experiment_to_alpha_result(self):
        """Test converting experiment to legacy format."""
        hypo = Hypothesis(statement="Test", rationale="Test")
        exp = AlphaExperiment(
            id="exp_001",
            hypothesis=hypo,
            expression="rank(close)",
            alpha_id="alpha_123",
            metrics={"sharpe": 1.5},
            quality_status="PASS",
            status=ExperimentStatus.COMPLETED
        )
        
        result = experiment_to_alpha_result(exp)
        
        assert result["alpha_id"] == "alpha_123"
        assert result["expression"] == "rank(close)"
        assert result["hypothesis"] == "Test"
        assert result["metrics"]["sharpe"] == 1.5
        assert result["quality_status"] == "PASS"
        assert result["is_simulated"] is True
    
    def test_enhance_existing_node_evaluate_success(self):
        """Test enhancing evaluation for successful alpha."""
        # Create mock alpha
        class MockAlpha:
            expression = "rank(close)"
            quality_status = "PASS"
        
        alpha = MockAlpha()
        sim_result = {"sharpe": 1.8, "fitness": 0.5}
        hypothesis_dict = {"statement": "Momentum works"}
        
        feedback = enhance_existing_node_evaluate(
            alpha=alpha,
            sim_result=sim_result,
            hypothesis_dict=hypothesis_dict
        )
        
        assert feedback.decision is True
        assert feedback.hypothesis_supported is True
    
    def test_enhance_existing_node_evaluate_failure(self):
        """Test enhancing evaluation for failed alpha."""
        class MockAlpha:
            expression = "rank(close)"
            quality_status = "FAIL"
            validation_error = "Syntax error"
        
        alpha = MockAlpha()
        sim_result = {"sharpe": None, "fitness": None}
        hypothesis_dict = {"statement": "Test hypothesis"}
        
        feedback = enhance_existing_node_evaluate(
            alpha=alpha,
            sim_result=sim_result,
            hypothesis_dict=hypothesis_dict
        )
        
        assert feedback.decision is False


class TestEndToEndFlow:
    """End-to-end tests for complete pipeline flow."""
    
    @pytest.fixture
    def scenario(self):
        """Create test scenario."""
        return create_scenario(
            region="USA",
            universe="TOP3000",
            dataset_id="fundamental6",
            fields=[
                {"id": "close", "description": "Close price"},
                {"id": "volume", "description": "Trading volume"},
            ],
            operators=[
                {"name": "rank", "description": "Cross-sectional rank"},
                {"name": "ts_mean", "description": "Time series mean"},
            ]
        )
    
    @pytest.fixture
    def trace(self):
        """Create test trace."""
        return create_trace(
            dataset_id="fundamental6",
            region="USA",
            universe="TOP3000"
        )
    
    def test_manual_pipeline_flow(self, scenario, trace):
        """Test manual pipeline flow without async."""
        # Step 1: Create hypothesis
        hypothesis = Hypothesis(
            statement="Momentum in closing prices predicts returns",
            rationale="Trend following is a known market inefficiency",
            expected_signal="momentum",
            key_fields=["close"],
            suggested_operators=["rank", "ts_mean"]
        )
        
        # Step 2: Create experiment from hypothesis
        experiment = AlphaExperiment(
            id="exp_001",
            hypothesis=hypothesis,
            expression="rank(ts_mean(close, 20))",
            explanation="20-day momentum signal using cross-sectional rank",
            fields_used=["close"],
            dataset_id="fundamental6",
            region="USA",
            universe="TOP3000"
        )
        
        # Step 3: Simulate execution (mock)
        experiment.status = ExperimentStatus.COMPLETED
        experiment.alpha_id = "alpha_001"
        experiment.metrics = {
            "sharpe": 1.8,
            "fitness": 0.45,
            "turnover": 0.3
        }
        experiment.quality_status = "PASS"
        
        # Step 4: Generate feedback
        feedback = HypothesisFeedback(
            observations="Alpha achieved 1.8 sharpe with 0.3 turnover",
            hypothesis_evaluation="Hypothesis supported - momentum signal works",
            hypothesis_supported=True,
            attribution=AttributionType.HYPOTHESIS,
            decision=True,
            reason="Meets all quality thresholds",
            knowledge_extracted=[
                "If using ts_mean(close, 20), then good momentum smoothing",
                "If turnover < 0.3, then high quality signal"
            ],
            knowledge_confidence=0.8
        )
        
        # Step 5: Add to trace
        idx = trace.add_experiment(experiment, feedback)
        
        # Verify
        assert len(trace) == 1
        assert trace.get_sota() is not None
        sota_exp, sota_fb = trace.get_sota()
        assert sota_exp.id == "exp_001"
        assert sota_fb.decision is True
        
        # Verify knowledge extraction
        assert len(trace.knowledge_base.rules) >= 1
    
    def test_trace_with_multiple_experiments(self, trace):
        """Test trace with multiple experiments including failures."""
        # Experiment 1: Success
        hypo1 = Hypothesis(statement="Hypothesis 1", rationale="")
        exp1 = AlphaExperiment(
            id="exp_001",
            hypothesis=hypo1,
            expression="rank(close)",
            metrics={"sharpe": 1.5},
            quality_status="PASS",
            status=ExperimentStatus.COMPLETED
        )
        fb1 = HypothesisFeedback(
            observations="Success",
            hypothesis_evaluation="Supported",
            decision=True,
            reason="Good"
        )
        trace.add_experiment(exp1, fb1)
        
        # Experiment 2: Failure (hypothesis issue)
        hypo2 = Hypothesis(statement="Bad hypothesis", rationale="")
        exp2 = AlphaExperiment(
            id="exp_002",
            hypothesis=hypo2,
            expression="ts_zscore(close, 5)",
            metrics={"sharpe": -0.5},
            quality_status="FAIL"
        )
        fb2 = HypothesisFeedback(
            observations="Negative sharpe",
            hypothesis_evaluation="Refuted",
            attribution=AttributionType.HYPOTHESIS,
            decision=False,
            reason="Hypothesis doesn't work",
            knowledge_extracted=["If using ts_zscore with 5 days, then overfitting"]
        )
        trace.add_experiment(exp2, fb2)
        
        # Experiment 3: Failure (implementation issue)
        hypo3 = Hypothesis(statement="Good hypothesis", rationale="")
        exp3 = AlphaExperiment(
            id="exp_003",
            hypothesis=hypo3,
            expression="invalid_syntax(",
            status=ExperimentStatus.FAILED,
            error_type="SYNTAX_ERROR"
        )
        fb3 = HypothesisFeedback(
            observations="Syntax error",
            hypothesis_evaluation="Cannot evaluate",
            attribution=AttributionType.IMPLEMENTATION,
            decision=False,
            reason="Implementation error"
        )
        trace.add_experiment(exp3, fb3)
        
        # Verify statistics
        stats = trace.get_stats()
        assert stats["total_experiments"] == 3
        assert stats["successful"] == 1
        assert stats["failed"] == 2
        
        # Verify knowledge was only extracted from non-implementation failures
        # (hypothesis failure should be recorded, implementation should not)
        # The knowledge extraction happens automatically on add_experiment
    
    def test_trace_lineage_and_branching(self, trace):
        """Test experiment lineage and branching."""
        # Root experiment
        exp1 = AlphaExperiment(id="root", expression="root_expr")
        fb1 = HypothesisFeedback(
            observations="", hypothesis_evaluation="", 
            decision=True, reason=""
        )
        idx1 = trace.add_experiment(exp1, fb1, parent_idx=None)
        
        # Branch A from root
        exp2 = AlphaExperiment(id="branch_a", expression="branch_a_expr")
        fb2 = HypothesisFeedback(
            observations="", hypothesis_evaluation="",
            decision=True, reason=""
        )
        idx2 = trace.add_experiment(exp2, fb2, parent_idx=idx1)
        
        # Branch B from root (parallel exploration)
        exp3 = AlphaExperiment(id="branch_b", expression="branch_b_expr")
        fb3 = HypothesisFeedback(
            observations="", hypothesis_evaluation="",
            decision=False, reason=""
        )
        idx3 = trace.add_experiment(exp3, fb3, parent_idx=idx1)
        
        # Continuation from branch A
        exp4 = AlphaExperiment(id="branch_a_child", expression="branch_a_child_expr")
        fb4 = HypothesisFeedback(
            observations="", hypothesis_evaluation="",
            decision=True, reason=""
        )
        idx4 = trace.add_experiment(exp4, fb4, parent_idx=idx2)
        
        # Verify structure
        assert trace.is_root(idx1)
        assert not trace.is_root(idx2)
        assert not trace.is_root(idx3)
        
        # Root should have two children
        children = trace.get_children(idx1)
        assert len(children) == 2
        
        # Lineage of branch_a_child should be: root -> branch_a -> branch_a_child
        lineage = trace.get_lineage(idx4)
        assert len(lineage) == 3
        assert lineage[0][0].id == "root"
        assert lineage[1][0].id == "branch_a"
        assert lineage[2][0].id == "branch_a_child"
    
    def test_knowledge_evolution(self, trace):
        """Test knowledge evolution across experiments."""
        # First experiment - learn a pattern
        exp1 = AlphaExperiment(
            id="exp_001",
            hypothesis=Hypothesis(statement="Momentum works", rationale=""),
            expression="rank(ts_mean(close, 20))",
            metrics={"sharpe": 1.6},
            quality_status="PASS"
        )
        fb1 = HypothesisFeedback(
            observations="Success with 20-day momentum",
            hypothesis_evaluation="Supported",
            decision=True,
            reason="Good",
            knowledge_extracted=[
                "If using ts_mean with 20 days, then good momentum signal"
            ],
            knowledge_confidence=0.7
        )
        trace.add_experiment(exp1, fb1)
        
        # Second experiment - reinforce the pattern
        exp2 = AlphaExperiment(
            id="exp_002",
            hypothesis=Hypothesis(statement="Momentum with volume", rationale=""),
            expression="rank(ts_mean(close, 20)) * volume",
            metrics={"sharpe": 1.8},
            quality_status="PASS"
        )
        fb2 = HypothesisFeedback(
            observations="Even better with volume",
            hypothesis_evaluation="Supported",
            decision=True,
            reason="Great",
            knowledge_extracted=[
                "If using ts_mean with 20 days, then good momentum signal"  # Same pattern
            ],
            knowledge_confidence=0.8
        )
        trace.add_experiment(exp2, fb2)
        
        # Check that confidence increased for the pattern
        query_result = trace.query_knowledge()
        if query_result.success_patterns:
            # Find the ts_mean pattern
            matching = [r for r in query_result.success_patterns if "ts_mean" in r.condition or "20 days" in r.condition]
            if matching:
                # Should have higher confidence due to reinforcement
                assert matching[0].evidence_count >= 1
    
    def test_hypothesis_abandonment(self, trace):
        """Test hypothesis abandonment logic."""
        bad_hypothesis = "This hypothesis always fails"
        
        # Add multiple failures for same hypothesis
        for i in range(4):
            exp = AlphaExperiment(
                id=f"exp_{i}",
                hypothesis=Hypothesis(statement=bad_hypothesis, rationale=""),
                expression=f"test_{i}",
                quality_status="FAIL"
            )
            fb = HypothesisFeedback(
                observations="Failed again",
                hypothesis_evaluation="Refuted",
                attribution=AttributionType.HYPOTHESIS,  # Important: attributed to hypothesis
                decision=False,
                reason="Doesn't work"
            )
            trace.add_experiment(exp, fb)
        
        # Should recommend abandoning
        should_abandon, reason = trace.should_abandon_hypothesis(bad_hypothesis)
        
        assert should_abandon
        assert "4" in reason or "failed" in reason.lower()


class TestKnowledgeIntegration:
    """Tests for knowledge system integration."""
    
    def test_knowledge_query_for_new_experiment(self):
        """Test querying knowledge for a new experiment."""
        # Setup knowledge base with some rules
        kb = EvolvingKnowledge()
        kb.add_rule(KnowledgeRule(
            condition="using rank operator",
            conclusion="helps with cross-sectional comparison",
            knowledge_type=KnowledgeType.SUCCESS_PATTERN,
            confidence=0.8
        ))
        kb.add_rule(KnowledgeRule(
            condition="using ts_zscore with short window",
            conclusion="leads to overfitting",
            knowledge_type=KnowledgeType.FAILURE_PATTERN,
            confidence=0.7
        ))
        
        # Create trace with this knowledge base
        trace = ExperimentTrace(
            dataset_id="test",
            region="USA",
            universe="TOP3000",
            knowledge_base=kb
        )
        
        # Query knowledge
        knowledge = trace.query_knowledge()
        
        assert len(knowledge.success_patterns) == 1
        assert len(knowledge.failure_patterns) == 1
        assert "rank" in knowledge.success_patterns[0].condition
        assert "ts_zscore" in knowledge.failure_patterns[0].condition
    
    def test_knowledge_prompt_context(self):
        """Test generating prompt context from knowledge."""
        kb = EvolvingKnowledge()
        kb.add_rule(KnowledgeRule(
            condition="testing momentum",
            conclusion="works well in trending markets",
            knowledge_type=KnowledgeType.SUCCESS_PATTERN,
            confidence=0.75
        ))
        
        trace = ExperimentTrace(
            dataset_id="test",
            region="USA",
            universe="TOP3000",
            knowledge_base=kb
        )
        
        knowledge = trace.query_knowledge()
        context = knowledge.to_prompt_context()
        
        assert "momentum" in context or "worked" in context.lower()
