"""
LangGraph Node Functions - Backward Compatibility Module

This module re-exports all node functions from the modular nodes/ package.
For new code, prefer importing directly from backend.agents.graph.nodes.

Node Organization:
- nodes/base.py: Common helpers (record_trace, _debug_log)
- nodes/generation.py: RAG query, hypothesis, code generation
- nodes/validation.py: Expression validation, self-correction
- nodes/evaluation.py: Simulation, quality evaluation
- nodes/persistence.py: Save results
"""

# Re-export everything from the nodes package for backward compatibility
from backend.agents.graph.nodes import (
    # Base utilities
    record_trace,
    _debug_log,
    EXPERIMENT_TRACKING_ENABLED,
    get_current_experiment,
    # Generation nodes
    node_rag_query,
    node_distill_context,
    node_hypothesis,
    node_code_gen,
    # Validation nodes
    node_validate,
    node_self_correct,
    # Evaluation nodes
    node_simulate,
    node_evaluate,
    # Persistence nodes
    node_save_results,
)

__all__ = [
    # Base
    "record_trace",
    "_debug_log",
    "EXPERIMENT_TRACKING_ENABLED",
    "get_current_experiment",
    # Generation
    "node_rag_query",
    "node_distill_context",
    "node_hypothesis",
    "node_code_gen",
    # Validation
    "node_validate",
    "node_self_correct",
    # Evaluation
    "node_simulate",
    "node_evaluate",
    # Persistence
    "node_save_results",
]
