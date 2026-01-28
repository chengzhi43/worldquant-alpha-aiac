"""
Prompt Templates for Alpha Mining

Design Principles:
1. Avoid Bias: Don't suggest certain approaches are inherently better
2. Structured Output: Clear JSON schemas for reliable parsing
3. Separation of Concerns: Hypothesis generation vs Expression construction
4. Configurable: Strategy parameters injected at runtime
5. Factual Context: Provide data, not opinions

Reference: Alpha-GPT, RD-Agent CoSTEER, Chain-of-Alpha
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


# =============================================================================
# DATA CLASSES FOR TYPE SAFETY
# =============================================================================

@dataclass
class PromptContext:
    """Structured context for prompt rendering."""
    dataset_id: str = ""
    dataset_description: str = ""
    dataset_category: str = ""
    region: str = "USA"
    universe: str = "TOP3000"
    
    # Available data (will be JSON serialized)
    fields: List[Dict] = field(default_factory=list)
    operators: List[Dict] = field(default_factory=list)
    
    # Knowledge base context
    success_patterns: List[Dict] = field(default_factory=list)
    failure_pitfalls: List[Dict] = field(default_factory=list)
    
    # Strategy guidance (from StrategyAgent)
    preferred_fields: List[str] = field(default_factory=list)
    avoid_fields: List[str] = field(default_factory=list)
    focus_hypotheses: List[str] = field(default_factory=list)
    avoid_patterns: List[str] = field(default_factory=list)
    
    # Generation parameters
    num_alphas: int = 5
    exploration_weight: float = 0.5  # 0=pure exploitation, 1=pure exploration


# =============================================================================
# PROMPT BUILDERS (Functional Style for Testability)
# =============================================================================

def build_fields_context(fields: List[Dict], max_fields: int = 30) -> str:
    """Build concise field reference with type info, avoiding overwhelming the model."""
    if not fields:
        return "No fields available."
    
    # Separate MATRIX and VECTOR fields
    matrix_fields = []
    vector_fields = []
    other_fields = []
    
    for f in fields[:max_fields]:
        field_id = f.get("id", f.get("name", "unknown"))
        field_type = f.get("type", "MATRIX").upper()
        
        if field_type == "VECTOR":
            vector_fields.append(field_id)
        elif field_type == "MATRIX":
            matrix_fields.append(field_id)
        else:
            other_fields.append(field_id)
    
    lines = []
    
    if matrix_fields:
        sample = ", ".join(matrix_fields[:10])
        if len(matrix_fields) > 10:
            sample += f" ... (+{len(matrix_fields) - 10} more)"
        lines.append(f"- **MATRIX fields** (time-series, use ts_* operators directly): {sample}")
    
    if vector_fields:
        sample = ", ".join(vector_fields[:10])
        if len(vector_fields) > 10:
            sample += f" ... (+{len(vector_fields) - 10} more)"
        lines.append(f"- **VECTOR fields** (MUST use vec_* operators first!): {sample}")
    
    if other_fields:
        sample = ", ".join(other_fields[:5])
        lines.append(f"- Other: {sample}")
    
    return "\n".join(lines)


def build_operators_context(operators: List[Dict], max_ops: int = 40) -> str:
    """Build operator reference grouped by category."""
    if not operators:
        return "Use standard operators."
    
    by_category: Dict[str, List[str]] = {}
    for op in operators[:max_ops]:
        cat = op.get("category", "Other")
        if cat not in by_category:
            by_category[cat] = []
        op_name = op.get("name", op.get("id", "unknown"))
        by_category[cat].append(op_name)
    
    lines = []
    for cat, op_names in sorted(by_category.items()):
        lines.append(f"- {cat}: {', '.join(op_names[:10])}")
    
    return "\n".join(lines)


def build_patterns_context(patterns: List[Dict], label: str, max_items: int = 5) -> str:
    """Build pattern reference without implying they must be followed."""
    if not patterns:
        return f"No {label} recorded yet."
    
    lines = []
    for p in patterns[:max_items]:
        pattern = p.get("pattern", p.get("template", ""))
        desc = p.get("description", "")
        if pattern:
            lines.append(f"- `{pattern}`: {desc[:80]}")
    
    return "\n".join(lines) if lines else f"No {label} recorded yet."


def build_strategy_constraints(ctx: PromptContext) -> str:
    """Build strategy-driven constraints without being prescriptive."""
    constraints = []
    
    if ctx.avoid_fields:
        constraints.append(
            f"Fields with recent issues (consider alternatives): {', '.join(ctx.avoid_fields[:5])}"
        )
    
    if ctx.avoid_patterns:
        constraints.append(
            f"Patterns that underperformed recently: {'; '.join(ctx.avoid_patterns[:3])}"
        )
    
    # CRITICAL TYPE CONSTRAINTS
    constraints.append(
        "**VECTOR FIELD RULE**: VECTOR-type fields MUST be processed with vec_* operators (vec_sum, vec_avg, vec_max, vec_min,vec_count,vec_range,vec_stddev, etc.) BEFORE using ts_* operators. Example: ts_rank(vec_sum(vector_field), 20) - NOT ts_rank(vector_field, 20)"
    )
    constraints.append(
        "**MATRIX FIELD RULE**: MATRIX-type fields can use ts_* operators directly. Example: ts_rank(matrix_field, 20)"
    )
    
    # Syntax constraints (always apply)
    constraints.extend([
        "Lookback windows must be positive integers",
        "Maximum 3 distinct fields per expression",
        "Maximum 8 operators per expression",
        "Ensure no look-ahead bias (no future data access)"
    ])
    
    return "\n".join(f"- {c}" for c in constraints)


# =============================================================================
# ALPHA GENERATION PROMPTS (Refactored)
# =============================================================================

ALPHA_GENERATION_SYSTEM = """You are a quantitative research assistant that generates alpha expressions.

