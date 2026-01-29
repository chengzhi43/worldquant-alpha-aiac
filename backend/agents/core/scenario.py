"""
Scenario abstraction based on RD-Agent architecture.

Key concepts:
- Scenario: Provides complete context for alpha mining task
- AlphaMiningScenario: WorldQuant BRAIN specific scenario
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class Scenario(ABC):
    """
    Abstract scenario providing task context.
    
    Based on RD-Agent's Scenario class.
    
    Provides:
    - Background information about the task domain
    - Source data descriptions
    - Environment constraints
    - Experiment settings
    """
    
    @property
    @abstractmethod
    def background(self) -> str:
        """Background information about the task domain."""
    
    @property
    @abstractmethod
    def source_data(self) -> str:
        """Description of available source data."""
    
    @property
    @abstractmethod
    def rich_style_description(self) -> str:
        """Rich description for presentation."""
    
    @abstractmethod
    def get_scenario_all_desc(
        self,
        filtered_tag: Optional[str] = None,
        simple_background: bool = False
    ) -> str:
        """Get complete scenario description."""
    
    @abstractmethod
    def get_runtime_environment(self) -> str:
        """Get runtime environment information."""
    
    @property
    def experiment_setting(self) -> Optional[str]:
        """Get experiment settings as rich text."""
        return None


@dataclass
class DatasetContext:
    """Context about the dataset being mined."""
    dataset_id: str
    dataset_name: str = ""
    description: str = ""
    
    # Available fields
    fields: List[Dict[str, Any]] = field(default_factory=list)
    field_categories: Dict[str, List[str]] = field(default_factory=dict)
    
    # Statistics
    coverage: Optional[float] = None
    update_frequency: Optional[str] = None
    
    def get_field_summary(self, max_fields: int = 20) -> str:
        """Get summary of available fields."""
        if not self.fields:
            return "No field information available."
        
        lines = [f"Dataset: {self.dataset_name or self.dataset_id}"]
        lines.append(f"Total fields: {len(self.fields)}")
        
        # Group by category if available
        if self.field_categories:
            for cat, field_ids in list(self.field_categories.items())[:5]:
                lines.append(f"  - {cat}: {len(field_ids)} fields")
        
        # List sample fields
        lines.append("\nSample fields:")
        for f in self.fields[:max_fields]:
            name = f.get("id") or f.get("name", "unknown")
            desc = f.get("description", "")[:50]
            lines.append(f"  - {name}: {desc}")
        
        if len(self.fields) > max_fields:
            lines.append(f"  ... and {len(self.fields) - max_fields} more")
        
        return "\n".join(lines)


@dataclass
class OperatorContext:
    """Context about available operators."""
    operators: List[Dict[str, Any]] = field(default_factory=list)
    operator_categories: Dict[str, List[str]] = field(default_factory=dict)
    
    def get_operator_summary(self, max_operators: int = 30) -> str:
        """Get summary of available operators."""
        if not self.operators:
            return "No operator information available."
        
        lines = [f"Total operators: {len(self.operators)}"]
        
        # Group by category
        if self.operator_categories:
            for cat, op_ids in list(self.operator_categories.items())[:8]:
                lines.append(f"  - {cat}: {len(op_ids)} operators")
        
        # List commonly used operators
        lines.append("\nCommon operators:")
        for op in self.operators[:max_operators]:
            name = op.get("name", "unknown")
            desc = op.get("description", "")[:40]
            lines.append(f"  - {name}: {desc}")
        
        return "\n".join(lines)


class AlphaMiningScenario(Scenario):
    """
    WorldQuant BRAIN Alpha Mining Scenario.
    
    Provides complete context for alpha mining tasks including:
    - BRAIN platform background
    - Dataset and field information
    - Operator information
    - Quality requirements
    """
    
    def __init__(
        self,
        region: str = "USA",
        universe: str = "TOP3000",
        dataset_context: Optional[DatasetContext] = None,
        operator_context: Optional[OperatorContext] = None
    ):
        self.region = region
        self.universe = universe
        self.dataset_context = dataset_context or DatasetContext(dataset_id="unknown")
        self.operator_context = operator_context or OperatorContext()
        
        # Quality thresholds
        self.quality_thresholds = {
            "min_sharpe": 1.25,
            "min_fitness": 0.3,
            "max_turnover": 0.7,
            "max_drawdown": 0.25,
        }
    
    @property
    def background(self) -> str:
        return """WorldQuant BRAIN Platform Alpha Mining

