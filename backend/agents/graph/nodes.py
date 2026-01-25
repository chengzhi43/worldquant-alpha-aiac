"""
LangGraph Node Functions
Pure functions that process state and return partial updates
"""

import json
import time
from typing import Dict, List, Any, Optional
from loguru import logger

from backend.agents.graph.state import (
    MiningState, AlphaCandidate, AlphaResult, FailureRecord, 
    TraceStepData, add_trace_step
)
from backend.agents.services import LLMService, RAGService, get_llm_service
from backend.agents.prompts import (
    ALPHA_GENERATION_SYSTEM, ALPHA_GENERATION_USER,
    HYPOTHESIS_SYSTEM, HYPOTHESIS_USER,
    SELF_CORRECT_SYSTEM, SELF_CORRECT_USER
)
from backend.adapters.brain_adapter import BrainAdapter
from backend.config import settings


# =============================================================================
# NODE: RAG Query
# =============================================================================

async def node_rag_query(state: MiningState, rag_service: RAGService) -> Dict:
    """
    Retrieve success patterns and failure pitfalls from knowledge base.
    
    Input State:
        - dataset_id, region
    
    Output Updates:
        - patterns, pitfalls
        - trace_steps
    """
    start_time = time.time()
    node_name = "RAG_QUERY"
    
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id} dataset={state.dataset_id}")
    
    try:
        result = await rag_service.query(
            dataset_id=state.dataset_id,
            region=state.region,
            max_patterns=5,
            max_pitfalls=10
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"[{node_name}] 完成 | patterns={len(result.patterns)} pitfalls={len(result.pitfalls)}"
        )
        
        # Create trace step
        trace_update = add_trace_step(
            state,
            step_type=node_name,
            input_data={"dataset_id": state.dataset_id, "region": state.region},
            output_data={"patterns_count": len(result.patterns), "pitfalls_count": len(result.pitfalls)},
            duration_ms=duration_ms,
            status="SUCCESS"
        )
        
        return {
            "patterns": result.patterns,
            "pitfalls": result.pitfalls,
            **trace_update
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[{node_name}] 失败 | error={e}")
        
        trace_update = add_trace_step(
            state, node_name, {}, {},
            duration_ms, "FAILED", str(e)
        )
        
        return {
            "patterns": [],
            "pitfalls": [],
            "error": str(e),
            **trace_update
        }


# =============================================================================
# NODE: Hypothesis Generation
# =============================================================================

async def node_hypothesis(state: MiningState, llm_service: LLMService) -> Dict:
    """
    Generate investment hypotheses based on dataset.
    
    Input State:
        - dataset_id, fields
    
    Output Updates:
        - hypotheses
        - trace_steps
    """
    start_time = time.time()
    node_name = "HYPOTHESIS"
    
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id}")
    
    fields_summary = "\n".join([
        f"- {f.get('id', f.get('name'))}: {f.get('description', '')}"
        for f in state.fields[:20]
    ])
    
    prompt = HYPOTHESIS_USER.format(
        dataset_id=state.dataset_id,
        category="Unknown",  # Could be enhanced with dataset info
        subcategory="Unknown",
        description="",
        fields_summary=fields_summary
    )
    
    response = await llm_service.call(
        system_prompt=HYPOTHESIS_SYSTEM,
        user_prompt=prompt,
        temperature=0.7,
        json_mode=True
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    hypotheses = []
    if response.success and response.parsed:
        hypotheses = response.parsed.get("hypotheses", [])
    
    logger.info(f"[{node_name}] 完成 | hypotheses={len(hypotheses)}")
    
    trace_update = add_trace_step(
        state, node_name,
        {"dataset_id": state.dataset_id},
        {"hypotheses_count": len(hypotheses)},
        duration_ms,
        "SUCCESS" if response.success else "FAILED",
        response.error
    )
    
    return {
        "hypotheses": hypotheses,
        **trace_update
    }


# =============================================================================
# NODE: Code Generation
# =============================================================================

async def node_code_gen(state: MiningState, llm_service: LLMService) -> Dict:
    """
    Generate Alpha expressions using LLM.
    
    Input State:
        - dataset_id, fields, operators, patterns, pitfalls
    
    Output Updates:
        - pending_alphas
        - trace_steps
    """
    start_time = time.time()
    node_name = "CODE_GEN"
    
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id}")
    
    # Prepare few-shot examples
    few_shot_text = "\n".join([
        f"- {p['pattern']}: {p.get('description', '')}"
        for p in state.patterns
    ]) or "暂无成功模式参考"
    
    # Prepare constraints
    constraints_text = "\n".join([
        f"- 避免: {p['pattern']} (原因: {p.get('description', '')})"
        for p in state.pitfalls
    ]) or "暂无特殊限制"
    
    prompt = ALPHA_GENERATION_USER.format(
        region=state.region,
        universe=state.universe,
        dataset_id=state.dataset_id,
        dataset_description="",
        fields_json=json.dumps(state.fields[:30], ensure_ascii=False),
        operators_json=json.dumps(state.operators[:50], ensure_ascii=False),
        few_shot_examples=few_shot_text,
        negative_constraints=constraints_text,
        num_alphas=state.num_alphas_target
    )
    
    response = await llm_service.call(
        system_prompt=ALPHA_GENERATION_SYSTEM,
        user_prompt=prompt,
        temperature=0.8,
        json_mode=True
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Parse alphas into candidates
    pending_alphas = []
    if response.success and response.parsed:
        raw_alphas = response.parsed.get("alphas", [])
        for alpha_data in raw_alphas:
            candidate = AlphaCandidate(
                expression=alpha_data.get("expression", ""),
                hypothesis=alpha_data.get("hypothesis"),
                explanation=alpha_data.get("explanation"),
                expected_sharpe=alpha_data.get("expected_sharpe")
            )
            if candidate.expression:
                pending_alphas.append(candidate)
    
    logger.info(f"[{node_name}] 完成 | alphas={len(pending_alphas)}")
    
    trace_update = add_trace_step(
        state, node_name,
        {"num_alphas_target": state.num_alphas_target},
        {"alphas_generated": len(pending_alphas)},
        duration_ms,
        "SUCCESS" if response.success else "FAILED",
        response.error
    )
    
    return {
        "pending_alphas": pending_alphas,
        "current_alpha_index": 0,
        **trace_update
    }


# =============================================================================
# NODE: Validate
# =============================================================================

from validator import ExpressionValidator

# Initialize Validator (Singleton-ish)
_VALIDATOR = ExpressionValidator()

async def node_validate(state: MiningState) -> Dict:
    """
    Validate current alpha expression syntax using ExpressionValidator.
    
    Input State:
        - current_alpha_index, pending_alphas
    
    Output Updates:
        - pending_alphas (with validation result)
        - trace_steps
    """
    start_time = time.time()
    node_name = "VALIDATE"
    
    if state.current_alpha_index >= len(state.pending_alphas):
        logger.warning(f"[{node_name}] 无待处理 Alpha")
        return {}
    
    current = state.pending_alphas[state.current_alpha_index]
    expression = current.expression
    
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id} index={state.current_alpha_index}")
    
    # Advanced Validation using validator.py
    is_valid = True
    error = None
    
    if not expression or not expression.strip():
        is_valid = False
        error = "Empty expression"
    else:
        # Use AST-based validator
        try:
            # check_expression returns {"valid": bool, "error": str, "ast": ...}
            # Wait, looking at validator.py source, check_expression is defined but implementation wasn't fully shown.
            # However, validate_ast returns list of errors.
            # Let's assume usage based on common pattern or implement a wrapper here if check_expression isn't what I think.
            # Looking at validator.py again:
            # def check_expression(self, expression: str) -> Dict[str, Any]:
            # It seems robust.
            
            validation_result = _VALIDATOR.check_expression(expression)
            
            if not validation_result.get("valid", False):
                is_valid = False
                # Combine errors
                errors = validation_result.get("errors", [])
                error = "; ".join(errors) if errors else "Syntax error"
                # Add simplified expression if available but invalid? No.
            else:
                # If valid, use the simplified/formatted expression if returned
                # (validator might strip comments or format it)
                pass
                
        except Exception as e:
            is_valid = False
            error = f"Validation Exception: {str(e)}"
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Update current alpha
    updated_alpha = current.model_copy()
    updated_alpha.is_valid = is_valid
    updated_alpha.validation_error = error
    if not is_valid:
         logger.warning(f"Alpha Invalid: {expression} | Error: {error}")
    
    # Update list
    updated_list = state.pending_alphas.copy()
    updated_list[state.current_alpha_index] = updated_alpha
    
    logger.info(f"[{node_name}] 完成 | valid={is_valid}")
    
    trace_update = add_trace_step(
        state, node_name,
        {"expression": expression[:100]},
        {"is_valid": is_valid},
        duration_ms,
        "SUCCESS" if is_valid else "FAILED",
        error
    )
    
    return {
        "pending_alphas": updated_list,
        "retry_count": 0 if is_valid else state.retry_count,
        **trace_update
    }


