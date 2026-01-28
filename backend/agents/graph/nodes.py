"""
LangGraph Node Functions
Pure functions that process state and return partial updates
"""

import json
import time
import random
import os  # #region agent log
from typing import Dict, List, Any, Optional
from loguru import logger
from langchain_core.runnables import RunnableConfig

# #region agent log
def _debug_log(hypo_id, location, message, data=None):
    try:
        log_path = r"e:\AIACV2_v1.2\worldquant-alpha-aiac\.cursor\debug.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        entry = {"hypothesisId": hypo_id, "location": location, "message": message, "data": data or {}, "timestamp": int(time.time()*1000), "sessionId": "debug-session"}
        with open(log_path, "a", encoding="utf-8") as f: f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except: pass
# #endregion

from backend.agents.graph.state import (
    MiningState, AlphaCandidate, AlphaResult, FailureRecord, 
    TraceStepData, add_trace_step, merge_state
)
from backend.agents.services import LLMService, RAGService, get_llm_service
from backend.agents.services.trace_service import TraceService, TraceStepRecord
from backend.agents.prompts import (
    # System prompts
    ALPHA_GENERATION_SYSTEM,
    HYPOTHESIS_SYSTEM,
    DISTILL_SYSTEM,
    SELF_CORRECT_SYSTEM,
    # Legacy user templates (for backward compatibility)
    ALPHA_GENERATION_USER,
    HYPOTHESIS_USER,
    DISTILL_USER,
    SELF_CORRECT_USER,
    # New builder functions (preferred)
    build_alpha_generation_prompt,
    build_hypothesis_prompt,
    build_distill_prompt,
    build_self_correct_prompt,
    PromptContext,
)
from backend.adapters.brain_adapter import BrainAdapter
from backend.config import settings

# Observability: Import experiment tracker for metrics collection
try:
    from backend.experiment_tracker import get_current_experiment, MetricsCollector
    EXPERIMENT_TRACKING_ENABLED = True
except ImportError:
    EXPERIMENT_TRACKING_ENABLED = False
    get_current_experiment = lambda: None


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
        # #region agent log
        _debug_log("C", "nodes.py:rag_query:result", "RAG query complete", {
            "patterns_count": len(result.patterns), 
            "pitfalls_count": len(result.pitfalls), 
            "duration_ms": duration_ms, 
            "dataset_id": state.dataset_id,
            "patterns_datasets": [p.get('metadata', {}).get('dataset', 'generic') for p in result.patterns],
            "top_patterns": [p.get('pattern','')[:50] for p in result.patterns[:3]]
        })
        # #endregion
        
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
    
    # P1-fix-2: Enhanced error handling for LLM response parsing
    try:
        response = await llm_service.call(
            system_prompt=DISTILL_SYSTEM,
            user_prompt=prompt,
            temperature=0.5, # Lower temp for classification
            json_mode=True
        )
    except Exception as llm_err:
        logger.error(f"[{node_name}] LLM call failed: {llm_err}")
        response = type('obj', (object,), {'success': False, 'parsed': None, 'error': str(llm_err)})()
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    selected_concepts = []
    reasoning = ""
    focused_fields = []
    
    # P1-fix-2: Robust parsing with multiple fallbacks
    if response.success and response.parsed:
        try:
            parsed = response.parsed
            # Handle both dict and potential None
            if isinstance(parsed, dict):
                selected_concepts = parsed.get("selected_concepts", []) or []
                reasoning = parsed.get("reasoning", "") or ""
            else:
                logger.warning(f"[{node_name}] Unexpected parsed type: {type(parsed)}")
        except (TypeError, AttributeError) as parse_err:
            logger.error(f"[{node_name}] Parse error: {parse_err}")
            selected_concepts = []
    
    # Ensure selected_concepts is always a list
    if not isinstance(selected_concepts, list):
        selected_concepts = [selected_concepts] if selected_concepts else []
    
    if selected_concepts:
        # Filter fields
        # Loose matching: if category contains the selected concept key word
        full_field_list = state.fields
        
        # Log match attempts for debugging
        logger.info(f"[{node_name}] Available Categories: {list(categories.keys())}")
        logger.info(f"[{node_name}] LLM Selected: {selected_concepts}")
        
        # Exact or partial match strategy
        for f in full_field_list:
            f_cat = f.get("category") or "General"
            f_id = str(f.get("id", "")).lower()
            f_name = str(f.get("name", "")).lower()
            
            # Match against category, ID, or Name
            # If any selected concept matches any part of field metadata
            for c in selected_concepts:
                c_lower = c.lower()
                # 1. Category match (substring)
                if c_lower in f_cat.lower() or f_cat.lower() in c_lower:
                    focused_fields.append(f)
                    break
                # 2. Field ID/Name match (substring)
                if c_lower in f_id or c_lower in f_name:
                    focused_fields.append(f)
                    break
                
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
# NODE: Code Generation (Strategy-Aware)
# =============================================================================

