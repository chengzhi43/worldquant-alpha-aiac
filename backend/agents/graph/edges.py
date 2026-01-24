"""
LangGraph Edge Functions
Conditional routing logic for the mining workflow
"""

from typing import Literal
from loguru import logger

from backend.agents.graph.state import MiningState
from backend.config import settings


# =============================================================================
# EDGE: After Validate
# =============================================================================

def route_after_validate(state: MiningState) -> Literal["simulate", "self_correct", "record_failure"]:
    """
    Route after validation step.
    
    - If valid: proceed to simulate
    - If invalid and retries available: go to self-correct
    - If max retries reached: record failure
    """
    current = state.pending_alphas[state.current_alpha_index]
    
    if current.is_valid:
        logger.debug("[Edge] route_after_validate -> simulate")
        return "simulate"
    
    if state.retry_count < state.max_retries:
        logger.debug(f"[Edge] route_after_validate -> self_correct (retry {state.retry_count + 1}/{state.max_retries})")
        return "self_correct"
    
    logger.debug("[Edge] route_after_validate -> record_failure (max retries)")
    return "record_failure"


# =============================================================================
# EDGE: After Self-Correct
# =============================================================================

def route_after_self_correct(state: MiningState) -> Literal["validate", "record_failure"]:
    """
    Route after self-correction.
    
    - If correction succeeded: go back to validate
    - If still failing: record failure
    """
    current = state.pending_alphas[state.current_alpha_index]
    
    # Check if we have a new expression
    if current.expression and current.expression != current.original_expression:
        logger.debug("[Edge] route_after_self_correct -> validate")
        return "validate"
    
    logger.debug("[Edge] route_after_self_correct -> record_failure")
    return "record_failure"


# =============================================================================
# EDGE: After Simulate
# =============================================================================

def route_after_simulate(state: MiningState) -> Literal["evaluate", "record_failure"]:
    """
    Route after simulation.
    
    - If simulation succeeded: evaluate quality
    - If failed: record failure
    """
    current = state.pending_alphas[state.current_alpha_index]
    
    if current.simulation_success:
        logger.debug("[Edge] route_after_simulate -> evaluate")
        return "evaluate"
    
    logger.debug("[Edge] route_after_simulate -> record_failure")
    return "record_failure"


# =============================================================================
# EDGE: After Evaluate
# =============================================================================

def route_after_evaluate(state: MiningState) -> Literal["save_alpha", "record_failure"]:
    """
    Route after quality evaluation.
    
    - If passes quality thresholds: save alpha
    - If rejected: record failure (or save with REJECT status)
    """
    current = state.pending_alphas[state.current_alpha_index]
    metrics = current.metrics or {}
    
    sharpe = metrics.get("sharpe") or 0
    turnover = metrics.get("turnover") or 0
    fitness = metrics.get("fitness") or 0
    
    sharpe_min = getattr(settings, 'SHARPE_MIN', 1.5)
    turnover_max = getattr(settings, 'TURNOVER_MAX', 0.7)
    fitness_min = getattr(settings, 'FITNESS_MIN', 0.6)
    
    quality_pass = (
        sharpe >= sharpe_min and
        turnover <= turnover_max and
        fitness >= fitness_min
    )
    
    if quality_pass:
        logger.debug(f"[Edge] route_after_evaluate -> save_alpha (sharpe={sharpe:.2f})")
        return "save_alpha"
    
    logger.debug(f"[Edge] route_after_evaluate -> record_failure (sharpe={sharpe:.2f} < {sharpe_min})")
    return "record_failure"


# =============================================================================
# EDGE: Check More Alphas
# =============================================================================

def route_next_alpha(state: MiningState) -> Literal["validate", "end"]:
    """
    Check if there are more alphas to process.
    
    - If more pending: loop back to validate
    - If done: end
    """
    if state.current_alpha_index < len(state.pending_alphas):
        logger.debug(f"[Edge] route_next_alpha -> validate (index={state.current_alpha_index}/{len(state.pending_alphas)})")
        return "validate"
    
    logger.debug("[Edge] route_next_alpha -> end")
    return "end"


# =============================================================================
# EDGE: Error Check
# =============================================================================

def route_check_error(state: MiningState) -> Literal["continue", "error"]:
    """
    Check if there's a critical error that should stop execution.
    """
    if state.should_stop or state.error:
        logger.warning(f"[Edge] route_check_error -> error: {state.error}")
        return "error"
    
    return "continue"