WorldQuant BRAIN is a quantitative trading research platform where users create 
alpha expressions (mathematical formulas) that predict future stock returns.

Key Concepts:
1. Alpha Expression: A formula combining data fields and operators to generate 
   trading signals (positive = long, negative = short)
   
2. Data Fields: Fundamental, technical, and alternative data (e.g., close, volume, 
   market_cap, analyst_rating)
   
3. Operators: Mathematical functions (rank, ts_mean, zscore, decay_linear, etc.)
   that transform and combine data fields
   
4. Quality Metrics:
   - Sharpe Ratio: Risk-adjusted return (target > 1.25)
   - Fitness: Overall quality score (target > 0.3)
   - Turnover: Portfolio change rate (target < 0.7)
   - Drawdown: Maximum loss from peak (target < 0.25)

5. Submission Tests:
   - Self-correlation check: Alpha must not be too similar to existing alphas
   - Concentration check: Signal must be diversified across stocks
   - In-sample vs out-of-sample: Alpha must generalize, not overfit
"""
    
    @property
    def source_data(self) -> str:
        return f"""Available Data:
        
Region: {self.region}
Universe: {self.universe}

{self.dataset_context.get_field_summary()}

{self.operator_context.get_operator_summary()}
"""
    
    @property
    def rich_style_description(self) -> str:
        return f"""🎯 Alpha Mining Task

Region: {self.region} | Universe: {self.universe}
Dataset: {self.dataset_context.dataset_name or self.dataset_context.dataset_id}
Fields: {len(self.dataset_context.fields)} | Operators: {len(self.operator_context.operators)}

Quality Targets:
  Sharpe ≥ {self.quality_thresholds['min_sharpe']}
  Fitness ≥ {self.quality_thresholds['min_fitness']}
  Turnover ≤ {self.quality_thresholds['max_turnover']}
"""
    
    def get_scenario_all_desc(
        self,
        filtered_tag: Optional[str] = None,
        simple_background: bool = False
    ) -> str:
        """Get complete scenario description for LLM prompts."""
        
        sections = []
        
        # Background
        if simple_background:
            sections.append("You are mining alpha expressions for the WorldQuant BRAIN platform.")
        else:
            sections.append(self.background)
        
        # Constraints
        sections.append(f"""
## Task Constraints

- Region: {self.region}
- Universe: {self.universe}
- Target metrics: Sharpe > {self.quality_thresholds['min_sharpe']}, Fitness > {self.quality_thresholds['min_fitness']}
""")
        
        # Data context
        if filtered_tag != "hypothesis_only":
            sections.append(f"""
## Available Data

{self.dataset_context.get_field_summary(max_fields=15)}
""")
        
        # Operators
        if filtered_tag not in ["hypothesis_only", "data_only"]:
            sections.append(f"""
## Available Operators

{self.operator_context.get_operator_summary(max_operators=20)}
""")
        
        # Guidelines
        sections.append("""
## Guidelines

1. Alpha expressions should be syntactically valid
2. Use appropriate operators for your hypothesis
3. Consider both fundamentals and market dynamics
4. Ensure the alpha is not trivially correlated with existing alphas
5. Balance complexity with interpretability
""")
        
        return "\n".join(sections)
    
    def get_runtime_environment(self) -> str:
        return f"""Runtime Environment:
- Platform: WorldQuant BRAIN Simulation
- Region: {self.region}
- Universe: {self.universe}
- Execution: Cloud-based backtesting
"""
    
    @property
    def experiment_setting(self) -> str:
        return f"""Experiment Settings:
- Delay: 1 day
- Decay: Variable (typically 4-8)
- Neutralization: INDUSTRY or SUBINDUSTRY
- Truncation: 0.01-0.05
- Lookback: 252-504 days
"""
    
    def update_dataset(self, dataset_id: str, fields: List[Dict]):
        """Update dataset context."""
        self.dataset_context = DatasetContext(
            dataset_id=dataset_id,
            fields=fields
        )
    
    def update_operators(self, operators: List[Dict]):
        """Update operator context."""
        self.operator_context = OperatorContext(operators=operators)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "region": self.region,
            "universe": self.universe,
            "dataset_id": self.dataset_context.dataset_id,
            "fields_count": len(self.dataset_context.fields),
            "operators_count": len(self.operator_context.operators),
            "quality_thresholds": self.quality_thresholds,
        }
