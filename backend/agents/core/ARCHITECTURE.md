# Core Architecture - Alpha Mining System

基于RD-Agent架构重构的核心模块，提供完整的实验追踪、知识进化和反馈系统。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AlphaMiningPipeline                              │
│                                                                         │
│  ┌─────────────┐   ┌──────────────────┐   ┌─────────────┐   ┌─────────┐│
│  │HypothesisGen│──►│Hypothesis2Experi│──►│Experiment   │──►│Experiment││
│  │             │   │      ment        │   │  Runner     │   │2Feedback ││
│  └─────────────┘   └──────────────────┘   └─────────────┘   └─────────┘│
│         │                  │                     │               │      │
│         ▼                  ▼                     ▼               ▼      │
│    Hypothesis ────► AlphaExperiment ────► AlphaExperiment ─► Feedback  │
│                                            (with results)              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          ExperimentTrace (DAG)                          │
│                                                                         │
│  ┌──────┐    ┌──────┐    ┌──────┐                                      │
│  │Exp 1 │───►│Exp 2 │───►│Exp 3 │  (线性探索)                          │
│  └──────┘    └──────┘    └──────┘                                      │
│       │                                                                 │
│       └──────────────────►┌──────┐                                     │
│                           │Exp 4 │  (分支探索)                          │
│                           └──────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EvolvingKnowledge                                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ KnowledgeRules (If..., then...)                                 │   │
│  │                                                                  │   │
│  │ SUCCESS: If turnover < 0.3 and sharpe > 1.5, then high quality  │   │
│  │ FAILURE: If using rank on boolean field, then likely syntax err │   │
│  │ OPTIMIZE: If sharpe positive but below threshold, try decay     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 实验系统 (experiment.py)

```python
# Hypothesis - 可测试的投资假设
hypothesis = Hypothesis(
    statement="Momentum persists in low volatility stocks",
    rationale="Low vol stocks have less noise, cleaner momentum signal",
    expected_signal="momentum",
    key_fields=["close", "volatility_20"],
    confidence="medium"
)

# AlphaExperiment - 完整的实验记录
experiment = AlphaExperiment(
    id="exp_001",
    hypothesis=hypothesis,
    expression="rank(ts_corr(close, volume, 20))",
    status=ExperimentStatus.COMPLETED,
    metrics={"sharpe": 1.8, "fitness": 0.45},
    quality_status="PASS"
)

# EvoStep - 进化步骤 (关联假设、知识、反馈)
step = EvoStep(
    experiment=experiment,
    queried_knowledge=knowledge,
    feedback=feedback,
    parent_indices=(0,)  # 派生自第0个实验
)
```

### 2. 反馈系统 (feedback.py)

```python
feedback = HypothesisFeedback(
    # 观察
    observations="Alpha achieved 1.8 sharpe with low turnover",
    
    # 假设评估
    hypothesis_evaluation="Hypothesis supported - momentum in low vol works",
    hypothesis_supported=True,
    
    # 归因 (关键！)
    attribution=AttributionType.HYPOTHESIS,  # vs IMPLEMENTATION
    attribution_confidence=0.8,
    
    # 决策
    decision=True,
    should_continue_direction=True,
    
    # 新假设建议
    new_hypothesis="Try extending to mid-cap stocks",
    
    # 知识提取
    knowledge_extracted=[
        "If volatility < 0.2, then momentum signals are cleaner",
        "If using ts_corr with volume, then 20-day window works well"
    ]
)
```

### 3. 追踪系统 (trace.py)

```python
# 创建追踪
trace = ExperimentTrace(
    dataset_id="fundamental6",
    region="USA",
    universe="TOP3000"
)

# 添加实验 (支持DAG结构)
idx1 = trace.add_experiment(exp1, fb1, parent_idx=None)  # 根节点
idx2 = trace.add_experiment(exp2, fb2, parent_idx=idx1)  # 子节点
idx3 = trace.add_experiment(exp3, fb3, parent_idx=None)  # 新分支

# 查询功能
sota = trace.get_sota()  # 获取最佳实验
lineage = trace.get_lineage(idx2)  # 获取血统 [exp1, exp2]
should_abandon, reason = trace.should_abandon_hypothesis("momentum works")
```

### 4. 知识系统 (knowledge.py, evolving_rag.py)

```python
# 知识规则
rule = KnowledgeRule(
    condition="using ts_zscore on price fields",
    conclusion="typically achieves good mean reversion signals",
    knowledge_type=KnowledgeType.SUCCESS_PATTERN,
    confidence=0.75
)

# 查询知识
knowledge = trace.query_knowledge(hypothesis)
print(knowledge.to_prompt_context())
# 输出:
# **What has worked**:
# - If ts_zscore on price, then good mean reversion (confidence: high)
# **What hasn't worked**:
# - If rank on boolean, then syntax error (confidence: high)

# 从实验自动提取知识
rag = AlphaRAGStrategy()
new_rules = rag.generate_knowledge(trace)
```

