"""
Unit tests for core feedback module.

Tests:
- HypothesisFeedback creation and methods
- AttributionType handling
- Knowledge extraction logic
"""

import pytest
from backend.agents.core.feedback import (
    HypothesisFeedback,
    AttributionType,
)


class TestAttributionType:
    """Tests for AttributionType enum."""
    
    def test_attribution_values(self):
        """Test attribution enum values."""
        assert AttributionType.HYPOTHESIS.value == "hypothesis"
        assert AttributionType.IMPLEMENTATION.value == "implementation"
        assert AttributionType.BOTH.value == "both"
        assert AttributionType.UNKNOWN.value == "unknown"


class TestHypothesisFeedback:
    """Tests for HypothesisFeedback dataclass."""
    
    def test_feedback_creation_basic(self):
        """Test basic feedback creation."""
        feedback = HypothesisFeedback(
            observations="Alpha achieved 1.8 sharpe",
            hypothesis_evaluation="Hypothesis supported",
            decision=True,
            reason="Good metrics"
        )
        
        assert feedback.observations == "Alpha achieved 1.8 sharpe"
        assert feedback.decision
        assert bool(feedback)  # Truthy if decision is True
    
    def test_feedback_with_attribution(self):
        """Test feedback with attribution."""
        feedback = HypothesisFeedback(
            observations="Failed due to syntax error",
            hypothesis_evaluation="Cannot evaluate",
            attribution=AttributionType.IMPLEMENTATION,
            attribution_confidence=0.9,
            decision=False,
            reason="Syntax error in expression"
        )
        
        assert feedback.attribution == AttributionType.IMPLEMENTATION
        assert feedback.is_implementation_failure()
        assert not feedback.is_hypothesis_failure()
    
    def test_feedback_hypothesis_failure(self):
        """Test hypothesis failure attribution."""
        feedback = HypothesisFeedback(
            observations="Negative sharpe",
            hypothesis_evaluation="Hypothesis refuted",
            attribution=AttributionType.HYPOTHESIS,
            decision=False,
            reason="The hypothesis doesn't work"
        )
        
        assert feedback.is_hypothesis_failure()
        assert not feedback.is_implementation_failure()
    
    def test_feedback_with_new_hypothesis(self):
        """Test feedback with new hypothesis suggestion."""
        feedback = HypothesisFeedback(
            observations="Partial success",
            hypothesis_evaluation="Needs refinement",
            decision=False,
            reason="Close but not enough",
            new_hypothesis="Try adding volume factor",
            new_hypothesis_rationale="Volume confirms momentum"
        )
        
        assert feedback.new_hypothesis == "Try adding volume factor"
        assert feedback.new_hypothesis_rationale == "Volume confirms momentum"
    
    def test_feedback_with_knowledge(self):
        """Test feedback with knowledge extraction."""
        feedback = HypothesisFeedback(
            observations="Success",
            hypothesis_evaluation="Supported",
            decision=True,
            reason="Good",
            knowledge_extracted=[
                "If using ts_mean with 20 days, then good smoothing",
                "If turnover < 0.3, then high quality signal"
            ],
            knowledge_confidence=0.8
        )
        
        assert len(feedback.knowledge_extracted) == 2
        assert "ts_mean" in feedback.knowledge_extracted[0]
    
    def test_feedback_get_confident_knowledge(self):
        """Test get_confident_knowledge method."""
        feedback = HypothesisFeedback(
            observations="Test",
            hypothesis_evaluation="Test",
            decision=True,
            reason="Test",
            knowledge_extracted=["Rule 1", "Rule 2"],
            knowledge_confidence=0.8  # High confidence
        )
        
        confident = feedback.get_confident_knowledge()
        assert len(confident) == 2
        
        # Low confidence
        feedback.knowledge_confidence = 0.3
        confident = feedback.get_confident_knowledge()
        assert len(confident) == 0
    
    def test_feedback_get_tentative_knowledge(self):
        """Test get_tentative_knowledge method."""
        feedback = HypothesisFeedback(
            observations="Test",
            hypothesis_evaluation="Test",
            decision=True,
            reason="Test",
            knowledge_extracted=["Rule 1"],
            knowledge_confidence=0.5  # Medium confidence
        )
        
        tentative = feedback.get_tentative_knowledge()
        assert len(tentative) == 1
        
        # High confidence - not tentative
        feedback.knowledge_confidence = 0.8
        tentative = feedback.get_tentative_knowledge()
        assert len(tentative) == 0
    
    def test_feedback_should_record_to_knowledge_base(self):
        """Test should_record_to_knowledge_base method."""
        # Hypothesis failure - should record
        feedback1 = HypothesisFeedback(
            observations="Test",
            hypothesis_evaluation="Test",
            attribution=AttributionType.HYPOTHESIS,
            decision=False,
            reason="Test"
        )
        assert feedback1.should_record_to_knowledge_base()
        
        # Implementation failure - should NOT record
        feedback2 = HypothesisFeedback(
            observations="Test",
            hypothesis_evaluation="Test",
            attribution=AttributionType.IMPLEMENTATION,
            decision=False,
            reason="Test"
        )
        assert not feedback2.should_record_to_knowledge_base()
        
        # Success - should record
        feedback3 = HypothesisFeedback(
            observations="Test",
            hypothesis_evaluation="Test",
            attribution=AttributionType.HYPOTHESIS,
            decision=True,
            reason="Test"
        )
        assert feedback3.should_record_to_knowledge_base()
    
    def test_feedback_to_dict(self):
        """Test feedback serialization."""
        feedback = HypothesisFeedback(
            observations="Test observation",
            hypothesis_evaluation="Supported",
            hypothesis_supported=True,
            attribution=AttributionType.HYPOTHESIS,
            attribution_confidence=0.8,
            decision=True,
            reason="Good metrics",
            new_hypothesis="Next idea",
            knowledge_extracted=["Rule 1"]
        )
        
        data = feedback.to_dict()
        
        assert data["observations"] == "Test observation"
        assert data["hypothesis_evaluation"] == "Supported"
        assert data["hypothesis_supported"] is True
        assert data["attribution"] == "hypothesis"
        assert data["decision"] is True
        assert data["new_hypothesis"] == "Next idea"
    
    def test_feedback_from_exception(self):
        """Test creating feedback from exception."""
        error = ValueError("Test error message")
        feedback = HypothesisFeedback.from_exception(error)
        
        assert not feedback.decision
        assert "Test error message" in feedback.observations
        assert feedback.attribution == AttributionType.IMPLEMENTATION
        assert feedback.should_retry_implementation
    
    def test_feedback_from_dict(self):
        """Test creating feedback from dict."""
        data = {
            "observation": "Test observation",
            "hypothesis_evaluation": "Supported",
            "hypothesis_supported": True,
            "attribution": {"primary_cause": "hypothesis", "confidence": 0.8},
            "decision": {"success": True, "reasoning": "Good"},
            "new_hypothesis": {"statement": "Next idea", "rationale": "Because"},
            "knowledge_extraction": {
                "confident_knowledge": ["Rule 1", "Rule 2"],
                "should_not_conclude": ["Wrong conclusion"]
            }
        }
        
        feedback = HypothesisFeedback.from_dict(data)
        
        assert feedback.observations == "Test observation"
        assert feedback.hypothesis_supported is True
        assert feedback.attribution == AttributionType.HYPOTHESIS
        assert feedback.decision is True
        assert feedback.new_hypothesis == "Next idea"
        assert len(feedback.knowledge_extracted) == 2
        assert len(feedback.invalid_conclusions) == 1
    
    def test_feedback_from_dict_simple(self):
        """Test creating feedback from simple dict."""
        data = {
            "observations": "Simple observation",
            "hypothesis_evaluation": "Evaluated",
            "attribution": "implementation",
            "decision": False,
            "reason": "Simple reason"
        }
        
        feedback = HypothesisFeedback.from_dict(data)
        
        assert feedback.observations == "Simple observation"
        assert feedback.attribution == AttributionType.IMPLEMENTATION
    
    def test_feedback_str(self):
        """Test feedback string representation."""
        feedback = HypothesisFeedback(
            observations="Test obs",
            hypothesis_evaluation="Evaluated",
            decision=True,
            reason="Good reason",
            new_hypothesis="Next"
        )
        
        result = str(feedback)
        
        assert "Decision: True" in result
        assert "Reason: Good reason" in result
        assert "Observations: Test obs" in result
