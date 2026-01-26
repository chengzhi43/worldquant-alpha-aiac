"""
LangGraph Node Functions
Pure functions that process state and return partial updates
"""

import json
import time
import random
from typing import Dict, List, Any, Optional
from loguru import logger
from langchain_core.runnables import RunnableConfig

from backend.agents.graph.state import (
    MiningState, AlphaCandidate, AlphaResult, FailureRecord, 
    TraceStepData, add_trace_step, merge_state
)
from backend.agents.services import LLMService, RAGService, get_llm_service
from backend.agents.services.trace_service import TraceService, TraceStepRecord
from backend.agents.prompts import (
    ALPHA_GENERATION_SYSTEM, ALPHA_GENERATION_USER,
    HYPOTHESIS_SYSTEM, HYPOTHESIS_USER,
    SELF_CORRECT_SYSTEM, SELF_CORRECT_USER,
    DISTILL_SYSTEM, DISTILL_USER
)
from backend.adapters.brain_adapter import BrainAdapter
from backend.config import settings


# =============================================================================
# HELPER: Real-Time Trace + State Update
# =============================================================================

async def record_trace(
    state: MiningState,
    trace_service: Optional[TraceService],
    step_type: str,
    input_data: Dict = None,
    output_data: Dict = None,
    duration_ms: int = 0,
    status: str = "SUCCESS",
    error_message: str = None
) -> Dict:
    """Helper to update state AND persist trace to DB immediately."""
    
    # 1. Update In-Memory State (Pydantic)
    state_update = add_trace_step(
        state, step_type, input_data, output_data, duration_ms, status, error_message
    )
    
    # 2. Persist to DB (Real-Time)
    if trace_service:
        try:
            # Note: TraceService manages its own step_order counter if used via create_record,
            # but here we want to sync with State if possible.
            # However, persistence usually just needs the data.
            # We construct record manually to ensure we commit exactly what's in state.
            
            # Use state.step_order + 1 as that's what add_trace_step uses
            step_order = state.step_order + 1
            
            record = TraceStepRecord(
                step_type=step_type,
                step_order=step_order,
                input_data=input_data or {},
                output_data=output_data or {},
                duration_ms=duration_ms,
                status=status,
                error_message=error_message
            )
            await trace_service.persist_record(record)
        except Exception as e:
            logger.error(f"Failed to persist trace step: {e}")
            
    return state_update


# =============================================================================
# NODE: RAG Query
# =============================================================================