### 5. 场景系统 (scenario.py)

```python
scenario = AlphaMiningScenario(
    region="USA",
    universe="TOP3000",
    dataset_context=DatasetContext(
        dataset_id="fundamental6",
        fields=fields
    ),
    operator_context=OperatorContext(
        operators=operators
    )
)

# 生成LLM提示词上下文
context = scenario.get_scenario_all_desc(filtered_tag="hypothesis")
```

### 6. 管道系统 (pipeline.py)

```python
# 创建完整管道
pipeline = AlphaMiningPipeline(
    hypothesis_gen=LLMHypothesisGen(scenario, llm_service),
    h2e=LLMHypothesis2Experiment(scenario, llm_service),
    runner=BRAINExperimentRunner(brain_adapter, scenario),
    e2f=LLMExperiment2Feedback(scenario, llm_service)
)

# 运行单次迭代
result = await pipeline.run_iteration(trace)
trace.add_experiment(result.experiment, result.feedback)

# 运行多次
results = await pipeline.run_multiple(trace, num_experiments=5)
```

## 关键设计决策

### 1. 归因感知 (Attribution-Aware)

区分失败是由于假设还是实现：

```python
if feedback.attribution == AttributionType.HYPOTHESIS:
    # 假设本身有问题 - 记录到知识库，避免重复
    knowledge_base.add_rule(failure_rule)
elif feedback.attribution == AttributionType.IMPLEMENTATION:
    # 实现问题 - 不记录为假设失败，可以重试
    pass  # 不污染知识库
```

### 2. DAG追踪 (DAG Trace)

支持分支探索：

```
根实验 ─► 改进1 ─► 改进2
   │
   └──► 新方向1 ─► 新方向1改进
   │
   └──► 新方向2
```

### 3. 知识进化 (Knowledge Evolution)

- 从成功实验提取"如果...则..."规则
- 从失败实验提取警告模式
- 基于新证据更新置信度
- 支持持久化和加载

### 4. 组件解耦 (Component Decoupling)

每个组件单一职责：

| 组件 | 职责 |
|-----|------|
| HypothesisGen | 基于trace生成假设 |
| Hypothesis2Experiment | 假设→表达式 |
| ExperimentRunner | 执行模拟 |
| Experiment2Feedback | 生成结构化反馈 |

## 集成指南

### 渐进式迁移

```python
# 在现有 node_evaluate 中使用增强反馈
from backend.agents.core.integration import enhance_existing_node_evaluate

feedback = enhance_existing_node_evaluate(
    alpha=alpha,
    sim_result=result,
    hypothesis_dict={"statement": alpha.hypothesis}
)

# 基于归因决定是否记录知识
if feedback.should_record_to_knowledge_base():
    await rag_service.record_failure_pattern(...)
```

### 完全使用新架构

```python
from backend.agents.core import (
    create_scenario,
    create_alpha_pipeline,
    create_trace,
    run_enhanced_mining
)

# 创建场景
scenario = create_scenario(
    region="USA",
    dataset_id="fundamental6",
    fields=fields,
    operators=operators
)

# 创建追踪
trace = create_trace(dataset_id="fundamental6", region="USA")

# 运行挖掘
result = await run_enhanced_mining(
    llm_service=llm_service,
    brain_adapter=brain,
    dataset_id="fundamental6",
    fields=fields,
    operators=operators,
    num_experiments=5
)
```

## 文件结构

```
backend/agents/core/
├── __init__.py           # 统一导出
├── ARCHITECTURE.md       # 本文档
├── experiment.py         # Hypothesis, AlphaExperiment, EvoStep
├── feedback.py           # HypothesisFeedback, AttributionType
├── trace.py              # ExperimentTrace (DAG)
├── knowledge.py          # KnowledgeRule, EvolvingKnowledge
├── scenario.py           # Scenario, AlphaMiningScenario
├── pipeline.py           # Pipeline组件和组合
├── evolving_rag.py       # 增强RAG策略
└── integration.py        # 与现有系统集成
```

## 与RD-Agent的对应关系

| 本项目 | RD-Agent |
|-------|----------|
| `Hypothesis` | `Hypothesis` |
| `AlphaExperiment` | `Experiment` |
| `HypothesisFeedback` | `HypothesisFeedback` |
| `ExperimentTrace` | `Trace` |
| `EvolvingKnowledge` | `EvolvingKnowledgeBase` |
| `AlphaRAGStrategy` | `CoSTEERRAGStrategy` |
| `AlphaMiningPipeline` | `RDLoop` |