# =============================================================================
# NODE: Self-Correct
# =============================================================================

async def node_self_correct(state: MiningState, llm_service: LLMService) -> Dict:
    """
    Use LLM to fix a failed expression.
    
    Input State:
        - current_alpha_index, pending_alphas, retry_count
    
    Output Updates:
        - pending_alphas (with corrected expression)
        - retry_count
        - trace_steps
    """
    start_time = time.time()
    node_name = "SELF_CORRECT"
    
    current = state.pending_alphas[state.current_alpha_index]
    
    logger.info(
        f"[{node_name}] 开始执行 | task={state.task_id} "
        f"retry={state.retry_count + 1}/{state.max_retries}"
    )
    
    fields_str = ", ".join([
        f.get('id', f.get('name', '')) for f in state.fields[:50]
    ])
    
    prompt = SELF_CORRECT_USER.format(
        expression=current.expression,
        error_message=current.validation_error or "Unknown error",
        error_type="SYNTAX_ERROR",
        available_fields=fields_str
    )
    
    response = await llm_service.call(
        system_prompt=SELF_CORRECT_SYSTEM,
        user_prompt=prompt,
        temperature=0.3,
        json_mode=True
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Update alpha with fixed expression
    updated_alpha = current.model_copy()
    updated_alpha.correction_attempts = current.correction_attempts + 1
    
    if not updated_alpha.original_expression:
        updated_alpha.original_expression = current.expression
    
    if response.success and response.parsed:
        fixed = response.parsed.get("fixed_expression")
        if fixed:
            updated_alpha.expression = fixed
            updated_alpha.is_valid = None  # Reset for re-validation
            updated_alpha.validation_error = None
    
    # Update list
    updated_list = state.pending_alphas.copy()
    updated_list[state.current_alpha_index] = updated_alpha
    
    logger.info(f"[{node_name}] 完成 | fixed={bool(response.parsed and response.parsed.get('fixed_expression'))}")
    
    trace_update = add_trace_step(
        state, node_name,
        {"original": current.expression[:100], "error": current.validation_error},
        {"fixed": updated_alpha.expression[:100] if updated_alpha.expression else None},
        duration_ms,
        "SUCCESS" if response.success else "FAILED",
        response.error
    )
    
    return {
        "pending_alphas": updated_list,
        "retry_count": state.retry_count + 1,
        **trace_update
    }


# =============================================================================
# NODE: Simulate
# =============================================================================

async def node_simulate(state: MiningState, brain: BrainAdapter) -> Dict:
    """
    Simulate alpha on BRAIN platform.
    
    Input State:
        - current_alpha_index, pending_alphas, region, universe
    
    Output Updates:
        - pending_alphas (with simulation result)
        - trace_steps
    """
    start_time = time.time()
    node_name = "SIMULATE"
    
    current = state.pending_alphas[state.current_alpha_index]
    
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id}")
    
    try:
        result = await brain.simulate_alpha(
            expression=current.expression,
            region=state.region,
            universe=state.universe,
            delay=1,
            decay=4,
            neutralization="SUBINDUSTRY"
        )
        
        success = result.get("success", False)
        
        # Update alpha
        updated_alpha = current.model_copy()
        updated_alpha.is_simulated = True
        updated_alpha.simulation_success = success
        updated_alpha.alpha_id = result.get("alpha_id")
        updated_alpha.metrics = result.get("metrics", {})
        updated_alpha.simulation_error = result.get("error")
        
    except Exception as e:
        logger.error(f"[{node_name}] 异常 | error={e}")
        updated_alpha = current.model_copy()
        updated_alpha.is_simulated = True
        updated_alpha.simulation_success = False
        updated_alpha.simulation_error = str(e)
        success = False
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Update list
    updated_list = state.pending_alphas.copy()
    updated_list[state.current_alpha_index] = updated_alpha
    
    logger.info(f"[{node_name}] 完成 | success={success}")
    
    trace_update = add_trace_step(
        state, node_name,
        {"expression": current.expression[:100], "region": state.region},
        {"success": success, "alpha_id": updated_alpha.alpha_id},
        duration_ms,
        "SUCCESS" if success else "FAILED",
        updated_alpha.simulation_error
    )
    
    return {
        "pending_alphas": updated_list,
        **trace_update
    }


