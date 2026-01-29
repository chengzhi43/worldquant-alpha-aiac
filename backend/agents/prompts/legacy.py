"""
Legacy prompt templates for backward compatibility.

These templates use string formatting directly (not the builder functions).
Prefer using the builder functions for new code.
"""


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