Your role is to:
1. Translate investment hypotheses into mathematical expressions
2. Use only the provided fields and operators
3. Ensure syntactic correctness and logical coherence

Guidelines:
- Focus on clarity and simplicity over complexity
- Each expression should represent a testable hypothesis
- Provide clear reasoning for your choices

Output must be valid JSON matching the specified schema."""


def build_alpha_generation_prompt(ctx: PromptContext) -> str:
    """Build user prompt for alpha generation with full context."""
    
    # Build strategy section based on exploration weight
    strategy_section = ""
    if ctx.exploration_weight > 0.7:
        strategy_section = """
**Exploration Mode**: Prioritize novel combinations and underexplored fields.
Consider unconventional approaches that differ from known patterns."""
    elif ctx.exploration_weight < 0.3:
        strategy_section = """
**Exploitation Mode**: Build upon patterns that have shown promise.
Focus on variations and refinements of successful approaches."""
    else:
        strategy_section = """
**Balanced Mode**: Mix novel explorations with refinements of known approaches."""
    
    # Build hypothesis guidance if available
    hypothesis_guidance = ""
    if ctx.focus_hypotheses:
        hypothesis_guidance = f"""
**Suggested Research Directions** (for reference, not requirements):
{chr(10).join(f'- {h}' for h in ctx.focus_hypotheses[:5])}"""
    
    # Build preferred fields section if available
    preferred_section = ""
    if ctx.preferred_fields:
        preferred_section = f"""
**Fields with Recent Success** (consider using):
{', '.join(ctx.preferred_fields[:10])}"""
    
    return f"""## Dataset Context

**Dataset**: {ctx.dataset_id}
**Description**: {ctx.dataset_description or 'Not provided'}
**Category**: {ctx.dataset_category or 'General'}
**Region**: {ctx.region} | **Universe**: {ctx.universe}

## Available Data

**Fields** (grouped by category):
{build_fields_context(ctx.fields)}
{preferred_section}

**Operators** (grouped by category):
{build_operators_context(ctx.operators)}

## Historical Context

**Patterns that have worked**:
{build_patterns_context(ctx.success_patterns, "success patterns")}

**Known pitfalls to be aware of**:
{build_patterns_context(ctx.failure_pitfalls, "pitfalls")}

## Constraints

{build_strategy_constraints(ctx)}

**CRITICAL CONSTRAINT**:
You MUST Use ONLY the provided fields. Do NOT assume the existence of 'close', 'open', 'volume', 'returns', or 'cap' unless explicitly listed in the available fields section above. Hallucinating fields will cause immediate failure.

## Strategy
{strategy_section}
{hypothesis_guidance}

