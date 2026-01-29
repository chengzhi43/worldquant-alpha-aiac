"""
Unit tests for core knowledge module.

Tests:
- KnowledgeRule creation and methods
- EvolvingKnowledge management
- QueriedKnowledge formatting
"""

import pytest
from backend.agents.core.knowledge import (
    KnowledgeRule,
    KnowledgeType,
    QueriedKnowledge,
    EvolvingKnowledge,
)


class TestKnowledgeType:
    """Tests for KnowledgeType enum."""
    
    def test_knowledge_type_values(self):
        """Test knowledge type values."""
        assert KnowledgeType.SUCCESS_PATTERN.value == "success_pattern"
        assert KnowledgeType.FAILURE_PATTERN.value == "failure_pattern"
        assert KnowledgeType.OPTIMIZATION_RULE.value == "optimization_rule"
        assert KnowledgeType.FIELD_INSIGHT.value == "field_insight"


class TestKnowledgeRule:
    """Tests for KnowledgeRule dataclass."""
    
    def test_rule_creation(self):
        """Test basic rule creation."""
        rule = KnowledgeRule(
            condition="using ts_zscore on price",
            conclusion="good mean reversion signal"
        )
        
        assert rule.condition == "using ts_zscore on price"
        assert rule.conclusion == "good mean reversion signal"
        assert rule.knowledge_type == KnowledgeType.SUCCESS_PATTERN
        assert rule.confidence == 0.5
    
    def test_rule_str(self):
        """Test rule string representation."""
        rule = KnowledgeRule(
            condition="turnover < 0.3",
            conclusion="high quality signal"
        )
        
        result = str(rule)
        
        assert "If turnover < 0.3" in result
        assert "then high quality signal" in result
    
    def test_rule_to_prompt_text(self):
        """Test rule prompt formatting."""
        rule = KnowledgeRule(
            condition="using decay_linear",
            conclusion="smoother signal",
            confidence=0.8
        )
        
        text = rule.to_prompt_text()
        
        assert "high" in text.lower()  # High confidence
        assert "decay_linear" in text
    
    def test_rule_update_with_evidence_supports(self):
        """Test confidence update with supporting evidence."""
        rule = KnowledgeRule(
            condition="test",
            conclusion="test",
            confidence=0.5,
            evidence_count=1
        )
        
        original_confidence = rule.confidence
        rule.update_with_evidence(supports=True)
        
        assert rule.confidence > original_confidence
        assert rule.evidence_count == 2
    
    def test_rule_update_with_evidence_refutes(self):
        """Test confidence update with refuting evidence."""
        rule = KnowledgeRule(
            condition="test",
            conclusion="test",
            confidence=0.5,
            evidence_count=1
        )
        
        original_confidence = rule.confidence
        rule.update_with_evidence(supports=False)
        
        assert rule.confidence < original_confidence
        assert rule.evidence_count == 2
    
    def test_rule_confidence_bounds(self):
        """Test confidence stays within bounds."""
        rule = KnowledgeRule(condition="test", conclusion="test", confidence=0.9)
        
        # Many supporting updates
        for _ in range(20):
            rule.update_with_evidence(supports=True)
        
        assert rule.confidence <= 0.95
        
        # Many refuting updates
        for _ in range(50):
            rule.update_with_evidence(supports=False)
        
        assert rule.confidence >= 0.05
    
    def test_rule_matches_context_basic(self):
        """Test context matching."""
        rule = KnowledgeRule(
            condition="test",
            conclusion="test",
            knowledge_type=KnowledgeType.SUCCESS_PATTERN,
            dataset_id="fundamental6",
            region="USA"
        )
        
        # Should match
        assert rule.matches_context(dataset_id="fundamental6", region="USA")
        assert rule.matches_context(dataset_id="fundamental6")  # Region not specified
        assert rule.matches_context()  # No filters
        
        # Should not match
        assert not rule.matches_context(dataset_id="other_dataset")
        assert not rule.matches_context(region="CHN")
    
    def test_rule_matches_context_type_filter(self):
        """Test context matching with type filter."""
        rule = KnowledgeRule(
            condition="test",
            conclusion="test",
            knowledge_type=KnowledgeType.SUCCESS_PATTERN
        )
        
        assert rule.matches_context(knowledge_types=[KnowledgeType.SUCCESS_PATTERN])
        assert not rule.matches_context(knowledge_types=[KnowledgeType.FAILURE_PATTERN])
    
    def test_rule_to_dict(self):
        """Test rule serialization."""
        rule = KnowledgeRule(
            condition="test condition",
            conclusion="test conclusion",
            knowledge_type=KnowledgeType.OPTIMIZATION_RULE,
            dataset_id="test_dataset",
            confidence=0.75
        )
        
        data = rule.to_dict()
        
        assert data["condition"] == "test condition"
        assert data["conclusion"] == "test conclusion"
        assert data["knowledge_type"] == "optimization_rule"
        assert data["confidence"] == 0.75


