"""
Prompt Templates for Alpha Mining
Based on Alpha-GPT paradigm with CoSTEER enhancements
"""

# =============================================================================
# MINING AGENT PROMPTS
# =============================================================================

ALPHA_GENERATION_SYSTEM = """你是一位世界级的量化研究员，专门从事 Alpha 因子挖掘。
你需要基于给定的数据集和字段，生成高质量的 Alpha 表达式。

## 核心原则
1. **逻辑清晰**: 每个 Alpha 必须有明确的经济学假设
2. **语法正确**: 严格遵循 WorldQuant BRAIN 平台语法
3. **避免过拟合**: 表达式简洁，参数合理
4. **禁止前瞻**: 不能使用未来数据

## 输出格式
你必须以 JSON 格式输出，包含:
- expression: Alpha 表达式
- hypothesis: 背后的投资假设
- explanation: 逻辑解释
"""

ALPHA_GENERATION_USER = """## 挖掘任务
 
 **区域**: {region}
 **股票池**: {universe}
 **数据集**: {dataset_id}
 **描述**: {dataset_description}
 
 ## 可用字段
 {fields_json}
 ***禁止使用除上面给出的字段外的任何字段***
 
 ## 可用算子
 {operators_json}
 ***禁止使用除上面给出的算子外的任何算子***
 
 ## 成功模式参考 (Few-shot/Alpha-GPT)
 {few_shot_examples}
 
 ## 输入假设 (Input Hypotheses)
 {hypotheses_context}
 
 ## 避坑指南 (Negative Constraints & Syntax Rules)
 {negative_constraints}
 
 ### CRITICAL SYNTAX RULES (Violation = Compilation Failure):
 1. **Lookback Windows MUST be Integers**: Use `20`, `60`, NOT `20.0` or `0`.
    - Correct: `ts_mean(close, 20)`
    - Incorrect: `ts_mean(close, 20.0)`
 
 2. **Keyword Arguments are MANDATORY for certain parameters**:
    - `ts_regression(y, x, d, lag=0, rettype=0)`
    - `winsorize(x, std=4)` 
    - `ts_rank(x, d, constant=0)`
    - `hump(x, hump=0.01)`
    - `ts_quantile(x, d, driver="gaussian")`
 
 3. **Operator Specifics**:
    - `scale(x)`: Exactly 1 input.
    - `power(x, n)`: Use `power`, NOT `pow`.
    - `group_neutralize(x, sector)`: Group name (sector/industry) is NOT quoted.
    - `inverse(x)`: Exactly 1 input (1/x).
 
 4. **Logic**:
    - Avoid look-ahead bias (do not use `ts_step(-1)` or negative delays).
 
 5. **Mathematical Operations**:
    - Use standard infix operators (`+`, `-`, `*`, `/`) where possible.
    - **FORBIDDEN FUNCTIONS**: `neg()`, `add()`, `sub()`, `mul()`, `div()`.
    - Use `-x` for negation, NOT `neg(x)`.
    - Use `x - y` for subtraction, NOT `sub(x, y)` or `subtract(x, y)`.
 
 ## 任务
 请生成 {num_alphas} 个高质量 Alpha 表达式。
 
 输出 JSON 格式:
 ```json
 {{
   "alphas": [
     {{
       "expression": "rank(ts_delta(close, 5))",
       "hypothesis_id": 1,
       "hypothesis": "Short-term momentum reversal...",
       "explanation": "Ranking the 5-day price change...",
       "expected_sharpe": 1.5
     }}
   ]
 }}
 ```
 """

# =============================================================================
# HYPOTHESIS GENERATION
# =============================================================================

HYPOTHESIS_SYSTEM = """你是一位资深量化策略研究员，擅长从数据特征中提炼投资假设。"""

HYPOTHESIS_USER = """## 数据集分析

**数据集**: {dataset_id}
**类别**: {category} > {subcategory}
**描述**: {description}

**可用字段**:
{fields_summary}

## 任务
基于以上数据集特征，生成 3-5 个可验证的投资假设。

输出 JSON 格式:
```json
{{
  "hypotheses": [
    {{
      "idea": "假设描述",
      "rationale": "理论依据",
      "key_fields": ["field1", "field2"],
      "suggested_operators": ["ts_rank", "ts_corr"]
    }}
  ]
}}
```
"""

# =============================================================================
# SELF-CORRECTION PROMPT
# =============================================================================

SELF_CORRECT_SYSTEM = """你是一位 Alpha 表达式调试专家。你需要分析错误原因并修复表达式。"""

SELF_CORRECT_USER = """## 错误的表达式

```
{expression}
```

## 错误信息
{error_message}

## 错误类型
{error_type}

## 可用字段 (参考)
{available_fields}

## 任务
1. 分析错误原因
2. 提供修复后的表达式
3. 解释修改内容

输出 JSON 格式:
```json
{{
  "analysis": "错误原因分析",
  "fixed_expression": "修复后的表达式",
  "changes": "修改说明"
}}
```
"""

# =============================================================================
# LOGIC EXPLANATION
# =============================================================================

EXPLAIN_ALPHA_SYSTEM = """你是一位量化投资专家，擅长解释 Alpha 因子的经济学含义。"""

EXPLAIN_ALPHA_USER = """## Alpha 表达式

```
{expression}
```

## 使用的字段
{fields_used}

## 使用的算子
{operators_used}

## 模拟结果
- Sharpe Ratio: {sharpe}
- Returns: {returns}%
- Turnover: {turnover}

## 任务
用通俗易懂的语言解释这个 Alpha 因子：
1. 它捕捉了什么市场现象？
2. 为什么这个逻辑可能有效？
3. 潜在风险是什么？

输出简洁的中文解释 (2-3 句话)。
"""

# =============================================================================
# FEEDBACK ANALYSIS
# =============================================================================

FAILURE_ANALYSIS_SYSTEM = """你是一位 Alpha 挖掘流程优化专家，擅长从失败案例中总结教训。"""

FAILURE_ANALYSIS_USER = """## 今日失败样本 ({count} 个)

### 按错误类型分布
{error_distribution}

### 代表性失败案例
{sample_failures}

## 任务
1. 分析主要失败模式
2. 提取可复用的避坑规则
3. 建议 Prompt 优化方向

输出 JSON 格式:
```json
{{
  "patterns": [
    {{
      "pattern": "错误模式描述",
      "frequency": 0.3,
      "recommendation": "建议规避策略"
    }}
  ],
  "prompt_improvements": ["改进点1", "改进点2"]
}}
```
"""