## Task

Generate {ctx.num_alphas} distinct alpha expressions. For each:
1. State a clear investment hypothesis
2. Construct an expression that tests this hypothesis
3. Explain the economic logic

**Output Schema** (JSON):
```json
{{
  "alphas": [
    {{
      "hypothesis": "Clear statement of the investment thesis being tested",
      "expression": "Valid expression using provided fields and operators",
      "explanation": "Why this logic might capture market inefficiency",
      "key_fields": ["field1", "field2"],
      "complexity": "low|medium|high"
    }}
  ]
}}
```"""


# =============================================================================
# HYPOTHESIS GENERATION PROMPTS
# =============================================================================

HYPOTHESIS_SYSTEM = """You are a quantitative research strategist.

Your role is to generate testable investment hypotheses based on:
1. The characteristics of the available data
2. General financial theory and market microstructure
3. Historical patterns that have shown promise

Guidelines:
- Each hypothesis should be specific and testable
- Avoid vague statements; be precise about the expected relationship
- Consider both momentum and mean-reversion effects
- Think about what market behavior the data might capture

Output must be valid JSON."""


def build_hypothesis_prompt(ctx: PromptContext) -> str:
    """Build prompt for hypothesis generation."""
    
    exploration_guidance = ""
    if ctx.exploration_weight > 0.6:
        exploration_guidance = """
**Focus**: Generate diverse hypotheses exploring different aspects of the data.
Consider unconventional relationships and cross-field interactions."""
    else:
        exploration_guidance = """
**Focus**: Generate hypotheses that build upon successful patterns.
Refine and extend approaches that have shown promise."""
    
    return f"""## Dataset Analysis

**Dataset**: {ctx.dataset_id}
**Category**: {ctx.dataset_category}
**Description**: {ctx.dataset_description}

**Core Fields** (sample):
{build_fields_context(ctx.fields, max_fields=20)}

## Historical Context

**Successful approaches**:
{build_patterns_context(ctx.success_patterns, "patterns")}

**Approaches that failed**:
{build_patterns_context(ctx.failure_pitfalls, "pitfalls")}

## Strategy
{exploration_guidance}

## Task

Generate 3-5 investment hypotheses suitable for this dataset.

**Output Schema** (JSON):
```json
{{
  "hypotheses": [
    {{
      "idea": "Clear statement of the hypothesis",
      "rationale": "Economic or behavioral reasoning",
      "key_fields": ["relevant", "fields"],
      "suggested_operators": ["ts_rank", "ts_delta"],
      "expected_behavior": "momentum|mean_reversion|other",
      "confidence": "high|medium|low"
    }}
  ]
}}
```"""


# =============================================================================
# CONCEPT DISTILLATION PROMPTS
# =============================================================================

DISTILL_SYSTEM = """You are a data categorization specialist.

Your role is to identify the most relevant field categories for alpha research
based on the dataset description and successful historical patterns.

Be objective in your selection - choose categories that contain
the most informative signals, not those that sound appealing."""


def build_distill_prompt(ctx: PromptContext, field_categories: Dict[str, List[str]]) -> str:
    """Build prompt for concept distillation."""
    
    categories_text = []
    for cat, fields in sorted(field_categories.items()):
        sample = ", ".join(fields[:5])
        if len(fields) > 5:
            sample += f" ... (+{len(fields) - 5} more)"
        categories_text.append(f"- **{cat}** ({len(fields)} fields): {sample}")
    
    return f"""## Dataset Context

**Dataset**: {ctx.dataset_id}
**Description**: {ctx.dataset_description}
**Category**: {ctx.dataset_category}

## Successful Patterns Reference
{build_patterns_context(ctx.success_patterns, "patterns")}

## Available Field Categories

{chr(10).join(categories_text)}

## Task

Select 3-5 field categories most likely to contain useful signals.

**Selection Criteria**:
1. Relevance to dataset description
2. Alignment with successful patterns
3. Information density (prefer specific categories over "General")

**Output Schema** (JSON):
```json
{{
  "selected_concepts": ["Category1", "Category2", "Category3"],
  "reasoning": "Brief explanation of selection logic"
}}
```

