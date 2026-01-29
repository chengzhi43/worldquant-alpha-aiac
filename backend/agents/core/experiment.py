"""
Experiment data structures based on RD-Agent architecture.

Key concepts:
- Hypothesis: Testable investment hypothesis
- AlphaExperiment: Complete experiment record
- EvoStep: Evolution step linking experiment, knowledge, and feedback
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from backend.agents.core.feedback import HypothesisFeedback
    from backend.agents.core.knowledge import QueriedKnowledge


class ExperimentStatus(Enum):
    """Experiment lifecycle status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Hypothesis:
    """
    Testable investment hypothesis.
    
    Based on RD-Agent's Hypothesis class but adapted for alpha mining.
    Each hypothesis should be:
    - Precise and testable
    - Focused on a single direction
    - Supported by rationale
    """
    
    # Core
    statement: str  # Clear, testable hypothesis
    rationale: str  # Economic/behavioral reasoning
    
    # Classification
    expected_signal: str = "unknown"  # momentum | mean_reversion | value | other
    key_fields: List[str] = field(default_factory=list)
    suggested_operators: List[str] = field(default_factory=list)
    
    # Concise summaries (for knowledge transfer)
    concise_reason: str = ""
    concise_observation: str = ""
    concise_justification: str = ""
    concise_knowledge: str = ""  # Transferable insight
    
    # Metadata
    confidence: str = "medium"  # high | medium | low
    novelty: str = "established"  # established | emerging | experimental
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __str__(self) -> str:
        return f"Hypothesis: {self.statement}\nRationale: {self.rationale}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "rationale": self.rationale,
            "expected_signal": self.expected_signal,
            "key_fields": self.key_fields,
            "suggested_operators": self.suggested_operators,
            "confidence": self.confidence,
            "novelty": self.novelty,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Hypothesis':
        return cls(
            statement=data.get("statement", data.get("idea", "")),
            rationale=data.get("rationale", ""),
            expected_signal=data.get("expected_signal", "unknown"),
            key_fields=data.get("key_fields", []),
            suggested_operators=data.get("suggested_operators", []),
            confidence=data.get("confidence", "medium"),
            novelty=data.get("novelty", "established"),
            concise_reason=data.get("concise_reason", ""),
            concise_observation=data.get("concise_observation", ""),
            concise_justification=data.get("concise_justification", ""),
            concise_knowledge=data.get("concise_knowledge", ""),
        )


@dataclass
class RunningInfo:
    """Execution information for an experiment."""
    result: Optional[Dict[str, Any]] = None
    running_time_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class AlphaExperiment:
    """
    Complete record of a single alpha experiment.
    
    Based on RD-Agent's Experiment class, adapted for alpha mining.
    Links hypothesis, implementation, execution, and results.
    """
    
    # Identity
    id: str = ""  # Unique experiment ID
    
    # Hypothesis being tested
    hypothesis: Optional[Hypothesis] = None
    
    # Implementation
    expression: str = ""
    explanation: str = ""
    fields_used: List[str] = field(default_factory=list)
    
    # Execution info
    status: ExperimentStatus = ExperimentStatus.PENDING
    running_info: RunningInfo = field(default_factory=RunningInfo)
    
    # Simulation results
    alpha_id: Optional[str] = None  # BRAIN platform alpha ID
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Quality assessment
    quality_status: str = "PENDING"  # PASS | FAIL | OPTIMIZE
    failed_checks: List[str] = field(default_factory=list)
    
    # Errors (if any)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    
    # Lineage
    derived_from: Optional[str] = None  # Parent experiment ID
    optimization_of: Optional[str] = None  # If this is an optimization variant
    
    # Context
    dataset_id: str = ""
    region: str = ""
    universe: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_success(self) -> bool:
        """Check if experiment was successful."""
        return self.quality_status == "PASS"
    
    def is_optimizable(self) -> bool:
        """Check if experiment is worth optimizing."""
        return self.quality_status == "OPTIMIZE"
    
    def get_sharpe(self) -> Optional[float]:
        """Get sharpe ratio from metrics."""
        return self.metrics.get("sharpe")
    
    def get_fitness(self) -> Optional[float]:
        """Get fitness from metrics."""
        return self.metrics.get("fitness")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hypothesis": self.hypothesis.to_dict() if self.hypothesis else None,
            "expression": self.expression,
            "explanation": self.explanation,
            "status": self.status.value,
            "alpha_id": self.alpha_id,
            "metrics": self.metrics,
            "quality_status": self.quality_status,
            "failed_checks": self.failed_checks,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "dataset_id": self.dataset_id,
            "region": self.region,
            "created_at": self.created_at.isoformat(),
        }
    
    def get_brief_info(self) -> str:
        """Get brief information string for prompts."""
        hypo_text = self.hypothesis.statement[:100] if self.hypothesis else "N/A"
        return f"""
Experiment: {self.id}
Hypothesis: {hypo_text}
Expression: {self.expression[:100]}...
Result: {self.quality_status} (Sharpe: {self.get_sharpe()}, Fitness: {self.get_fitness()})
"""


@dataclass
class EvoStep:
    """
    Evolution step - links experiment, knowledge, and feedback.
    
    Based on RD-Agent's EvoStep. Each step represents:
    - An experiment that was run
    - The knowledge that was queried before generation
    - The feedback received after execution
    
    This enables:
    - Tracing "what knowledge led to this experiment"
    - Learning "what feedback did this experiment generate"
    - Building "if context then approach" rules
    """
    
    # The experiment
    experiment: AlphaExperiment
    
    # Knowledge queried before generation
    queried_knowledge: Optional['QueriedKnowledge'] = None
    
    # Feedback after execution
    feedback: Optional['HypothesisFeedback'] = None
    
    # Parent step (for DAG structure)
    parent_indices: tuple = field(default_factory=tuple)  # () = root, (1,) = parent at index 1
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_root(self) -> bool:
        """Check if this is a root step (new exploration direction)."""
        return len(self.parent_indices) == 0
    
    def get_hypothesis(self) -> Optional[Hypothesis]:
        """Get hypothesis from experiment."""
        return self.experiment.hypothesis if self.experiment else None
    
    def was_successful(self) -> bool:
        """Check if this step's experiment was successful."""
        if self.feedback:
            return self.feedback.decision
        return self.experiment.is_success() if self.experiment else False