class TestQueriedKnowledge:
    """Tests for QueriedKnowledge dataclass."""
    
    def test_queried_knowledge_creation(self):
        """Test basic creation."""
        qk = QueriedKnowledge()
        
        assert len(qk.success_patterns) == 0
        assert len(qk.failure_patterns) == 0
        assert len(qk.optimization_rules) == 0
    
    def test_queried_knowledge_has_relevant(self):
        """Test has_relevant_knowledge method."""
        qk = QueriedKnowledge()
        assert not qk.has_relevant_knowledge()
        
        qk.success_patterns = [
            KnowledgeRule(condition="test", conclusion="test")
        ]
        assert qk.has_relevant_knowledge()
    
    def test_queried_knowledge_to_prompt_context_empty(self):
        """Test prompt context with no knowledge."""
        qk = QueriedKnowledge()
        context = qk.to_prompt_context()
        
        assert "No specific knowledge" in context
    
    def test_queried_knowledge_to_prompt_context_with_patterns(self):
        """Test prompt context with patterns."""
        qk = QueriedKnowledge()
        qk.success_patterns = [
            KnowledgeRule(condition="cond1", conclusion="conc1"),
            KnowledgeRule(condition="cond2", conclusion="conc2")
        ]
        qk.failure_patterns = [
            KnowledgeRule(condition="fail_cond", conclusion="fail_conc")
        ]
        
        context = qk.to_prompt_context()
        
        assert "have worked" in context.lower() or "worked" in context.lower()
        assert "cond1" in context
        assert "cautious" in context.lower() or "fail_cond" in context