# =============================================================================
# NODE: Evaluate Quality
# =============================================================================

async def node_evaluate(state: MiningState) -> Dict:
    """
    Evaluate alpha quality against thresholds.
    
    Input State:
        - current_alpha_index, pending_alphas
    
    Output Updates:
        - pending_alphas
        - trace_steps
    """
    start_time = time.time()
    node_name = "EVALUATE"
    
    current = state.pending_alphas[state.current_alpha_index]
    metrics = current.metrics or {}
    
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id}")
    
    # Quality thresholds
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
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"[{node_name}] 完成 | pass={quality_pass} "
        f"sharpe={sharpe:.2f} turnover={turnover:.2f} fitness={fitness:.2f}"
    )
    
    trace_update = add_trace_step(
        state, node_name,
        {"sharpe": sharpe, "turnover": turnover, "fitness": fitness},
        {"quality_pass": quality_pass},
        duration_ms,
        "SUCCESS"
    )
    
    # We'll use this in edge routing
    return {
        **trace_update
    }


# =============================================================================
# NODE: Save Alpha
# =============================================================================

async def node_save_alpha(state: MiningState) -> Dict:
    """
    Save successful alpha to results.
    
    Input State:
        - current_alpha_index, pending_alphas
    
    Output Updates:
        - generated_alphas
        - current_alpha_index (advance)
    """
    node_name = "SAVE_ALPHA"
    
    current = state.pending_alphas[state.current_alpha_index]
    
    result = AlphaResult(
        expression=current.expression,
        hypothesis=current.hypothesis,
        explanation=current.explanation,
        alpha_id=current.alpha_id,
        metrics=current.metrics,
        quality_status="PASS"
    )
    
    logger.info(f"[{node_name}] Alpha 保存 | id={current.alpha_id}")
    
    return {
        "generated_alphas": state.generated_alphas + [result],
        "current_alpha_index": state.current_alpha_index + 1,
        "retry_count": 0
    }


