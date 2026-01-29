"""
Evolving RAG Strategy based on RD-Agent's CoSTEER knowledge management.

Key features:
- Knowledge generation from experiment traces
- Multi-strategy querying (similar success, similar error, component-based)
- Automatic knowledge consolidation
- Attribution-aware learning

This integrates with the existing RAGService but provides enhanced capabilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pickle

from backend.agents.core.experiment import AlphaExperiment, EvoStep, Hypothesis
from backend.agents.core.feedback import AttributionType, HypothesisFeedback
from backend.agents.core.knowledge import (
    EvolvingKnowledge,
    KnowledgeRule,
    KnowledgeType,
    QueriedKnowledge,
)
from backend.agents.core.trace import ExperimentTrace


@dataclass
class AlphaKnowledge:
    """
    Knowledge extracted from a single alpha experiment.
    
    Similar to RD-Agent's CoSTEERKnowledge.
    """
    
    # Source experiment
    experiment_id: str
    hypothesis: Optional[Hypothesis] = None
    expression: str = ""
    
    # Result
    was_successful: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Feedback
    feedback: Optional[HypothesisFeedback] = None
    
    # Context
    dataset_id: str = ""
    region: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_summary(self) -> str:
        """Get summary for knowledge transfer."""
        hypo_text = self.hypothesis.statement[:100] if self.hypothesis else "N/A"
        result = "Success" if self.was_successful else "Failed"
        sharpe = self.metrics.get("sharpe", "N/A")
        return f"""
Hypothesis: {hypo_text}
Expression: {self.expression[:80]}...
Result: {result} (Sharpe: {sharpe})
"""


@dataclass
class EnhancedQueriedKnowledge(QueriedKnowledge):
    """
    Enhanced queried knowledge with multi-source results.
    
    Based on RD-Agent's CoSTEERQueriedKnowledgeV2.
    """
    
    # From similar hypotheses
    similar_hypothesis_successes: List[AlphaKnowledge] = field(default_factory=list)
    similar_hypothesis_failures: List[AlphaKnowledge] = field(default_factory=list)
    
    # From similar errors (error -> fix examples)
    error_to_fix_examples: List[Tuple[str, AlphaKnowledge, AlphaKnowledge]] = field(default_factory=list)
    
    # Failed task info (exceeded retry limit)
    abandoned_hypotheses: List[str] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Format for LLM prompt."""
        sections = []
        
        # Success patterns
        if self.success_patterns:
            patterns_text = "\n".join(r.to_prompt_text() for r in self.success_patterns[:5])
            sections.append(f"**What has worked**:\n{patterns_text}")
        
        # Failure patterns  
        if self.failure_patterns:
            patterns_text = "\n".join(r.to_prompt_text() for r in self.failure_patterns[:5])
            sections.append(f"**What hasn't worked** (be cautious):\n{patterns_text}")
        
        # Similar successful experiments
        if self.similar_hypothesis_successes:
            examples = []
            for k in self.similar_hypothesis_successes[:3]:
                examples.append(k.get_summary())
            sections.append(f"**Similar successful experiments**:\n{''.join(examples)}")
        
        # Error fix examples
        if self.error_to_fix_examples:
            fixes = []
            for error_type, failed, fixed in self.error_to_fix_examples[:3]:
                fixes.append(f"- Error: {error_type}\n  Before: {failed.expression[:50]}...\n  After: {fixed.expression[:50]}...")
            sections.append(f"**How similar errors were fixed**:\n{''.join(fixes)}")
        
        # Abandoned hypotheses
        if self.abandoned_hypotheses:
            sections.append(f"**Do NOT retry these directions** (already failed multiple times):\n" + 
                          "\n".join(f"- {h[:80]}..." for h in self.abandoned_hypotheses[:5]))
        
        return "\n\n".join(sections) if sections else "No specific prior knowledge available."


class EvolvingRAGStrategy(ABC):
    """
    Abstract RAG Strategy for alpha mining.
    
    Based on RD-Agent's RAGStrategy.
    
    Responsibilities:
    1. Load/initialize knowledge base
    2. Query knowledge for experiment generation
    3. Generate new knowledge from experiment traces
    4. Persist knowledge base
    """
    
    def __init__(
        self,
        knowledge_base_path: Optional[Path] = None
    ):
        self.knowledge_base_path = knowledge_base_path
        self.knowledge_base: EvolvingKnowledge = self._load_or_init_knowledge_base()
        
        # Track processed experiments
        self._processed_experiment_count = 0
    
    def _load_or_init_knowledge_base(self) -> EvolvingKnowledge:
        """Load existing or create new knowledge base."""
        if self.knowledge_base_path and self.knowledge_base_path.exists():
            try:
                with open(self.knowledge_base_path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        return EvolvingKnowledge()
    
    def dump_knowledge_base(self):
        """Persist knowledge base to disk."""
        if self.knowledge_base_path:
            self.knowledge_base_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.knowledge_base_path, "wb") as f:
                pickle.dump(self.knowledge_base, f)
    
    @abstractmethod
    def query(
        self,
        hypothesis: Optional[Hypothesis],
        trace: ExperimentTrace,
        **kwargs
    ) -> EnhancedQueriedKnowledge:
        """Query knowledge base for experiment generation."""
    
    @abstractmethod
    def generate_knowledge(
        self,
        trace: ExperimentTrace,
        **kwargs
    ) -> List[KnowledgeRule]:
        """Generate new knowledge from experiment trace."""


