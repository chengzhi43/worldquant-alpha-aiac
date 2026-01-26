"""
Prompt Templates for Alpha Mining
Based on Alpha-GPT paradigm with CoSTEER enhancements
"""

# =============================================================================
# MINING AGENT PROMPTS
# =============================================================================

# =============================================================================
# MINING AGENT PROMPTS
# =============================================================================

ALPHA_GENERATION_SYSTEM = """You are a quantitative researcher AI.
Your goal is to generate hypothesis-driven Alpha expressions based on financial data.

## Research Standards
1. **Hypothesis-Driven**: Every Alpha must stem from a coherent economic rationale.
2. **Robustness**: Prefer simple, explainable logic over complex overfitting.
3. **Validity**: Strictly adhere to the platform's operator and field syntax.
4. **No Look-ahead**: Ensure no future data usage.

## Output Format
JSON structure containing:
- `expression`: The Alpha code.
- `hypothesis`: The economic reasoning.
- `explanation`: Brief logic description.
"""

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
- Lookback windows must be integers (e.g., `20`, not `20.0`).
- Use keyword args where required (e.g., `ts_rank(x, d, constant=0)`).
- Max operators: 7
- Max fields: 3

## Knowledge Base (Context)
**Hypotheses**:
{hypotheses_context}

**Reference Patterns**:
{few_shot_examples}

## Task
Generate {num_alphas} distinct Alpha expressions derived from the provided hypotheses.

Output JSON:
```json
{{
  "alphas": [
    {{
      "expression": "rank(ts_delta(close, 5))",
      "hypothesis": "Short-term mean reversion...",
      "explanation": "captures price reversal..."
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
**类别**: {category} {subcategory}
**描述**: {description}

**核心可用字段 (Top 20)**:
{fields_summary}

## 成功模式参考 (Exploitation)
**利用历史高分模式进行微调**:
{success_patterns}

## 探索任务 (Exploration)
**强制探索以下随机/冷门字段**:
{exploration_fields}

## 任务
基于以上信息，生成 3-5 个投资假设。请采用 **混合策略 (Hybrid Strategy)**:

1. **稳健型 (Exploitation)**: 生成 1-2 个基于“成功模式”的假设，保证基础得分。
2. **探索型 (Exploration)**: 生成 1-2 个基于“探索任务”中字段的创新假设，寻找新 Alpha。

输出 JSON 格式:
```json
{{
  "hypotheses": [
    {{
      "idea": "假设描述 (注明 [Exploit] 或 [Explore])",
      "rationale": "理论依据 (特别是探索型假设的经济学逻辑)",
      "key_fields": ["field1", "field2"],
      "suggested_operators": ["ts_rank", "ts_corr"]
    }}
  ]
}}
```
"""

# =============================================================================
# CONCEPT DISTILLATION PROMPT
# =============================================================================

DISTILL_SYSTEM = """你是一位资深量化数据专家。你需要从海量数据字段中提炼出最核心的投资概念。"""

DISTILL_USER = """## 数据集背景
**数据集**: {dataset_id}
**描述**: {description}
**类别**: {category}

## 成功模式参考
{success_patterns}

## 字段概览 (按类别聚类)
{field_categories}

## 任务
该数据集包含大量字段。为了避免噪音，请根据数据集描述和成功模式，从 **上方列出的字段类别** 中挑选出 **3-5 个最相关** 的类别 (Concepts)。

**重要约束**:
1. **严格使用列表中的类别名称** (Available Categories)，**禁止发明新的类别名**。
2. 如果绝大多数字段都在 "General" 或 "Unknown" 类，请包含它们，否则无法检索到字段。
3. 请优先选择包含丰富信息量的特定类别 (如 "Analyst Estimates")。

输出 JSON 格式:
```json
{{
  "selected_concepts": ["Volatility", "Momentum", "General"],
  "reasoning": "数据集描述强调了高频波动特性..."
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

# =============================================================================
# ROUND ANALYSIS (EVOLUTION LOOP)
# =============================================================================

ROUND_ANALYSIS_SYSTEM = """你是一位 Alpha 挖掘策略专家，擅长从一轮挖掘结果中提炼洞察，指导下一轮迭代。
目标：通过分析本轮的成功和失败案例，总结出具体的模式(Patterns)和避坑指南(Pitfalls)，帮助下一轮生成更高质量的 Alpha。"""

ROUND_ANALYSIS_USER = """## 本轮挖掘结果 (Round {iteration})

### 成功案例 (Success: {success_count})
{success_examples}

### 失败案例 (Failures: {failure_count})
{failure_examples}

### 任务上下文
数据集: {dataset_id}
区域: {region}

## 任务
请分析以上结果，提炼出对下一轮挖掘有帮助的知识：

1. **成功模式 (Patterns)**: 成功 Alpha 中有哪些共性的算子组合或逻辑？(例如: ts_rank(volume) + ts_corr 表现好)
2. **失败陷阱 (Pitfalls)**: 哪些操作导致了普遍的错误？(例如: 某个字段在这个区域不可用，或者某种算子组合容易过拟合)
3. **策略调整**: 下一轮应该更关注什么？

输出 JSON 格式:
```json
{{
  "new_patterns": [
    {{
      "pattern": "ts_rank(returns) * ts_decay_linear(volume)",
      "description": "动量与成交量结合在近期表现稳定",
      "score": 0.8
    }}
  ],
  "new_pitfalls": [
    {{
      "pattern": "ts_zscore(fundamental_data)",
      "description": "基础数据缺失值过多导致 zscore 异常",
      "recommendation": "使用前先用 fillna 或 rank 处理"
    }}
  ]
}}
```
"""