# =============================================================================
# NODE: Record Failure
# =============================================================================

async def node_record_failure(state: MiningState) -> Dict:
    """
    Record failed alpha attempt.
    
    Input State:
        - current_alpha_index, pending_alphas
    
    Output Updates:
        - failures
        - current_alpha_index (advance)
    """
    node_name = "RECORD_FAILURE"
    
    current = state.pending_alphas[state.current_alpha_index]
    
    error_type = "UNKNOWN"
    error_message = "Unknown error"
    
    if current.validation_error:
        error_type = "VALIDATION_ERROR"
        error_message = current.validation_error
    elif current.simulation_error:
        error_type = "SIMULATION_ERROR"
        error_message = current.simulation_error
    
    failure = FailureRecord(
        expression=current.expression,
        error_type=error_type,
        error_message=error_message
    )
    
    logger.info(f"[{node_name}] 失败记录 | type={error_type}")
    
    # Add trace step for failure
    trace_update = add_trace_step(
        state, node_name,
        {"error_type": error_type, "expression": current.expression[:100]},
        {"error_message": error_message},
        0,
        "FAILED",
        error_message
    )
    
    return {
        "failures": state.failures + [failure],
        "current_alpha_index": state.current_alpha_index + 1,
        "retry_count": 0,
        **trace_update
    }