async def node_code_gen(state: MiningState, llm_service: LLMService, config: RunnableConfig = None) -> Dict:
    """
    Generate Alpha expressions using LLM with strategy context.
    
    Now supports:
    - Strategy-driven temperature and exploration weight
    - Preferred/avoided fields from evolution strategy
    - Focus hypotheses and avoid patterns from feedback
    
    Input State:
        - dataset_id, fields, operators, patterns, pitfalls
        
    Config:
        - strategy: Evolution strategy dict with exploration parameters
    
    Output Updates:
        - pending_alphas
        - trace_steps
    """
    from backend.agents.prompts import PromptContext, build_alpha_generation_prompt
    
    start_time = time.time()
    node_name = "CODE_GEN"
    
    # Extract services from config
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    strategy_dict = config.get("configurable", {}).get("strategy", {}) if config else {}
    
    # Extract strategy parameters with defaults
    temperature = strategy_dict.get("temperature", 0.7)
    exploration_weight = strategy_dict.get("exploration_weight", 0.5)
    preferred_fields = strategy_dict.get("preferred_fields", [])
    avoid_fields = strategy_dict.get("avoid_fields", [])
    focus_hypotheses = strategy_dict.get("focus_hypotheses", [])
    avoid_patterns = strategy_dict.get("avoid_patterns", [])
    
    logger.info(
        f"[{node_name}] Starting | task={state.task_id} "
        f"temp={temperature:.2f} explore={exploration_weight:.2f}"
    )
    
    # Build structured prompt context
    prompt_context = PromptContext(
        dataset_id=state.dataset_id,
        dataset_description=state.dataset_description or "",
        dataset_category=state.dataset_category or "",
        region=state.region,
        universe=state.universe,
        fields=state.focused_fields if state.focused_fields else state.fields[:30],
        operators=state.operators[:50],
        success_patterns=state.patterns[:5],
        failure_pitfalls=state.pitfalls[:5],
        preferred_fields=preferred_fields,
        avoid_fields=avoid_fields,
        focus_hypotheses=focus_hypotheses + [
            h.get("idea", str(h)) if isinstance(h, dict) else str(h)
            for h in state.hypotheses[:3]
        ],
        avoid_patterns=avoid_patterns,
        num_alphas=state.num_alphas_target,
        exploration_weight=exploration_weight,
    )
    
    # Build prompt using new system
    prompt = build_alpha_generation_prompt(prompt_context)
    
    # Defensive: wrap LLM call in try-except
    try:
        response = await llm_service.call(
            system_prompt=ALPHA_GENERATION_SYSTEM,
            user_prompt=prompt,
            temperature=temperature,  # Use strategy-driven temperature
            json_mode=True
        )
    except Exception as llm_err:
        logger.error(f"[{node_name}] LLM call exception: {llm_err}")
        response = type('obj', (object,), {'success': False, 'parsed': None, 'error': str(llm_err)})()
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Parse alphas into candidates
    pending_alphas = []
    if response.success and response.parsed and isinstance(response.parsed, dict):
        raw_alphas = response.parsed.get("alphas", []) or []
        for alpha_data in raw_alphas:
            # Extract all available metadata
            hypothesis_text = alpha_data.get("hypothesis", "")
            explanation = alpha_data.get("explanation", "")
            key_fields = alpha_data.get("key_fields", [])
            complexity = alpha_data.get("complexity", "medium")
            
            candidate = AlphaCandidate(
                expression=alpha_data.get("expression", ""),
                hypothesis=hypothesis_text,
                explanation=explanation,
                expected_sharpe=alpha_data.get("expected_sharpe")
            )
            
            # Only add if expression is valid
            if candidate.expression and candidate.expression.strip():
                pending_alphas.append(candidate)
    # #region agent log
    _debug_log("A", "nodes.py:code_gen:result", "Alpha code generation complete", {"alphas_generated": len(pending_alphas), "target": state.num_alphas_target, "duration_ms": duration_ms, "llm_success": response.success, "temperature": temperature})
    # #endregion
    
    logger.info(f"[{node_name}] Complete | alphas={len(pending_alphas)}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {
            "num_alphas_target": state.num_alphas_target,
            "strategy": {
                "temperature": temperature,
                "exploration_weight": exploration_weight,
                "preferred_fields_count": len(preferred_fields),
                "avoid_fields_count": len(avoid_fields),
            }
        },
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
# NODE: Validate (P0-1: Enhanced with semantic type validation)
# =============================================================================

