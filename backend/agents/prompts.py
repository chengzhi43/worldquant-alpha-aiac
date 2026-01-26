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
# ROUND ANALYSIS (EVOLUTION LOOP) - Enhanced with RD-Agent/Alpha-GPT insights
# =============================================================================

ROUND_ANALYSIS_SYSTEM = """你是一位 Alpha 挖掘策略专家，擅长从一轮挖掘结果中提炼深度洞察，指导下一轮迭代。

核心能力（参考 RD-Agent/Alpha-GPT/Chain-of-Alpha 论文）：
1. **结构化模式提取**: 从成功Alpha中提取可复用的算子组合模板
2. **失败根因分析**: 区分语法错误、字段问题、逻辑缺陷、质量不达标
3. **假设演进建议**: 基于结果推断哪些投资假设值得深入探索
4. **参数敏感性洞察**: 识别对窗口大小、衰减参数等敏感的模式

目标：生成可直接指导下一轮生成的结构化知识，而非泛泛的建议。"""

ROUND_ANALYSIS_USER = """## 本轮挖掘结果 (Round {iteration})

### 成功案例 (Success: {success_count})
{success_examples}

### 失败案例 (Failures: {failure_count})
{failure_examples}

### 任务上下文
数据集: {dataset_id}
区域: {region}

## 任务
请深度分析以上结果，提炼出对下一轮挖掘有帮助的结构化知识：

1. **成功模式 (Patterns)**: 
   - 提取具体的算子组合模板（如: `ts_rank(X, N) * ts_decay_linear(Y, M)`）
   - 分析为什么这个模式有效（经济逻辑）
   - 给出可泛化的变体建议

2. **失败陷阱 (Pitfalls)**: 
   - 识别导致失败的具体原因类型
   - 提供明确的避免建议

3. **字段洞察 (Field Insights)**:
   - 哪些字段在成功案例中频繁出现
   - 哪些字段导致了问题

4. **假设演进 (Hypothesis Evolution)**:
   - 哪些投资假设方向值得继续探索
   - 哪些假设应该放弃或调整

输出 JSON 格式:
```json
{{
  "new_patterns": [
    {{
      "pattern": "ts_rank(returns, 20) * ts_decay_linear(volume, 10)",
      "template": "ts_rank(MOMENTUM_FIELD, N) * ts_decay_linear(VOLUME_FIELD, M)",
      "description": "动量与成交量结合，短期动量(N=10-30)配合中期成交量衰减(M=5-15)",
      "economic_logic": "价量配合反映市场认可度",
      "variants": ["可尝试ts_corr替代乘法", "可加入波动率归一化"],
      "score": 0.8
    }}
  ],
  "new_pitfalls": [
    {{
      "pattern": "ts_zscore(fundamental_data)",
      "error_type": "DATA_QUALITY",
      "description": "基础数据缺失值过多导致 zscore 异常",
      "recommendation": "使用前先用 ts_mean 填充或改用 rank",
      "severity": "high"
    }}
  ],
  "field_insights": {{
    "effective_fields": ["returns", "volume", "close"],
    "problematic_fields": ["some_sparse_field"],
    "unexplored_fields": ["建议下轮尝试的字段"]
  }},
  "hypothesis_evolution": {{
    "promising_directions": ["动量-成交量交互", "波动率调整收益"],
    "abandon_directions": ["纯基本面因子在此数据集效果差"],
    "pivot_suggestions": ["从绝对值转向相对排名", "增加时序特征"]
  }}
}}
```
"""
