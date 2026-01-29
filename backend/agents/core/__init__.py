"""
Core abstractions for Alpha Mining based on RD-Agent architecture.

This module provides:
- Experiment: Complete experiment record with hypothesis, result, feedback
- EvoStep: Evolution step linking experiment, knowledge, and feedback  
- Trace: DAG-structured experiment history with parent-child relationships
- Feedback: Structured experiment feedback with hypothesis evaluation and attribution
- Knowledge: Evolving knowledge base with automatic rule extraction
- Scenario: Task context including dataset, operators, and quality thresholds
- Pipeline: Clear component interfaces (HypothesisGen, Hypothesis2Experiment, Experiment2Feedback)

Design Principles (from RD-Agent):
1. Clear separation of concerns - each component has single responsibility
2. Traceable experiment lineage - know what led to each experiment
3. Knowledge evolution from experiments - learn from successes and failures
4. Attribution-aware feedback - distinguish hypothesis failures from implementation errors
5. No preconceived biases - let evidence guide conclusions
"""

# Experiment types
from backend.agents.core.experiment import (
    Hypothesis,
    AlphaExperiment,
    EvoStep,
    ExperimentStatus,
    RunningInfo,
)

# Feedback types
from backend.agents.core.feedback import (
    HypothesisFeedback,
    AttributionType,
)

# Trace management
from backend.agents.core.trace import (
    ExperimentTrace,
    TraceNode,
)

# Knowledge management
from backend.agents.core.knowledge import (
    KnowledgeRule,
    KnowledgeType,
    QueriedKnowledge,
    EvolvingKnowledge,
)

# Scenario context
from backend.agents.core.scenario import (
    Scenario,
    AlphaMiningScenario,
    DatasetContext,
    OperatorContext,
)

# Pipeline components
from backend.agents.core.pipeline import (
    HypothesisGen,
    LLMHypothesisGen,
    Hypothesis2Experiment,
    LLMHypothesis2Experiment,
    ExperimentRunner,
    BRAINExperimentRunner,
    Experiment2Feedback,
    LLMExperiment2Feedback,
    AlphaMiningPipeline,
    PipelineResult,
)

# Evolving RAG
from backend.agents.core.evolving_rag import (
    AlphaKnowledge,
    EnhancedQueriedKnowledge,
    EvolvingRAGStrategy,
    AlphaRAGStrategy,
    create_alpha_rag_strategy,
)

# Integration helpers
from backend.agents.core.integration import (
    create_scenario,
    create_alpha_pipeline,
    create_trace,
    experiment_to_alpha_result,
    state_to_trace,
    run_enhanced_mining,
    enhance_existing_node_evaluate,
    EnhancedMiningResult,
)

__all__ = [
    # Experiment
    "Hypothesis",
    "AlphaExperiment", 
    "EvoStep",
    "ExperimentStatus",
    "RunningInfo",
    
    # Feedback
    "HypothesisFeedback",
    "AttributionType",
    
    # Trace
    "ExperimentTrace",
    "TraceNode",
    
    # Knowledge
    "KnowledgeRule",
    "KnowledgeType",
    "QueriedKnowledge",
    "EvolvingKnowledge",
    
    # Scenario
    "Scenario",
    "AlphaMiningScenario",
    "DatasetContext",
    "OperatorContext",
    
    # Pipeline
    "HypothesisGen",
    "LLMHypothesisGen",
    "Hypothesis2Experiment",
    "LLMHypothesis2Experiment",
    "ExperimentRunner",
    "BRAINExperimentRunner",
    "Experiment2Feedback",
    "LLMExperiment2Feedback",
    "AlphaMiningPipeline",
    "PipelineResult",
    
    # Evolving RAG
    "AlphaKnowledge",
    "EnhancedQueriedKnowledge",
    "EvolvingRAGStrategy",
    "AlphaRAGStrategy",
    "create_alpha_rag_strategy",
    
    # Integration
    "create_scenario",
    "create_alpha_pipeline",
    "create_trace",
    "experiment_to_alpha_result",
    "state_to_trace",
    "run_enhanced_mining",
    "enhance_existing_node_evaluate",
    "EnhancedMiningResult",
]