class TestEvolvingKnowledge:
    """Tests for EvolvingKnowledge class."""
    
    @pytest.fixture
    def knowledge_base(self):
        """Create empty knowledge base."""
        return EvolvingKnowledge()
    
    def test_add_rule(self, knowledge_base):
        """Test adding a rule."""
        rule = KnowledgeRule(
            condition="test condition",
            conclusion="test conclusion"
        )
        
        knowledge_base.add_rule(rule)
        
        assert len(knowledge_base.rules) == 1
    
    def test_add_duplicate_rule(self, knowledge_base):
        """Test adding duplicate rule updates existing."""
        rule1 = KnowledgeRule(
            condition="same condition",
            conclusion="same conclusion",
            confidence=0.5
        )
        rule2 = KnowledgeRule(
            condition="same condition",
            conclusion="same conclusion",
            confidence=0.5
        )
        
        knowledge_base.add_rule(rule1)
        original_confidence = knowledge_base.rules[0].confidence
        
        knowledge_base.add_rule(rule2)
        
        # Should still be 1 rule, with updated confidence
        assert len(knowledge_base.rules) == 1
        assert knowledge_base.rules[0].confidence > original_confidence
    
    def test_query_basic(self, knowledge_base):
        """Test basic query."""
        # Add some rules
        knowledge_base.add_rule(KnowledgeRule(
            condition="success1",
            conclusion="result1",
            knowledge_type=KnowledgeType.SUCCESS_PATTERN,
            confidence=0.7
        ))
        knowledge_base.add_rule(KnowledgeRule(
            condition="failure1",
            conclusion="result2",
            knowledge_type=KnowledgeType.FAILURE_PATTERN,
            confidence=0.6
        ))
        
        result = knowledge_base.query()
        
        assert len(result.success_patterns) == 1
        assert len(result.failure_patterns) == 1
    
    def test_query_with_confidence_filter(self, knowledge_base):
        """Test query with confidence filter."""
        knowledge_base.add_rule(KnowledgeRule(
            condition="high_conf",
            conclusion="result",
            confidence=0.8
        ))
        knowledge_base.add_rule(KnowledgeRule(
            condition="low_conf",
            conclusion="result",
            confidence=0.2
        ))
        
        result = knowledge_base.query(min_confidence=0.5)
        
        assert len(result.success_patterns) == 1
        assert result.success_patterns[0].condition == "high_conf"
    
    def test_query_with_dataset_filter(self, knowledge_base):
        """Test query with dataset filter."""
        knowledge_base.add_rule(KnowledgeRule(
            condition="specific",
            conclusion="result",
            dataset_id="dataset_a",
            confidence=0.7
        ))
        knowledge_base.add_rule(KnowledgeRule(
            condition="general",
            conclusion="result",
            dataset_id=None,  # General rule
            confidence=0.7
        ))
        
        result = knowledge_base.query(dataset_id="dataset_a")
        
        # Should include both specific and general rules
        assert len(result.success_patterns) == 2
    
    def test_query_with_max_results(self, knowledge_base):
        """Test query with max results."""
        for i in range(20):
            knowledge_base.add_rule(KnowledgeRule(
                condition=f"condition_{i}",
                conclusion=f"conclusion_{i}",
                confidence=0.5 + i * 0.02
            ))
        
        result = knowledge_base.query(max_results=5)
        
        assert len(result.success_patterns) == 5
    
    def test_query_sorted_by_confidence(self, knowledge_base):
        """Test that query results are sorted by confidence."""
        knowledge_base.add_rule(KnowledgeRule(
            condition="low",
            conclusion="result",
            confidence=0.4
        ))
        knowledge_base.add_rule(KnowledgeRule(
            condition="high",
            conclusion="result",
            confidence=0.9
        ))
        knowledge_base.add_rule(KnowledgeRule(
            condition="medium",
            conclusion="result",
            confidence=0.6
        ))
        
        result = knowledge_base.query()
        
        # Should be sorted high to low
        confidences = [r.confidence for r in result.success_patterns]
        assert confidences == sorted(confidences, reverse=True)
    
    def test_extract_rules_from_feedback_success(self, knowledge_base):
        """Test extracting rules from successful feedback."""
        rules = knowledge_base.extract_rules_from_feedback(
            experiment_id="exp_001",
            hypothesis_text="Momentum works",
            was_success=True,
            knowledge_extracted=[
                "If using ts_mean with 20 days, then good smoothing",
                "If turnover < 0.3, then high quality"
            ],
            dataset_id="fundamental6"
        )
        
        assert len(rules) == 2
        assert len(knowledge_base.rules) == 2
        assert knowledge_base.rules[0].knowledge_type == KnowledgeType.SUCCESS_PATTERN
    
    def test_extract_rules_from_feedback_failure(self, knowledge_base):
        """Test extracting rules from failed feedback."""
        rules = knowledge_base.extract_rules_from_feedback(
            experiment_id="exp_002",
            hypothesis_text="Failed hypothesis",
            was_success=False,
            knowledge_extracted=[
                "If using rank on boolean, then syntax error"
            ]
        )
        
        assert len(rules) == 1
        assert rules[0].knowledge_type == KnowledgeType.FAILURE_PATTERN
    
    def test_extract_rules_invalid_format(self, knowledge_base):
        """Test that invalid rule format is ignored."""
        rules = knowledge_base.extract_rules_from_feedback(
            experiment_id="exp_003",
            hypothesis_text="Test",
            was_success=True,
            knowledge_extracted=[
                "This is not a valid If-then rule",
                "If valid condition, then valid conclusion"
            ]
        )
        
        assert len(rules) == 1  # Only valid rule extracted
    
    def test_get_stats(self, knowledge_base):
        """Test get_stats method."""
        knowledge_base.add_rule(KnowledgeRule(
            condition="c1",
            conclusion="r1",
            knowledge_type=KnowledgeType.SUCCESS_PATTERN,
            dataset_id="ds1"
        ))
        knowledge_base.add_rule(KnowledgeRule(
            condition="c2",
            conclusion="r2",
            knowledge_type=KnowledgeType.FAILURE_PATTERN,
            dataset_id="ds1"
        ))
        
        stats = knowledge_base.get_stats()
        
        assert stats["total_rules"] == 2
        assert "success_pattern" in stats["by_type"]
        assert "failure_pattern" in stats["by_type"]