from validator import ExpressionValidator
from backend.alpha_semantic_validator import (
    AlphaSemanticValidator, 
    ExpressionDeduplicator,
    validate_alpha_semantically,
    compute_expression_hash
)

# Initialize Validators (Singleton-ish)
_VALIDATOR = ExpressionValidator()
_SEMANTIC_VALIDATOR = None  # Lazy init with fields
_DEDUPLICATOR = ExpressionDeduplicator(similarity_threshold=0.90)

async def node_validate(state: MiningState, config: RunnableConfig = None) -> Dict:
    """
    Batch validate ALL pending alpha expressions.
    
    Enhanced with P0 improvements:
    - P0-1: Semantic type validation (MATRIX/VECTOR constraints)
    - P0-2: Deduplication gate (skip already-seen expressions)
    
    Input State:
        - pending_alphas
        - fields (with type info for semantic validation)
    
    Output Updates:
        - pending_alphas (with validation result)
        - trace_steps
    """
    start_time = time.time()
    node_name = "VALIDATE"
    
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    # Reset deduplicator for this batch (cross-batch dedup handled at DB level)
    batch_dedup = ExpressionDeduplicator(similarity_threshold=0.90)
    
    updated_alphas = []
    valid_count = 0
    syntax_errors = []
    semantic_errors = []
    duplicate_count = 0
    type_warnings = []
    
    logger.info(f"[{node_name}] 开始批量校验 | count={len(state.pending_alphas)}")
    
    # Build field list for validators
    allowed_fields = []
    for f in state.fields:
        if isinstance(f, dict):
            allowed_fields.append(f.get("id", f.get("name")))
        else:
            allowed_fields.append(str(f))
    # #region agent log
    _debug_log("D", "nodes.py:validate:fields", "Allowed fields for validation", {"allowed_fields": allowed_fields, "fields_count": len(allowed_fields), "expressions": [a.expression[:100] for a in state.pending_alphas]})
    # #endregion
    
    # Initialize semantic validator with field type info
    semantic_validator = AlphaSemanticValidator(
        fields=state.fields,
        operators=None,  # Use default operator set
        strict_field_check=False,  # Warnings for unknown fields
        strict_type_check=True     # Block type mismatches (VECTOR fields without vec_* operators)
    )
    
    for alpha in state.pending_alphas:
        expression = alpha.expression
        is_valid = True
        error = None
        warnings = []
        
        if not expression or not expression.strip():
            is_valid = False
            error = "Empty expression"
        else:
            try:
                # Step 1: Deduplication check (P0-2)
                is_dup, dup_reason = batch_dedup.is_duplicate(expression)
                if is_dup:
                    is_valid = False
                    error = f"Duplicate: {dup_reason}"
                    duplicate_count += 1
                else:
                    # Add to batch dedup tracker
                    batch_dedup.add(expression)
                    
                    # Step 2: Syntax validation (existing)
                    syntax_result = _VALIDATOR.check_expression(expression, allowed_fields=allowed_fields)
                    if not syntax_result.get("valid", False):
                        is_valid = False
                        err_list = syntax_result.get("errors", [])
                        error = "; ".join(err_list) if err_list else "Syntax error"
                        syntax_errors.append(error)
                    else:
                        # Step 3: Semantic validation (P0-1: type constraints)
                        sem_result = semantic_validator.validate(expression)
                        
                        # Collect warnings (don't block, but record)
                        if sem_result.warnings:
                            warnings.extend(sem_result.warnings)
                            type_warnings.extend(sem_result.warnings[:2])
                            
                        # Semantic errors are blocking if strict
                        if sem_result.errors:
                            # For now, treat semantic errors as warnings (less strict)
                            # Can toggle to strict mode if needed
                            warnings.extend(sem_result.errors)
                            semantic_errors.extend(sem_result.errors[:2])
                            
            except Exception as e:
                is_valid = False
                error = f"Validation Exception: {str(e)}"
        
        updated_alpha = alpha.model_copy()
        updated_alpha.is_valid = is_valid
        updated_alpha.validation_error = error
        
        # Store warnings in a custom field if available, or append to error
        if warnings and not error:
            # Alpha passed but has warnings - store for analysis
            updated_alpha.validation_error = f"[WARNINGS] {'; '.join(warnings[:3])}"
        
        if is_valid:
            valid_count += 1
        else:
            if error and "Duplicate" not in error:
                syntax_errors.append(f"{expression[:50]}... -> {error}")
            
        updated_alphas.append(updated_alpha)
    
    duration_ms = int((time.time() - start_time) * 1000)
    # #region agent log
    _debug_log("D", "nodes.py:validate:result", "Validation complete", {"total": len(updated_alphas), "valid": valid_count, "invalid": len(updated_alphas) - valid_count, "duplicates": duplicate_count, "syntax_error_count": len(syntax_errors), "duration_ms": duration_ms, "pass_rate": round(valid_count / max(1, len(updated_alphas)) * 100, 1)})
    # #endregion
    
    logger.info(
        f"[{node_name}] 完成 | valid={valid_count}/{len(updated_alphas)} "
        f"duplicates={duplicate_count} type_warnings={len(type_warnings)}"
    )
    if syntax_errors:
        logger.warning(f"[{node_name}] Syntax Errors: {syntax_errors[:3]}")
    if semantic_errors:
        logger.warning(f"[{node_name}] Semantic Warnings: {semantic_errors[:3]}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {"count": len(updated_alphas)},
        {
            "valid_count": valid_count, 
            "invalid_count": len(updated_alphas) - valid_count,
            "duplicate_count": duplicate_count,
            "type_warnings": type_warnings[:5],
            "failures": [
                {"expression": a.expression[:100], "error": a.validation_error}
                for a in updated_alphas if not a.is_valid
            ][:10]  # Limit failure list
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

    # Build fields string with type info for self-correction
    matrix_fields = []
    vector_fields = []
    for f in state.fields[:50]:
        fid = f.get('id', f.get('name', ''))
        ftype = f.get('type', 'MATRIX').upper()
        if ftype == 'VECTOR':
            vector_fields.append(fid)
        else:
            matrix_fields.append(fid)
    
    fields_str = f"MATRIX fields (use ts_* directly): {', '.join(matrix_fields[:30])}"
    if vector_fields:
        fields_str += f"\nVECTOR fields (MUST use vec_* first, e.g., vec_sum, vec_avg): {', '.join(vector_fields)}"
    
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
# NODE: Simulate (P0-2: Enhanced with DB-level deduplication)
# =============================================================================

async def node_simulate(state: MiningState, brain: BrainAdapter, config: RunnableConfig = None) -> Dict:
    """
    Batch simulate ALL valid alphas on BRAIN platform.
    
    Enhanced with P0-2: DB-level deduplication
    - Check expression hash against existing alphas before simulation
    - Skip already-simulated expressions to save API calls
    
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
    
    # P0-2: DB-level deduplication check
    db_duplicates = 0
    indices_to_simulate = []
    
    try:
        from backend.database import AsyncSessionLocal
        from backend.selection_strategy import filter_unsimulated_expressions
        
        expressions_to_check = [state.pending_alphas[i].expression for i in valid_indices]
        
        async with AsyncSessionLocal() as db:
            new_exprs, dup_exprs = await filter_unsimulated_expressions(
                db, expressions_to_check, state.region, state.universe
            )
            
        # Map back to indices
        new_expr_set = set(new_exprs)
        for idx in valid_indices:
            expr = state.pending_alphas[idx].expression
            if expr in new_expr_set:
                indices_to_simulate.append(idx)
            else:
                db_duplicates += 1
                # Mark as duplicate (skip simulation)
                state.pending_alphas[idx].simulation_error = "DB duplicate: already simulated"
                state.pending_alphas[idx].is_simulated = True
                state.pending_alphas[idx].simulation_success = False
                
        logger.info(f"[{node_name}] DB dedup: {db_duplicates} duplicates skipped, "
                   f"{len(indices_to_simulate)} to simulate")
                   
    except Exception as e:
        logger.warning(f"[{node_name}] DB dedup check failed, proceeding with all: {e}")
        indices_to_simulate = valid_indices
        
    if not indices_to_simulate:
        logger.warning(f"[{node_name}] All expressions already in DB")
        return {"pending_alphas": state.pending_alphas}
        
    logger.info(f"[{node_name}] 开始批量模拟 | count={len(indices_to_simulate)} region={state.region}")
    
    expressions = [state.pending_alphas[i].expression for i in indices_to_simulate]
    # #region agent log
    _debug_log("E", "nodes.py:simulate:expressions", "Expressions to simulate", {"count": len(expressions), "expressions": [e[:150] for e in expressions], "region": state.region, "universe": state.universe})
    # #endregion
    
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
    
    # Update alphas - use indices_to_simulate (not valid_indices which includes DB dups)
    updated_alphas = state.pending_alphas.copy()
    success_count = 0
    
    for i, idx in enumerate(indices_to_simulate):
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
        
    # #region agent log
    failed_errors = [{"expr": expressions[i][:80], "error": results[i].get("error", "unknown")[:200]} for i in range(len(results)) if not results[i].get("success")]
    _debug_log("E", "nodes.py:simulate:result", "Simulation complete", {"total_to_simulate": len(indices_to_simulate), "success": success_count, "failed": len(indices_to_simulate) - success_count, "db_duplicates_skipped": db_duplicates, "duration_ms": duration_ms, "success_rate": round(success_count / max(1, len(indices_to_simulate)) * 100, 1), "failed_errors": failed_errors[:5]})
    # #endregion
    logger.info(f"[{node_name}] 完成 | success={success_count}/{len(indices_to_simulate)} db_skipped={db_duplicates}")
    
    # Observability: Record metrics for experiment tracking
    if EXPERIMENT_TRACKING_ENABLED:
        exp = get_current_experiment()
        if exp:
            exp.metrics.increment("simulation_count", len(indices_to_simulate))
            exp.metrics.record("dedup_skip_rate", 
                (db_duplicates / (len(indices_to_simulate) + db_duplicates) * 100) 
                if (len(indices_to_simulate) + db_duplicates) > 0 else 0,
                tags={"node": node_name, "region": state.region}
            )
            exp.metrics.record("simulation_success_rate",
                (success_count / len(indices_to_simulate) * 100) if len(indices_to_simulate) > 0 else 0,
                tags={"node": node_name}
            )
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {
            "batch_size": len(indices_to_simulate), 
            "db_duplicates_skipped": db_duplicates,
            "expressions": [e[:50] for e in expressions[:10]]  # Limit logged expressions
        },
        {
            "success_count": success_count,
            "simulated_count": len(indices_to_simulate),
            "db_duplicates": db_duplicates,
            "results": [{"id": r.get("alpha_id"), "err": r.get("error")} for r in results[:20]]
        },
        duration_ms,
        "SUCCESS" if success_count > 0 else "PARTIAL_FAILURE"
    )
    
    return {
        "pending_alphas": updated_alphas,
        **trace_update
    }


# =============================================================================
# NODE: Evaluate Quality (Multi-Objective Scoring)
# =============================================================================

async def node_evaluate(state: MiningState, brain: BrainAdapter = None, config: RunnableConfig = None) -> Dict:
    """
    Evaluate alpha quality using multi-objective scoring.
    
    Enhanced with P0-3: Two-stage correlation checking
    - Stage 1: Quick score based on metrics only (all alphas)
    - Stage 2: Correlation check only for near-PASS candidates (expensive API calls)
    
    This significantly reduces API calls while maintaining quality.
    
    Input State:
        - pending_alphas (with simulation results)
    
    Output Updates:
        - pending_alphas (with quality_status and score)
        - trace_steps
    """
    from backend.alpha_scoring import calculate_alpha_score, should_optimize, get_failed_tests
    
    start_time = time.time()
    node_name = "EVALUATE"
    
    trace_service = config.get("configurable", {}).get("trace_service") if config else None
    
    updated_alphas = state.pending_alphas.copy()
    pass_count = 0
    fail_count = 0
    optimize_count = 0
    corr_checks_performed = 0
    corr_checks_skipped = 0
    
    logger.info(f"[{node_name}] Starting two-stage evaluation | count={len(state.pending_alphas)}")
    
    # Configurable thresholds
    sharpe_min = getattr(settings, 'SHARPE_MIN', 1.5)
    turnover_max = getattr(settings, 'TURNOVER_MAX', 0.7)
    fitness_min = getattr(settings, 'FITNESS_MIN', 0.6)
    score_pass_threshold = getattr(settings, 'SCORE_PASS_THRESHOLD', 0.8)
    score_optimize_threshold = getattr(settings, 'SCORE_OPTIMIZE_THRESHOLD', 0.3)
    
    # P0-3: Threshold for triggering correlation check (only near-PASS candidates)
    # If preliminary score < this, skip correlation check entirely
    corr_check_threshold = getattr(settings, 'CORR_CHECK_THRESHOLD', 0.5)
    
    eval_details = []
    
    # P0-fix-1: Queue for knowledge feedback (failures to record)
    failure_feedback_queue = []
    
    for i, alpha in enumerate(updated_alphas):
        # Skip if not simulated successfully
        if not alpha.is_simulated or not alpha.simulation_success:
            if alpha.quality_status == "PENDING":
                alpha.quality_status = "FAIL"
            continue
        
        metrics = alpha.metrics or {}

        train_sharpe_val = metrics.get("train_sharpe")
        train_fitness_val = metrics.get("train_fitness")
        test_sharpe_val = metrics.get("test_sharpe")
        test_fitness_val = metrics.get("test_fitness")
        
        # Build simulation result dict for scoring
        sim_result = {
            "train": {
                "sharpe": train_sharpe_val if train_sharpe_val is not None else metrics.get("sharpe", 0),
                "fitness": train_fitness_val if train_fitness_val is not None else metrics.get("fitness", 0),
                "turnover": metrics.get("turnover", 0),
                "returns": metrics.get("returns", 0),
            },
            "test": {
                "sharpe": test_sharpe_val if test_sharpe_val is not None else metrics.get("sharpe", 0) * 0.8,
                "fitness": test_fitness_val if test_fitness_val is not None else metrics.get("fitness", 0),
            },
            "riskNeutralized": metrics.get("riskNeutralized", {}),
            "investabilityConstrained": metrics.get("investabilityConstrained", {}),
        }
        
        # =====================================================================
        # STAGE 1: Preliminary score WITHOUT correlation (cheap)
        # =====================================================================
        preliminary_score = calculate_alpha_score(
            sim_result=sim_result,
            prod_corr=0.0,  # Assume no correlation for preliminary
            self_corr=0.0
        )
        
        # Extract key metrics for quick threshold check
        sharpe = metrics.get("sharpe", 0) or 0
        turnover = metrics.get("turnover", 0) or 0
        fitness = metrics.get("fitness", 0) or 0
        
        # Quick fail check - if clearly below thresholds, skip correlation
        meets_thresholds = (
            sharpe >= sharpe_min and
            turnover <= turnover_max and
            fitness >= fitness_min
        )
        
        # =====================================================================
        # STAGE 2: Correlation check ONLY for promising candidates (expensive)
        # =====================================================================
        prod_corr = 0.0
        self_corr = 0.0
        needs_corr_check = (
            preliminary_score >= corr_check_threshold or 
            meets_thresholds
        )
        
        if needs_corr_check and brain and alpha.alpha_id:
            corr_checks_performed += 1
            try:
                prod_corr_result = await brain.check_correlation(alpha.alpha_id, check_type="PROD")
                if isinstance(prod_corr_result, dict):
                    prod_corr = float(prod_corr_result.get("max", 0.0) or 0.0)
            except Exception as e:
                logger.warning(f"[{node_name}] PROD correlation check failed for {alpha.alpha_id}: {e}")

            try:
                self_corr_result = await brain.check_correlation(alpha.alpha_id, check_type="SELF")
                if isinstance(self_corr_result, dict):
                    self_corr = float(self_corr_result.get("max", 0.0) or 0.0)
            except Exception as e:
                logger.warning(f"[{node_name}] SELF correlation check failed for {alpha.alpha_id}: {e}")
        else:
            corr_checks_skipped += 1

        # Final score with correlation penalty (if checked)
        score = calculate_alpha_score(
            sim_result=sim_result,
            prod_corr=prod_corr,
            self_corr=self_corr
        )
        
        # Get optimization recommendation
        should_opt, opt_reason = should_optimize(sim_result)
        failed_tests = get_failed_tests(sim_result)
        
        # Determine quality status using hybrid approach:
        # 1. If meets all thresholds OR score > pass_threshold -> PASS
        # 2. If should optimize and score > optimize_threshold -> OPTIMIZE
        # 3. Otherwise -> FAIL
        
        if meets_thresholds or score >= score_pass_threshold:
            alpha.quality_status = "PASS"
            pass_count += 1
        elif should_opt and score >= score_optimize_threshold:
            alpha.quality_status = "OPTIMIZE"
            optimize_count += 1
        else:
            alpha.quality_status = "FAIL"
            fail_count += 1
            
            # P0-fix-1: Record failure pattern to knowledge base for learning
            # Determine error type based on which threshold was missed
            error_type = "QUALITY_FAIL"
            if sharpe < sharpe_min:
                error_type = "LOW_SHARPE"
            elif fitness < fitness_min:
                error_type = "LOW_FITNESS"
            elif turnover > turnover_max:
                error_type = "HIGH_TURNOVER"
            elif sharpe < 0:
                error_type = "NEGATIVE_SIGNAL"
            
            # Queue for async feedback (will be processed at end of evaluation)
            if alpha.expression:
                failure_feedback_queue.append({
                    "expression": alpha.expression,
                    "error_type": error_type,
                    "metrics": metrics,
                    "region": state.region,
                    "dataset_id": state.dataset_id
                })
        
        # Store score and optimization info in metrics for later use
        alpha.metrics = {
            **metrics,
            "_score": round(score, 4),
            "_preliminary_score": round(preliminary_score, 4),
            "_prod_corr": round(prod_corr, 4) if prod_corr else None,
            "_self_corr": round(self_corr, 4) if self_corr else None,
            "_corr_checked": needs_corr_check,
            "_should_optimize": should_opt,
            "_optimize_reason": opt_reason,
            "_failed_tests": failed_tests,
        }
        
        # #region agent log
        _debug_log("F", "nodes.py:evaluate:alpha_detail", f"Alpha evaluated: {alpha.quality_status}", {
            "alpha_id": alpha.alpha_id,
            "expression": alpha.expression[:80] if alpha.expression else None,
            "sharpe": round(sharpe, 3),
            "fitness": round(fitness, 3),
            "turnover": round(turnover, 3),
            "score": round(score, 3),
            "preliminary_score": round(preliminary_score, 3),
            "meets_thresholds": meets_thresholds,
            "thresholds": {"sharpe_min": sharpe_min, "fitness_min": fitness_min, "turnover_max": turnover_max},
            "failed_tests": failed_tests,
            "status": alpha.quality_status
        })
        # #endregion
        
        eval_details.append({
            "id": alpha.alpha_id,
            "status": alpha.quality_status,
            "score": round(score, 4),
            "sharpe": sharpe,
            "fitness": fitness,
            "turnover": turnover,
            "corr_checked": needs_corr_check,
            "optimize_reason": opt_reason if should_opt else None,
        })
        
        updated_alphas[i] = alpha
    
    duration_ms = int((time.time() - start_time) * 1000)
    # #region agent log
    _debug_log("E", "nodes.py:evaluate:result", "Evaluation complete", {"pass": pass_count, "optimize": optimize_count, "fail": fail_count, "corr_checked": corr_checks_performed, "corr_skipped": corr_checks_skipped, "duration_ms": duration_ms, "pass_rate": round(pass_count / max(1, pass_count + optimize_count + fail_count) * 100, 1)})
    # #endregion
    
    logger.info(
        f"[{node_name}] Complete | pass={pass_count} optimize={optimize_count} fail={fail_count} "
        f"corr_checked={corr_checks_performed} corr_skipped={corr_checks_skipped}"
    )
    
    # Observability: Record evaluation metrics
    if EXPERIMENT_TRACKING_ENABLED:
        exp = get_current_experiment()
        if exp:
            exp.metrics.increment("pass_count", pass_count)
            exp.metrics.record("iteration_duration_ms", duration_ms, tags={"node": node_name})
            
            total_evaluated = pass_count + optimize_count + fail_count
            if total_evaluated > 0:
                exp.metrics.record("pass_rate", pass_count / total_evaluated * 100, tags={"region": state.region})
                
            # P0-3: Two-stage correlation savings
            total_corr = corr_checks_performed + corr_checks_skipped
            if total_corr > 0:
                exp.metrics.record("corr_check_skip_rate", 
                    corr_checks_skipped / total_corr * 100,
                    tags={"node": node_name}
                )
    
    # P0-fix-1: Process failure feedback queue - write to knowledge base
    # This enables the system to LEARN from failures
    if failure_feedback_queue:
        rag_service = config.get("configurable", {}).get("rag_service") if config else None
        if rag_service:
            feedback_recorded = 0
            # Sample failures to avoid overwhelming the KB (max 3 per iteration)
            sample_size = min(3, len(failure_feedback_queue))
            import random
            sampled_failures = random.sample(failure_feedback_queue, sample_size)
            
            for feedback in sampled_failures:
                try:
                    await rag_service.record_failure_pattern(
                        expression=feedback["expression"],
                        error_type=feedback["error_type"],
                        metrics=feedback["metrics"],
                        region=feedback["region"],
                        dataset_id=feedback["dataset_id"]
                    )
                    feedback_recorded += 1
                except Exception as e:
                    logger.warning(f"[{node_name}] Failed to record feedback: {e}")
            
            logger.info(f"[{node_name}] Knowledge feedback | recorded={feedback_recorded}/{len(failure_feedback_queue)}")
    
    trace_update = await record_trace(
        state, trace_service, node_name,
        {
            "evaluation_mode": "two_stage_correlation",
            "thresholds": {
                "sharpe_min": sharpe_min,
                "turnover_max": turnover_max,
                "fitness_min": fitness_min,
                "score_pass": score_pass_threshold,
                "corr_check_threshold": corr_check_threshold,
            }
        },
        {
            "pass_count": pass_count,
            "optimize_count": optimize_count,
            "fail_count": fail_count,
            "corr_checks_performed": corr_checks_performed,
            "corr_checks_skipped": corr_checks_skipped,
            "details": eval_details[:20]  # Limit to avoid huge trace
        },
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