class AlphaRAGStrategy(EvolvingRAGStrategy):
    """
    Concrete RAG Strategy for alpha mining.
    
    Based on RD-Agent's CoSTEERRAGStrategyV2.
    
    Features:
    1. Similar hypothesis query (via text embedding)
    2. Similar error query (error type -> fix examples)
    3. Knowledge extraction from trace
    4. Attribution-aware learning
    """
    
    def __init__(
        self,
        knowledge_base_path: Optional[Path] = None,
        max_similar_results: int = 5,
        fail_retry_limit: int = 3
    ):
        super().__init__(knowledge_base_path)
        self.max_similar_results = max_similar_results
        self.fail_retry_limit = fail_retry_limit
        
        # Additional storage for enhanced queries
        self._hypothesis_to_experiments: Dict[str, List[AlphaKnowledge]] = {}
        self._error_to_fixes: Dict[str, List[Tuple[AlphaKnowledge, AlphaKnowledge]]] = {}
        self._abandoned_hypotheses: List[str] = []
    
    def query(
        self,
        hypothesis: Optional[Hypothesis],
        trace: ExperimentTrace,
        dataset_id: Optional[str] = None,
        region: Optional[str] = None,
        **kwargs
    ) -> EnhancedQueriedKnowledge:
        """
        Query knowledge base for experiment generation.
        
        Multi-source query:
        1. General patterns (success/failure rules)
        2. Similar hypothesis experiments
        3. Error-to-fix examples
        """
        
        # Base query from knowledge base
        base_query = self.knowledge_base.query(
            dataset_id=dataset_id,
            region=region,
            min_confidence=0.3,
            max_results=self.max_similar_results
        )
        
        # Enhanced query
        result = EnhancedQueriedKnowledge(
            success_patterns=base_query.success_patterns,
            failure_patterns=base_query.failure_patterns,
            optimization_rules=base_query.optimization_rules,
            query_dataset_id=dataset_id,
            query_region=region,
        )
        
        # Query similar hypotheses
        if hypothesis:
            result.similar_hypothesis_successes = self._query_similar_hypothesis(
                hypothesis.statement, 
                success_only=True
            )
            result.similar_hypothesis_failures = self._query_similar_hypothesis(
                hypothesis.statement,
                success_only=False
            )
        
        # Check for abandoned hypotheses
        result.abandoned_hypotheses = self._get_abandoned_hypotheses(trace)
        
        return result
    
    def _query_similar_hypothesis(
        self,
        hypothesis_text: str,
        success_only: bool = True
    ) -> List[AlphaKnowledge]:
        """Find experiments with similar hypotheses."""
        from difflib import SequenceMatcher
        
        results = []
        
        for hypo_text, experiments in self._hypothesis_to_experiments.items():
            similarity = SequenceMatcher(
                None,
                hypothesis_text.lower(),
                hypo_text.lower()
            ).ratio()
            
            if similarity >= 0.6:
                for exp in experiments:
                    if success_only and exp.was_successful:
                        results.append(exp)
                    elif not success_only and not exp.was_successful:
                        results.append(exp)
        
        # Sort by relevance (could use embedding distance)
        return results[:self.max_similar_results]
    
    def _get_abandoned_hypotheses(self, trace: ExperimentTrace) -> List[str]:
        """Get hypotheses that have failed too many times."""
        abandoned = []
        
        # Count failures per hypothesis
        hypothesis_failures: Dict[str, int] = {}
        
        for exp, feedback in trace.hist:
            if feedback and not feedback.decision:
                if feedback.attribution == AttributionType.HYPOTHESIS:
                    hypo_text = exp.hypothesis.statement if exp.hypothesis else ""
                    if hypo_text:
                        hypothesis_failures[hypo_text] = hypothesis_failures.get(hypo_text, 0) + 1
        
        # Find abandoned
        for hypo, count in hypothesis_failures.items():
            if count >= self.fail_retry_limit:
                abandoned.append(hypo)
        
        return abandoned
    
    def generate_knowledge(
        self,
        trace: ExperimentTrace,
        **kwargs
    ) -> List[KnowledgeRule]:
        """
        Generate new knowledge from experiment trace.
        
        Attribution-aware:
        - Only record hypothesis failures as hypothesis failures
        - Implementation failures are recorded for error-fix patterns
        """
        new_rules = []
        
        # Process new experiments in trace
        for i in range(self._processed_experiment_count, len(trace.hist)):
            experiment, feedback = trace.hist[i]
            
            if not feedback:
                continue
            
            # Create AlphaKnowledge
            alpha_knowledge = AlphaKnowledge(
                experiment_id=experiment.id,
                hypothesis=experiment.hypothesis,
                expression=experiment.expression,
                was_successful=feedback.decision,
                metrics=experiment.metrics,
                feedback=feedback,
                dataset_id=trace.dataset_id,
                region=trace.region,
            )
            
            # Store for hypothesis query
            if experiment.hypothesis:
                hypo_text = experiment.hypothesis.statement
                if hypo_text not in self._hypothesis_to_experiments:
                    self._hypothesis_to_experiments[hypo_text] = []
                self._hypothesis_to_experiments[hypo_text].append(alpha_knowledge)
            
            # Record knowledge based on attribution
            if feedback.should_record_to_knowledge_base():
                # Extract If-Then rules
                for rule_text in feedback.knowledge_extracted:
                    rule = self._parse_rule(rule_text, feedback.decision, trace)
                    if rule:
                        self.knowledge_base.add_rule(rule)
                        new_rules.append(rule)
            
            # Record error-fix patterns for implementation failures
            if not feedback.decision and feedback.attribution == AttributionType.IMPLEMENTATION:
                self._record_error_pattern(experiment, trace.hist[:i])
        
        self._processed_experiment_count = len(trace.hist)
        
        return new_rules
    
    def _parse_rule(
        self,
        rule_text: str,
        was_success: bool,
        trace: ExperimentTrace
    ) -> Optional[KnowledgeRule]:
        """Parse rule text into KnowledgeRule."""
        rule_lower = rule_text.lower()
        
        if "if " in rule_lower and " then " in rule_lower:
            parts = rule_text.split(" then ", 1)
            if len(parts) == 2:
                condition = parts[0].replace("If ", "").replace("if ", "").strip()
                conclusion = parts[1].strip()
                
                return KnowledgeRule(
                    condition=condition,
                    conclusion=conclusion,
                    knowledge_type=KnowledgeType.SUCCESS_PATTERN if was_success else KnowledgeType.FAILURE_PATTERN,
                    dataset_id=trace.dataset_id,
                    region=trace.region,
                    confidence=0.5 if was_success else 0.4,
                )
        
        return None
    
    def _record_error_pattern(
        self,
        failed_experiment: AlphaExperiment,
        previous_experiments: List[Tuple[AlphaExperiment, HypothesisFeedback]]
    ):
        """Record error patterns for later querying."""
        error_type = failed_experiment.error_type or "UNKNOWN"
        
        # Look for similar experiments that succeeded after similar errors
        # This creates error -> fix examples
        for exp, fb in previous_experiments:
            if fb and fb.decision:
                # This was a success - could be a fix example
                # Check if hypothesis is similar
                if exp.hypothesis and failed_experiment.hypothesis:
                    from difflib import SequenceMatcher
                    similarity = SequenceMatcher(
                        None,
                        failed_experiment.hypothesis.statement.lower(),
                        exp.hypothesis.statement.lower()
                    ).ratio()
                    
                    if similarity >= 0.7:
                        # Found a potential fix
                        failed_knowledge = AlphaKnowledge(
                            experiment_id=failed_experiment.id,
                            hypothesis=failed_experiment.hypothesis,
                            expression=failed_experiment.expression,
                            was_successful=False,
                        )
                        fixed_knowledge = AlphaKnowledge(
                            experiment_id=exp.id,
                            hypothesis=exp.hypothesis,
                            expression=exp.expression,
                            was_successful=True,
                        )
                        
                        if error_type not in self._error_to_fixes:
                            self._error_to_fixes[error_type] = []
                        self._error_to_fixes[error_type].append(
                            (failed_knowledge, fixed_knowledge)
                        )


def create_alpha_rag_strategy(
    knowledge_base_path: Optional[str] = None
) -> AlphaRAGStrategy:
    """Factory function for AlphaRAGStrategy."""
    path = Path(knowledge_base_path) if knowledge_base_path else None
    return AlphaRAGStrategy(knowledge_base_path=path)