**Important**: Use exact category names from the list above."""


# =============================================================================
# SELF-CORRECTION PROMPTS
# =============================================================================

SELF_CORRECT_SYSTEM = """You are an alpha expression debugger.

Your role is to:
1. Analyze why an expression failed
2. Identify the specific issue (syntax, field name, operator usage)
3. Propose a corrected version

Be precise in your diagnosis and fix only what is broken."""


def build_self_correct_prompt(
    expression: str,
    error_message: str,
    error_type: str,
    available_fields: List[str]
) -> str:
    """Build prompt for self-correction."""
    
    return f"""## Failed Expression

```
{expression}
```

## Error Information

**Type**: {error_type}
**Message**: {error_message}

## Available Fields (for reference)

{', '.join(available_fields[:30])}

## Task

1. Diagnose the specific cause of failure
2. Propose a minimal fix (change only what is necessary)
3. Verify the fix addresses the error

**Output Schema** (JSON):
```json
{{
  "diagnosis": "Specific cause of the error",
  "fix_type": "field_name|syntax|operator|parameter",
  "fixed_expression": "Corrected expression",
  "changes_made": "Description of what was changed"
}}
```"""


# =============================================================================
# OPTIMIZATION PROMPTS (Chain-of-Alpha Style)
# =============================================================================

OPTIMIZATION_SYSTEM = """You are an alpha optimization specialist.

Your role is to improve weak alphas based on backtest feedback.
Focus on targeted modifications rather than complete rewrites.

Optimization strategies:
1. Window adjustment: Different lookback periods may capture different signals
2. Normalization: rank(), zscore() can improve cross-sectional comparability
3. Sign flip: Some signals work in reverse
4. Decay adjustment: Smoothing can improve stability
5. Neutralization: Risk factor removal can isolate pure alpha"""


def build_optimization_prompt(
    expression: str,
    metrics: Dict,
    failed_tests: List[str],
    optimization_reason: str
) -> str:
    """Build prompt for alpha optimization."""
    
    return f"""## Alpha to Optimize

```
{expression}
```

## Backtest Results

- **Train Sharpe**: {metrics.get('train_sharpe', 'N/A')}
- **Test Sharpe**: {metrics.get('test_sharpe', 'N/A')}
- **Fitness**: {metrics.get('fitness', 'N/A')}
- **Turnover**: {metrics.get('turnover', 'N/A')}
- **Risk-Neutralized Sharpe**: {metrics.get('rn_sharpe', 'N/A')}
- **Investability-Constrained Sharpe**: {metrics.get('invest_sharpe', 'N/A')}

## Issues Identified

**Failed Tests**: {', '.join(failed_tests) if failed_tests else 'None'}
**Optimization Trigger**: {optimization_reason}

## Task

Generate 5-8 targeted modifications that might improve this alpha.
Focus on the specific issues identified.

**Output Schema** (JSON):
```json
{{
  "analysis": "Brief analysis of what might be wrong",
  "modifications": [
    {{
      "type": "window|normalization|sign|structure",
      "expression": "Modified expression",
      "rationale": "Why this modification might help",
      "targets_issue": "Which identified issue this addresses"
    }}
  ]
}}
```"""


# =============================================================================
# ROUND ANALYSIS PROMPTS (For Strategy Agent)
# =============================================================================

ROUND_ANALYSIS_SYSTEM = """You are an alpha mining strategy analyst.

Your role is to analyze mining results and recommend adjustments for the next round.
Be objective and data-driven in your analysis.

Focus on:
1. Pattern extraction from successes (what worked)
2. Root cause analysis of failures (what went wrong)
3. Actionable recommendations (specific next steps)

Avoid:
- Vague suggestions ("try different approaches")
- Unfounded optimism or pessimism
- Recommendations without supporting evidence"""


def build_round_analysis_prompt(
    iteration: int,
    max_iterations: int,
    metrics_summary: str,
    success_examples: str,
    failure_examples: str,
    dataset_id: str,
    region: str,
    cumulative_success: int,
    target_goal: int
) -> str:
    """Build prompt for round analysis and strategy generation."""
    
    progress_pct = (cumulative_success / max(target_goal, 1)) * 100
    remaining_rounds = max_iterations - iteration
    
    return f"""## Round {iteration} Analysis