async def node_rag_query(state: MiningState, rag_service: RAGService, config: RunnableConfig = None) -> Dict:
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
    
    # Extract TraceService
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
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
        # Create trace step
        trace_update = await record_trace(
            state,
            trace_service,
            step_type=node_name,
            input_data={"dataset_id": state.dataset_id, "region": state.region},
            output_data={
                "patterns_count": len(result.patterns), 
                "pitfalls_count": len(result.pitfalls),
                "top_patterns": [p['pattern'] for p in result.patterns[:3]],
                "top_pitfalls": [p['pattern'] for p in result.pitfalls[:3]]
            },
            duration_ms=duration_ms,
            status="SUCCESS"
        )
        
        # Extract dataset metadata
        ds_info = result.dataset_info or {}
        description = ds_info.get("description", "")
        category = ds_info.get("category", "Unknown")
        subcategory = ds_info.get("subcategory", "")
        full_category = f"{category} > {subcategory}" if subcategory else category
        
        return {
            "patterns": result.patterns,
            "pitfalls": result.pitfalls,
            "dataset_description": description,
            "dataset_category": full_category,
            **trace_update
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[{node_name}] 失败 | error={e}")
        
        trace_update = await record_trace(
            state, trace_service, node_name, {}, {},
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

async def node_distill_context(state: MiningState, llm_service: LLMService, config: RunnableConfig = None) -> Dict:
    """
    Distill relevant concepts/categories from large field sets.
    
    Input State:
        - fields, dataset_description
        
    Output Updates:
        - distilled_concepts
        - focused_fields
        - trace_steps
    """
    start_time = time.time()
    node_name = "DISTILL_CONTEXT"
    
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id} fields={len(state.fields)}")
    
    # 1. Group fields by category
    categories = {}
    for f in state.fields:
        cat = f.get("category") or "General"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f.get("id", f.get("name")))
        
    # Format for prompt (limit sample size per category to avoid overflowing context)
    categories_text = []
    for cat, f_list in categories.items():
        sample = ", ".join(f_list[:5])
        suffix = f"... ({len(f_list)-5} more)" if len(f_list) > 5 else ""
        categories_text.append(f"- **{cat}**: {sample}{suffix}")
    
    field_categories_str = "\n".join(categories_text)
    
    # 2. Call LLM to select concepts
    success_patterns_text = "\n".join([
        f"- {p.get('pattern', '')}" for p in state.patterns[:3]
    ]) or "暂无"
    
    prompt = DISTILL_USER.format(
        dataset_id=state.dataset_id,
        description=state.dataset_description or "暂无",
        category=state.dataset_category or "Unknown",
        success_patterns=success_patterns_text,
        field_categories=field_categories_str
    )
    
    response = await llm_service.call(
        system_prompt=DISTILL_SYSTEM,
        user_prompt=prompt,
        temperature=0.5, # Lower temp for classification
        json_mode=True
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    selected_concepts = []
    reasoning = ""
    focused_fields = []
    
    if response.success and response.parsed:
        selected_concepts = response.parsed.get("selected_concepts", [])
        reasoning = response.parsed.get("reasoning", "")
        
        # Filter fields
        # Loose matching: if category contains the selected concept key word
        full_field_list = state.fields
        
        # Log match attempts for debugging
        logger.info(f"[{node_name}] Available Categories: {list(categories.keys())}")
        logger.info(f"[{node_name}] LLM Selected: {selected_concepts}")
        
        # Exact or partial match strategy
        for f in full_field_list:
            f_cat = f.get("category") or "General"
            # If any selected concept is a substring of category (or vice versa)
            if any(c.lower() in f_cat.lower() or f_cat.lower() in c.lower() for c in selected_concepts):
                focused_fields.append(f)
                
    # Fallback: if distillation failed or returned 0, use top 30 fields
    if not focused_fields:
        logger.warning(
            f"[{node_name}] Distillation yielded 0 fields (Selection: {selected_concepts} vs Available: {list(categories.keys())}). Falling back to top 30."
        )
        focused_fields = state.fields[:30]
        
    logger.info(f"[{node_name}] 完成 | concepts={selected_concepts} focused={len(focused_fields)}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"field_count": len(state.fields), "categories": list(categories.keys())},
        {
            "selected_concepts": selected_concepts,
            "focused_count": len(focused_fields),
            "reasoning": reasoning
        },
        duration_ms,
        "SUCCESS" if response.success else "FAILED",
        response.error
    )
    
    return {
        "distilled_concepts": selected_concepts,
        "focused_fields": focused_fields,
        **trace_update
    }
async def node_hypothesis(state: MiningState, llm_service: LLMService, config: RunnableConfig = None) -> Dict:
    """
    Generate investment hypotheses based on dataset using Hybrid Strategy.
    
    Strategy:
    1. Exploitation: Use success patterns and semantic metadata.
    2. Exploration: Force use of random/low-frequency fields.
    
    Input State:
        - dataset_id, fields, patterns, dataset_description
    
    Output Updates:
        - hypotheses
        - trace_steps
    """
    start_time = time.time()
    node_name = "HYPOTHESIS"
    
    # Extract TraceService
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    logger.info(f"[{node_name}] 开始执行 | task={state.task_id}")
    
    # 1. Prepare Fields Context (Summary of first 20)
    # Use focused_fields if available (from Concept Distillation), else top 20 raw fields
    target_fields = state.focused_fields if state.focused_fields else state.fields[:20]
    
    fields_summary = "\n".join([
        f"- {f.get('id', f.get('name'))}: {f.get('description', '')}"
        for f in target_fields[:20] # Limit to 20 even if focused has more
    ])
    
    # 2. Select Exploration Fields (Random 3 from full list)
    exploration_fields = []
    
    # Try to pick from non-focused fields first for true exploration
    remaining_fields = [f for f in state.fields if f not in target_fields]
    if len(remaining_fields) >= 3:
         exploration_fields = random.sample(remaining_fields, 3)
    elif len(state.fields) > 5:
        exploration_fields = random.sample(state.fields, min(3, len(state.fields)))
    else:
        exploration_fields = state.fields
        
    exploration_text = "\n".join([
        f"- {f.get('id', f.get('name'))}: {f.get('description', '')}"
        for f in exploration_fields
    ]) or "暂无额外探索字段"

    # 3. Prepare RAG Pattern Context
    success_patterns_text = "\n".join([
        f"- [Pattern] {p.get('pattern', '')}: {p.get('description', '')}"
        for p in state.patterns[:3]
    ]) or "暂无直接参考模式"

    prompt = HYPOTHESIS_USER.format(
        dataset_id=state.dataset_id,
        category=state.dataset_category or "Unknown", 
        subcategory="", # Merged into category in state
        description=state.dataset_description or "暂无详细描述",
        fields_summary=fields_summary,
        success_patterns=success_patterns_text,
        exploration_fields=exploration_text
    )
    
    # Higher temperature for creativity
    response = await llm_service.call(
        system_prompt=HYPOTHESIS_SYSTEM,
        user_prompt=prompt,
        temperature=0.9, 
        json_mode=True
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    hypotheses = []
    if response.success and response.parsed:
        hypotheses = response.parsed.get("hypotheses", [])
    
    logger.info(f"[{node_name}] 完成 | hypotheses={len(hypotheses)}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"dataset_id": state.dataset_id, "mode": "Hybrid (Exploit+Explore)"},
        {
            "hypotheses_count": len(hypotheses), 
            "hypotheses": hypotheses[:3],
            "exploration_candidates": [f.get('id') for f in exploration_fields]
        },
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

async def node_code_gen(state: MiningState, llm_service: LLMService, config: RunnableConfig = None) -> Dict:
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
    
    # Extract TraceService
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
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
    
    # Prepare hypotheses context
    hypotheses_text = "\n".join([
        f"ID {i+1}: {h.get('idea', h) if isinstance(h, dict) else h}" 
        for i, h in enumerate(state.hypotheses)
    ]) or "暂无特定假设"

    prompt = ALPHA_GENERATION_USER.format(
        region=state.region,
        universe=state.universe,
        dataset_id=state.dataset_id,
        dataset_description="",
        fields_json=json.dumps(state.fields[:30], ensure_ascii=False),
        operators_json=json.dumps(state.operators[:50], ensure_ascii=False),
        few_shot_examples=few_shot_text,
        hypotheses_context=hypotheses_text,
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
            # Capture hypothesis_id if available to link back
            h_id = alpha_data.get("hypothesis_id")
            hypothesis_text = alpha_data.get("hypothesis")
            
            # If ID is present, prepend to hypothesis text for visibility
            final_hypothesis = hypothesis_text
            if h_id:
                final_hypothesis = f"[H{h_id}] {hypothesis_text}"
                
            candidate = AlphaCandidate(
                expression=alpha_data.get("expression", ""),
                hypothesis=final_hypothesis,
                explanation=alpha_data.get("explanation"),
                expected_sharpe=alpha_data.get("expected_sharpe")
            )
            if candidate.expression:
                pending_alphas.append(candidate)
    
    logger.info(f"[{node_name}] 完成 | alphas={len(pending_alphas)}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"num_alphas_target": state.num_alphas_target},
        {
            "alphas_generated": len(pending_alphas),
            "expressions": [a.expression[:200] for a in pending_alphas]
        },
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

async def node_validate(state: MiningState, config: RunnableConfig = None) -> Dict:
    """
    Batch validate ALL pending alpha expressions.
    
    Input State:
        - pending_alphas
    
    Output Updates:
        - pending_alphas (with validation result)
        - trace_steps
    """
    start_time = time.time()
    node_name = "VALIDATE"
    
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    updated_alphas = []
    valid_count = 0
    errors = []
    
    logger.info(f"[{node_name}] 开始批量校验 | count={len(state.pending_alphas)}")
    
    for alpha in state.pending_alphas:
        expression = alpha.expression
        is_valid = True
        error = None
        
        if not expression or not expression.strip():
            is_valid = False
            error = "Empty expression"
        else:
            try:
                # Use validator
                # Extract allowed field IDs (handle both dict with 'id'/'name' and raw strings if any)
                allowed_fields = []
                for f in state.fields:
                    if isinstance(f, dict):
                        allowed_fields.append(f.get("id", f.get("name")))
                    else:
                        allowed_fields.append(str(f))
                
                validation_result = _VALIDATOR.check_expression(expression, allowed_fields=allowed_fields)
                if not validation_result.get("valid", False):
                    is_valid = False
                    err_list = validation_result.get("errors", [])
                    error = "; ".join(err_list) if err_list else "Syntax error"
            except Exception as e:
                is_valid = False
                error = f"Validation Exception: {str(e)}"
        
        updated_alpha = alpha.model_copy()
        updated_alpha.is_valid = is_valid
        updated_alpha.validation_error = error
        
        if is_valid:
            valid_count += 1
        else:
            errors.append(f"{expression[:50]}... -> {error}")
            
        updated_alphas.append(updated_alpha)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(f"[{node_name}] 完成 | valid={valid_count}/{len(updated_alphas)}")
    if errors:
        logger.warning(f"[{node_name}] Errors: {errors[:3]}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"count": len(updated_alphas)},
        {
            "valid_count": valid_count, 
            "invalid_count": len(updated_alphas) - valid_count,
            "failures": [
                {"expression": a.expression, "error": a.validation_error}
                for a in updated_alphas if not a.is_valid
            ]
        },
        duration_ms,
        "SUCCESS"
    )
    
    return {
        "pending_alphas": updated_alphas,
        **trace_update
    }


# =============================================================================
# NODE: Self-Correct
# =============================================================================

async def node_self_correct(state: MiningState, llm_service: LLMService, config: RunnableConfig = None) -> Dict:
    """
    Batch attempt to fix ALL invalid alphas.
    
    Input State:
        - pending_alphas
        - retry_count
    
    Output Updates:
        - pending_alphas (updated)
        - retry_count
    """
    start_time = time.time()
    node_name = "SELF_CORRECT"
    
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    # Identify invalid alphas that haven't exceeded attempts (if we tracked per-alpha attempts, but state has global retry_count)
    # We will treat state.retry_count as a global "pass" count.
    
    invalid_indices = [
        i for i, a in enumerate(state.pending_alphas) 
        if not a.is_valid
    ]
    
    if not invalid_indices:
        logger.info(f"[{node_name}] 没有需要修复的 Alpha")
        return {"retry_count": state.retry_count + 1}
        
    logger.info(f"[{node_name}] 开始批量修复 | count={len(invalid_indices)} pass={state.retry_count + 1}")

    fields_str = ", ".join([
        f.get('id', f.get('name', '')) for f in state.fields[:50]
    ])
    
    updated_alphas = state.pending_alphas.copy()
    fixed_count = 0
    
    # Track corrections for trace
    corrections_made = []
    
    # Process sequentially for now to avoid complexity/rate limits
    # Could be parallelized with asyncio.gather if needed
    for idx in invalid_indices:
        current = state.pending_alphas[idx]
        
        prompt = SELF_CORRECT_USER.format(
            expression=current.expression,
            error_message=current.validation_error or "Unknown error",
            error_type="SYNTAX_ERROR",
            available_fields=fields_str
        )
        
        try:
            response = await llm_service.call(
                system_prompt=SELF_CORRECT_SYSTEM,
                user_prompt=prompt,
                temperature=0.3,
                json_mode=True
            )
            
            # Update alpha
            updated_alpha = current.model_copy()
            updated_alpha.correction_attempts += 1
            if not updated_alpha.original_expression:
                updated_alpha.original_expression = current.expression
                
            if response.success and response.parsed:
                fixed = response.parsed.get("fixed_expression")
                if fixed:
                    corrections_made.append({
                        "original": current.expression,
                        "fixed": fixed,
                        "error": current.validation_error
                    })
                    updated_alpha.expression = fixed
                    updated_alpha.is_valid = None # Reset for re-validation
                    updated_alpha.validation_error = None
                    fixed_count += 1
            
            updated_alphas[idx] = updated_alpha
            
        except Exception as e:
            logger.error(f"[{node_name}] Fix failed for index {idx}: {e}")

    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(f"[{node_name}] 完成 | fixed_attempts={fixed_count}/{len(invalid_indices)}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"fix_targets": len(invalid_indices)},
        {
            "fixed_count": fixed_count,
            "corrections": corrections_made
        },
        duration_ms,
        "SUCCESS"
    )
    
    return {
        "pending_alphas": updated_alphas,
        "retry_count": state.retry_count + 1,
        **trace_update
    }


# =============================================================================
# NODE: Simulate
# =============================================================================

async def node_simulate(state: MiningState, brain: BrainAdapter, config: RunnableConfig = None) -> Dict:
    """
    Batch simulate ALL valid alphas on BRAIN platform.
    
    Input State:
        - pending_alphas, region, universe
    
    Output Updates:
        - pending_alphas (with simulation result)
        - trace_steps
    """
    start_time = time.time()
    node_name = "SIMULATE"
    
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    # Filter valid alphas that haven't been simulated successfully yet
    valid_indices = [
        i for i, a in enumerate(state.pending_alphas)
        if a.is_valid and not a.simulation_success
    ]
    
    if not valid_indices:
        logger.warning(f"[{node_name}] 无待模拟的有效 Alpha")
        return {}
        
    logger.info(f"[{node_name}] 开始批量模拟 | count={len(valid_indices)} region={state.region}")
    
    expressions = [state.pending_alphas[i].expression for i in valid_indices]
    
    try:
        # returns list of dicts: [{"success": True, "alpha_id": ...}, ...]
        results = await brain.simulate_batch(
            expressions=expressions,
            region=state.region,
            universe=state.universe,
            delay=1,
            decay=4,
            neutralization="SUBINDUSTRY"
        )
        
    except Exception as e:
        logger.error(f"[{node_name}] Batch Simulate Loop Error: {e}")
        # Fail all if batch call crashes hard (unlikely if adapter handles it)
        results = [{"success": False, "error": str(e)} for _ in expressions]

    duration_ms = int((time.time() - start_time) * 1000)
    
    # Update alphas
    updated_alphas = state.pending_alphas.copy()
    success_count = 0
    
    for i, idx in enumerate(valid_indices):
        res = results[i] if i < len(results) else {"success": False, "error": "Missing result"}
        
        current = updated_alphas[idx]
        updated = current.model_copy()
        
        updated.is_simulated = True
        updated.simulation_success = res.get("success", False)
        updated.alpha_id = res.get("alpha_id")
        updated.metrics = res.get("metrics", {})
        updated.simulation_error = res.get("error")
        
        if updated.simulation_success:
            success_count += 1
            
        updated_alphas[idx] = updated
        
    logger.info(f"[{node_name}] 完成 | success={success_count}/{len(valid_indices)}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"batch_size": len(valid_indices), "expressions": [e[:50] for e in expressions]},
        {
            "success_count": success_count, 
            "results": [{"id": r.get("alpha_id"), "metrics": r.get("metrics"), "err": r.get("error")} for r in results]
        },
        duration_ms,
        "SUCCESS" if success_count > 0 else "PARTIAL_FAILURE"
    )
    
    return {
        "pending_alphas": updated_alphas,
        **trace_update
    }


# =============================================================================
# NODE: Evaluate Quality
# =============================================================================

async def node_evaluate(state: MiningState, config: RunnableConfig = None) -> Dict:
    """
    Batch evaluate alpha quality against thresholds for all simulated alphas.
    
    Input State:
        - pending_alphas
    
    Output Updates:
        - pending_alphas (with quality_status)
        - trace_steps
    """
    start_time = time.time()
    node_name = "EVALUATE"
    
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    updated_alphas = state.pending_alphas.copy()
    pass_count = 0
    fail_count = 0
    
    logger.info(f"[{node_name}] 开始批量评估 | count={len(state.pending_alphas)}")
    
    sharpe_min = getattr(settings, 'SHARPE_MIN', 1.5)
    turnover_max = getattr(settings, 'TURNOVER_MAX', 0.7)
    fitness_min = getattr(settings, 'FITNESS_MIN', 0.6)
    
    eval_details = []
    
    for i, alpha in enumerate(updated_alphas):
        # Skip if not simulated successfully
        if not alpha.is_simulated or not alpha.simulation_success:
            if alpha.quality_status == "PENDING":
                 alpha.quality_status = "FAIL" # Mark as fail if it failed valid/sim steps
            continue
            
        metrics = alpha.metrics or {}
        sharpe = metrics.get("sharpe") or 0
        turnover = metrics.get("turnover") or 0
        fitness = metrics.get("fitness") or 0
        
        quality_pass = (
            sharpe >= sharpe_min and
            turnover <= turnover_max and
            fitness >= fitness_min
        )
        
        alpha.quality_status = "PASS" if quality_pass else "FAIL"
        
        if quality_pass:
            pass_count += 1
        else:
            fail_count += 1
            
        eval_details.append({
            "id": alpha.alpha_id,
            "pass": quality_pass,
            "sharpe": sharpe,
            "returns": metrics.get("returns"),
            "turnover": turnover,
            "fitness": fitness,
        })
        
        updated_alphas[i] = alpha
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"[{node_name}] 完成 | pass={pass_count} fail={fail_count}"
    )
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"thresholds": f"SR>{sharpe_min}, TO<{turnover_max}"},
        {"pass_count": pass_count, "fail_count": fail_count, "details": eval_details},
        duration_ms,
        "SUCCESS"
    )
    
    return {
        "pending_alphas": updated_alphas,
        **trace_update
    }


# =============================================================================
# NODE: Save Alpha
# =============================================================================

async def node_save_results(state: MiningState, config: RunnableConfig = None) -> Dict:
    """
    Batch process and save ALL results (Successes and Failures).
    
    Input State:
        - pending_alphas
    
    Output Updates:
        - generated_alphas (appends successes)
        - failures (appends failures)
        - pending_alphas (cleared)
        - trace_steps
    """
    node_name = "SAVE_RESULTS"
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    success_batch = []
    fail_batch = []
    
    logger.info(f"[{node_name}] 开始批量保存结果 | total={len(state.pending_alphas)}")
    
    for alpha in state.pending_alphas:
        if alpha.quality_status == "PASS":
            res = AlphaResult(
                expression=alpha.expression,
                hypothesis=alpha.hypothesis,
                explanation=alpha.explanation,
                alpha_id=alpha.alpha_id,
                metrics=alpha.metrics,
                quality_status="PASS"
            )
            success_batch.append(res)
            logger.info(f"[{node_name}] Alpha Saved | id={alpha.alpha_id}")
            
        else:
            # Determine error type and message
            err_type = "UNKNOWN"
            err_msg = "Unknown error"
            
            if alpha.is_valid is False:
                err_type = "SYNTAX_ERROR"
                err_msg = alpha.validation_error or "Syntax Error"
            elif alpha.is_simulated and not alpha.simulation_success:
                err_type = "SIMULATION_ERROR"
                err_msg = alpha.simulation_error or "Simulation Failed"
            elif alpha.quality_status == "FAIL":
                err_type = "QUALITY_CHECK_FAILED"
                err_msg = "Metrics below threshold"
            else:
                err_type = "OTHER"
                err_msg = "Unknown failure"
                
            rec = FailureRecord(
                expression=alpha.expression,
                error_type=err_type,
                error_message=err_msg,
                details={"metrics": alpha.metrics, "hypothesis": alpha.hypothesis}
            )
            fail_batch.append(rec)
    
    # Trace
    if trace_service:
        await record_trace(
            state, trace_service, node_name,
            {},
            {"saved": len(success_batch), "failed": len(fail_batch)},
            0,
            "SUCCESS",
            None
        )
            
    return {
        "generated_alphas": state.generated_alphas + success_batch,
        "failures": state.failures + fail_batch,
        "pending_alphas": [], # Clear pending processing queue
        "current_alpha_index": 0 # Reset index
    }