### Progress
- **Cumulative Success**: {cumulative_success}/{target_goal} ({progress_pct:.0f}%)
- **Remaining Rounds**: {remaining_rounds}
- **Dataset**: {dataset_id} | **Region**: {region}

### This Round's Metrics
{metrics_summary}

### Success Examples ({len(success_examples.split(chr(10))) if success_examples else 0})
{success_examples if success_examples else "No successes this round."}

### Failure Examples
{failure_examples if failure_examples else "No failures recorded."}

## Task

Analyze results and generate strategy for Round {iteration + 1}.

**Output Schema** (JSON):
```json
{{
  "analysis": {{
    "key_findings": ["Finding 1", "Finding 2"],
    "success_patterns": ["Pattern extracted from successes"],
    "failure_patterns": ["Common failure modes"],
    "bottleneck": "Main obstacle to progress"
  }},
  "strategy": {{
    "temperature": 0.7,
    "exploration_weight": 0.5,
    "focus_hypotheses": ["Directions to explore"],
    "avoid_patterns": ["Patterns to avoid"],
    "preferred_fields": ["Fields to prioritize"],
    "avoid_fields": ["Fields with issues"],
    "action_summary": "Concise strategy description",
    "reasoning": "Logic behind recommendations"
  }},
  "optimization_targets": [
    {{
      "expression": "Alpha to optimize (if any)",
      "reason": "Why this alpha is worth optimizing"
    }}
  ]
}}
```"""


# =============================================================================
# BACKWARDS COMPATIBILITY TEMPLATES
# =============================================================================

# Legacy templates for gradual migration
# These use string formatting directly (not the builder functions)

DISTILL_USER = """## Dataset Context

**Dataset**: {dataset_id}
**Description**: {description}
**Category**: {category}

## Successful Patterns Reference
{success_patterns}

## Available Field Categories
{field_categories}

## Task

Select 3-5 field categories most likely to contain useful signals.

**Selection Criteria**:
1. Relevance to dataset description
2. Alignment with successful patterns
3. Information density (prefer specific categories over "General")

**Output Schema** (JSON):
```json
{{
  "selected_concepts": ["Category1", "Category2", "Category3"],
  "reasoning": "Brief explanation of selection logic"
}}
```

**Important**: Use exact category names from the list above."""


HYPOTHESIS_USER = """## Dataset Analysis

**Dataset**: {dataset_id}
**Category**: {category} {subcategory}
**Description**: {description}

**Core Fields** (Top 20):
{fields_summary}

## Success Patterns Reference
{success_patterns}

## Exploration Task
**Fields to explore**:
{exploration_fields}

## Task

Generate 3-5 investment hypotheses based on the above information.

**Output Schema** (JSON):
```json
{{
  "hypotheses": [
    {{
      "idea": "Clear hypothesis statement",
      "rationale": "Economic/behavioral reasoning",
      "key_fields": ["field1", "field2"],
      "suggested_operators": ["ts_rank", "ts_delta"]
    }}
  ]
}}
```"""


ALPHA_GENERATION_USER = """## Research Context

**Dataset**: {dataset_id} ({dataset_description})
**Region**: {region}
**Universe**: {universe}

## Available Data

**Fields**:
{fields_json}

**Operators**:
{operators_json}

## Constraints & Rules
{negative_constraints}

**Syntax Enforcement**:
- Lookback windows must be integers (e.g., 20, not 20.0)
- Max operators: 7
- Max fields: 3

## Knowledge Base Context

**Hypotheses**:
{hypotheses_context}

**Reference Patterns**:
{few_shot_examples}

## Task

Generate {num_alphas} distinct Alpha expressions.

**Output Schema** (JSON):
```json
{{
  "alphas": [
    {{
      "expression": "rank(ts_delta(close, 5))",
      "hypothesis": "Short-term mean reversion...",
      "explanation": "Captures price reversal..."
    }}
  ]
}}
```"""


# =============================================================================
# FAILURE ANALYSIS (Legacy)
# =============================================================================

FAILURE_ANALYSIS_SYSTEM = """You are an alpha mining process optimization expert.

Your role is to analyze failed alpha expressions and extract actionable insights
that can improve future generation attempts.

Focus on:
1. Identifying common failure patterns
2. Extracting reusable avoidance rules
3. Suggesting prompt improvements"""

FAILURE_ANALYSIS_USER = """## Today's Failures ({count} total)

### Error Distribution
{error_distribution}

### Representative Failures
{sample_failures}

## Task

1. Analyze the main failure patterns
2. Extract reusable avoidance rules
3. Suggest prompt optimization directions

**Output Schema** (JSON):
```json
{{
  "patterns": [
    {{
      "pattern": "Failure pattern description",
      "frequency": 0.3,
      "recommendation": "How to avoid this"
    }}
  ],
  "prompt_improvements": ["Improvement 1", "Improvement 2"]
}}
```"""

# =============================================================================
# ROUND ANALYSIS (Legacy)
# =============================================================================

ROUND_ANALYSIS_USER = """## Round {iteration} Analysis

### Progress
- **Cumulative Success**: {cumulative_success}/{target_goal}
- **Remaining Rounds**: {remaining_rounds}
- **Dataset**: {dataset_id} | **Region**: {region}

### This Round's Metrics
{metrics_summary}

### Success Examples ({success_count})
{success_examples}

### Failure Examples ({failure_count})
{failure_examples}

## Task

Analyze results and generate insights for the next round.

**Output Schema** (JSON):
```json
{{
  "new_patterns": [
    {{
      "pattern": "Identified successful pattern",
      "template": "Generalized template",
      "description": "Description",
      "economic_logic": "Why it works",
      "variants": ["Variant suggestions"],
      "score": 0.8
    }}
  ],
  "new_pitfalls": [
    {{
      "pattern": "Problematic pattern",
      "error_type": "Error category",
      "description": "What went wrong",
      "recommendation": "How to avoid",
      "severity": "high|medium|low"
    }}
  ],
  "field_insights": {{
    "effective_fields": ["field1", "field2"],
    "problematic_fields": ["field3"],
    "unexplored_fields": ["field4"]
  }},
  "hypothesis_evolution": {{
    "promising_directions": ["Direction 1"],
    "abandon_directions": ["Direction 2"],
    "pivot_suggestions": ["Suggestion 1"]
  }}
}}
```"""

# =============================================================================
# SELF CORRECTION (Legacy)
# =============================================================================

SELF_CORRECT_USER = """## Failed Expression

```
{expression}
```

## Error Information

**Type**: {error_type}
**Message**: {error_message}

## Available Fields (for reference)
{available_fields}

## Task

1. Diagnose the specific cause of failure
2. Propose a minimal fix
3. Verify the fix addresses the error

**Output Schema** (JSON):
```json
{{
  "analysis": "Cause of the error",
  "fixed_expression": "Corrected expression",
  "changes": "What was changed"
}}
```"""


# =============================================================================
# PROMPT TEMPLATE REGISTRY (For Dynamic Selection)
# =============================================================================

class PromptRegistry:
    """Registry for prompt templates, enabling runtime selection and customization."""
    
    _system_prompts = {
        "alpha_generation": ALPHA_GENERATION_SYSTEM,
        "hypothesis": HYPOTHESIS_SYSTEM,
        "distill": DISTILL_SYSTEM,
        "self_correct": SELF_CORRECT_SYSTEM,
        "optimization": OPTIMIZATION_SYSTEM,
        "round_analysis": ROUND_ANALYSIS_SYSTEM,
    }
    
    _user_prompt_builders = {
        "alpha_generation": build_alpha_generation_prompt,
        "hypothesis": build_hypothesis_prompt,
        "self_correct": build_self_correct_prompt,
        "optimization": build_optimization_prompt,
        "round_analysis": build_round_analysis_prompt,
    }
    
    @classmethod
    def get_system_prompt(cls, prompt_type: str) -> str:
        """Get system prompt by type."""
        return cls._system_prompts.get(prompt_type, "")
    
    @classmethod
    def get_user_prompt_builder(cls, prompt_type: str):
        """Get user prompt builder function by type."""
        return cls._user_prompt_builders.get(prompt_type)
    
    @classmethod
    def register_system_prompt(cls, name: str, prompt: str):
        """Register custom system prompt."""
        cls._system_prompts[name] = prompt
    
    @classmethod
    def register_user_prompt_builder(cls, name: str, builder):
        """Register custom user prompt builder."""
        cls._user_prompt_builders[name] = builder
