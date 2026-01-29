"""
Pipeline components based on RD-Agent architecture.

This module defines the clear component interfaces:
- HypothesisGen: Generate hypotheses from trace
- Hypothesis2Experiment: Convert hypothesis to experiment
- ExperimentRunner: Run experiments (simulation)
- Experiment2Feedback: Generate feedback from experiment results

Each component has:
1. prepare_context(): Extract context from trace
2. convert_response(): Parse LLM response
3. Main method (gen/convert/run/generate_feedback)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from backend.agents.core.experiment import (
    AlphaExperiment,
    ExperimentStatus,
    Hypothesis,
)
from backend.agents.core.feedback import (
    AttributionType,
    HypothesisFeedback,
)
from backend.agents.core.knowledge import QueriedKnowledge
from backend.agents.core.scenario import AlphaMiningScenario, Scenario
from backend.agents.core.trace import ExperimentTrace

if TYPE_CHECKING:
    from backend.agents.services.llm_service import LLMService


# =============================================================================
# Hypothesis Generation
# =============================================================================

class HypothesisGen(ABC):
    """
    Abstract hypothesis generator.
    
    Based on RD-Agent's HypothesisGen.
    
    Responsibilities:
    1. Analyze trace history to understand what's been tried
    2. Query knowledge base for relevant patterns
    3. Generate novel, testable hypothesis
    """
    
    def __init__(self, scen: Scenario):
        self.scen = scen
    
    @abstractmethod
    def gen(
        self,
        trace: ExperimentTrace,
        queried_knowledge: Optional[QueriedKnowledge] = None
    ) -> Hypothesis:
        """
        Generate a new hypothesis based on trace.
        
        Args:
            trace: Experiment history
            queried_knowledge: Pre-queried knowledge (optional)
            
        Returns:
            A new hypothesis to test
        """


class LLMHypothesisGen(HypothesisGen):
    """
    LLM-based hypothesis generator.
    
    Implements the RD-Agent pattern:
    1. prepare_context() - Extract relevant context
    2. Call LLM with structured prompt
    3. convert_response() - Parse response to Hypothesis
    """
    
    def __init__(self, scen: Scenario, llm_service: 'LLMService'):
        super().__init__(scen)
        self.llm_service = llm_service
    
    def prepare_context(self, trace: ExperimentTrace) -> Tuple[Dict[str, Any], bool]:
        """
        Prepare context for LLM prompt.
        
        Returns:
            (context_dict, use_json_mode)
        """
        # Get trace history as context
        history_context = trace.to_prompt_context() if trace else "No prior experiments."
        
        # Get SOTA info
        sota_exp, sota_hypo = None, None
        if trace:
            sota_hypo, sota_exp = trace.get_sota_hypothesis_and_experiment()
        
        sota_context = ""
        if sota_exp:
            sota_context = f"""
Current Best (SOTA):
- Hypothesis: {sota_hypo.statement if sota_hypo else 'N/A'}
- Expression: {sota_exp.expression[:80]}...
- Sharpe: {sota_exp.get_sharpe()}, Fitness: {sota_exp.get_fitness()}
"""
        
        # Query knowledge
        knowledge_context = ""
        if trace and trace.knowledge_base:
            knowledge = trace.query_knowledge()
            knowledge_context = knowledge.to_prompt_context()
        
        return {
            "scenario": self.scen.get_scenario_all_desc(filtered_tag="hypothesis"),
            "hypothesis_and_feedback": history_context,
            "sota_context": sota_context,
            "knowledge": knowledge_context,
            "hypothesis_output_format": self._get_output_format(),
            "hypothesis_specification": self._get_specification(),
        }, True
    
    def _get_output_format(self) -> str:
        return """{
    "hypothesis": "Clear, testable statement about what drives returns",
    "rationale": "Economic/behavioral reasoning supporting the hypothesis",
    "expected_signal": "momentum | mean_reversion | value | quality | other",
    "key_fields": ["field1", "field2"],
    "suggested_operators": ["op1", "op2"],
    "confidence": "high | medium | low",
    "concise_knowledge": "One-line transferable insight"
}"""
    
    def _get_specification(self) -> str:
        return """A good hypothesis should be:
1. **Precise**: Clearly state what relationship you expect
2. **Testable**: Can be validated through simulation
3. **Novel**: Not identical to recent failed hypotheses
4. **Grounded**: Based on economic reasoning, not arbitrary patterns

Avoid:
- Vague statements ("stocks with good fundamentals outperform")
- Overly complex hypotheses testing multiple effects at once
- Hypotheses that have already failed multiple times
"""
    
    def convert_response(self, response: str) -> Hypothesis:
        """Convert LLM response to Hypothesis object."""
        import json
        
        try:
            data = json.loads(response) if isinstance(response, str) else response
        except json.JSONDecodeError:
            # Fallback parsing
            data = {"hypothesis": response, "rationale": ""}
        
        return Hypothesis.from_dict(data)
    
    async def gen(
        self,
        trace: ExperimentTrace,
        queried_knowledge: Optional[QueriedKnowledge] = None
    ) -> Hypothesis:
        """Generate hypothesis using LLM."""
        context, use_json = self.prepare_context(trace)
        
        # Build prompt
        from backend.agents.prompts.hypothesis import (
            HYPOTHESIS_SYSTEM,
            build_hypothesis_prompt,
        )
        
        system_prompt = HYPOTHESIS_SYSTEM.format(
            scenario=context["scenario"],
            output_format=context["hypothesis_output_format"],
            specification=context["hypothesis_specification"],
        )
        
        user_prompt = build_hypothesis_prompt(
            experiment_trace=context["hypothesis_and_feedback"],
            sota_context=context.get("sota_context", ""),
            knowledge=context.get("knowledge", ""),
        )
        
        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format="json" if use_json else None
        )
        
        return self.convert_response(response)


# =============================================================================
# Hypothesis to Experiment Conversion
# =============================================================================

class Hypothesis2Experiment(ABC):
    """
    Abstract converter from hypothesis to experiment.
    
    Based on RD-Agent's Hypothesis2Experiment.
    
    Responsibilities:
    1. Take a hypothesis and trace
    2. Generate concrete alpha expression implementing the hypothesis
    3. Return AlphaExperiment ready for execution
    """
    
    @abstractmethod
    def convert(
        self,
        hypothesis: Hypothesis,
        trace: ExperimentTrace
    ) -> AlphaExperiment:
        """
        Convert hypothesis to executable experiment.
        
        Args:
            hypothesis: The hypothesis to implement
            trace: Experiment history for context
            
        Returns:
            AlphaExperiment ready for execution
        """


class LLMHypothesis2Experiment(Hypothesis2Experiment):
    """
    LLM-based hypothesis to experiment converter.
    """
    
    def __init__(self, scen: Scenario, llm_service: 'LLMService'):
        self.scen = scen
        self.llm_service = llm_service
    
    def prepare_context(
        self,
        hypothesis: Hypothesis,
        trace: ExperimentTrace
    ) -> Tuple[Dict[str, Any], bool]:
        """Prepare context for LLM prompt."""
        
        # Get similar past experiments
        similar_experiments = ""
        if trace:
            similar = trace.get_experiments_for_hypothesis(hypothesis.statement, threshold=0.6)
            if similar:
                similar_experiments = "\n".join([
                    f"- Expression: {exp.expression[:60]}... Result: {'Success' if fb and fb.decision else 'Failed'}"
                    for exp, fb in similar[:3]
                ])
        
        return {
            "target_hypothesis": str(hypothesis),
            "scenario": self.scen.get_scenario_all_desc(filtered_tag="implementation"),
            "similar_experiments": similar_experiments,
            "experiment_output_format": self._get_output_format(),
        }, True
    
    def _get_output_format(self) -> str:
        return """{
    "expression": "rank(ts_mean(close, 20)) - rank(ts_mean(close, 5))",
    "explanation": "Explanation of how this implements the hypothesis",
    "fields_used": ["close"],
    "operators_used": ["rank", "ts_mean"]
}"""
    
    def convert_response(
        self,
        response: str,
        hypothesis: Hypothesis
    ) -> AlphaExperiment:
        """Convert LLM response to AlphaExperiment."""
        import json
        import uuid
        
        try:
            data = json.loads(response) if isinstance(response, str) else response
        except json.JSONDecodeError:
            data = {"expression": response, "explanation": ""}
        
        return AlphaExperiment(
            id=str(uuid.uuid4())[:8],
            hypothesis=hypothesis,
            expression=data.get("expression", ""),
            explanation=data.get("explanation", ""),
            fields_used=data.get("fields_used", []),
            status=ExperimentStatus.PENDING,
        )
    
    async def convert(
        self,
        hypothesis: Hypothesis,
        trace: ExperimentTrace
    ) -> AlphaExperiment:
        """Convert hypothesis to experiment using LLM."""
        context, use_json = self.prepare_context(hypothesis, trace)
        
        from backend.agents.prompts.generation import (
            ALPHA_GENERATION_SYSTEM,
            build_alpha_generation_prompt,
        )
        
        system_prompt = ALPHA_GENERATION_SYSTEM.format(
            scenario=context["scenario"],
            output_format=context["experiment_output_format"],
        )
        
        user_prompt = build_alpha_generation_prompt(
            target_hypothesis=context["target_hypothesis"],
            similar_experiments=context.get("similar_experiments", ""),
        )
        
        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format="json" if use_json else None
        )
        
        return self.convert_response(response, hypothesis)


# =============================================================================
# Experiment Runner (Simulation)
# =============================================================================

class ExperimentRunner(ABC):
    """
    Abstract experiment runner.
    
    Executes experiments (simulations) and populates results.
    """
    
    @abstractmethod
    async def run(self, experiment: AlphaExperiment) -> AlphaExperiment:
        """
        Run the experiment.
        
        Args:
            experiment: Experiment to run
            
        Returns:
            Same experiment with results populated
        """


class BRAINExperimentRunner(ExperimentRunner):
    """
    WorldQuant BRAIN experiment runner.
    """
    
    def __init__(self, brain_adapter, scen: AlphaMiningScenario):
        self.brain = brain_adapter
        self.scen = scen
    
    async def run(self, experiment: AlphaExperiment) -> AlphaExperiment:
        """Run experiment on BRAIN platform."""
        import time
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.running_info.started_at = time.time()
        
        try:
            # Simulate
            result = await self.brain.simulate_alpha(
                expression=experiment.expression,
                region=self.scen.region,
                universe=self.scen.universe,
                delay=1,
                decay=4,
                neutralization="INDUSTRY"
            )
            
            experiment.running_info.completed_at = time.time()
            experiment.running_info.running_time_ms = int(
                (experiment.running_info.completed_at - experiment.running_info.started_at) * 1000
            )
            
            if result.get("success"):
                experiment.status = ExperimentStatus.COMPLETED
                experiment.alpha_id = result.get("alpha_id")
                experiment.metrics = result.get("metrics", {})
                experiment.running_info.result = result
            else:
                experiment.status = ExperimentStatus.FAILED
                experiment.error_type = result.get("error_type", "SIMULATION_ERROR")
                experiment.error_message = result.get("error", "Simulation failed")
                
        except Exception as e:
            experiment.status = ExperimentStatus.FAILED
            experiment.error_type = "EXCEPTION"
            experiment.error_message = str(e)
        
        return experiment


# =============================================================================
# Experiment to Feedback
# =============================================================================

class Experiment2Feedback(ABC):
    """
    Abstract feedback generator.
    
    Based on RD-Agent's Experiment2Feedback.
    
    Responsibilities:
    1. Analyze experiment results
    2. Evaluate if hypothesis was supported
    3. Attribute failure to hypothesis vs implementation
    4. Suggest next hypothesis
    5. Extract transferable knowledge
    """
    
    def __init__(self, scen: Scenario):
        self.scen = scen
    
    @abstractmethod
    async def generate_feedback(
        self,
        experiment: AlphaExperiment,
        trace: ExperimentTrace
    ) -> HypothesisFeedback:
        """
        Generate structured feedback from experiment.
        
        Args:
            experiment: Completed experiment
            trace: Experiment history for context
            
        Returns:
            HypothesisFeedback with analysis and suggestions
        """


class LLMExperiment2Feedback(Experiment2Feedback):
    """
    LLM-based feedback generator.
    
    Key responsibilities:
    1. Determine if hypothesis was validated or refuted
    2. Attribute failures (hypothesis vs implementation)
    3. Generate new hypothesis suggestion
    4. Extract knowledge rules
    """
    
    def __init__(self, scen: Scenario, llm_service: 'LLMService'):
        super().__init__(scen)
        self.llm_service = llm_service
    
    def prepare_context(
        self,
        experiment: AlphaExperiment,
        trace: ExperimentTrace
    ) -> Dict[str, Any]:
        """Prepare context for feedback generation."""
        
        # Get experiment info
        hypothesis_text = experiment.hypothesis.statement if experiment.hypothesis else ""
        expression = experiment.expression
        metrics = experiment.metrics
        error = experiment.error_message
        
        # Get recent similar experiments for context
        similar_context = ""
        if trace and hypothesis_text:
            similar = trace.get_experiments_for_hypothesis(hypothesis_text, threshold=0.7)
            if similar:
                similar_context = "\n".join([
                    f"- Previous attempt: {exp.expression[:50]}... -> {'Success' if fb and fb.decision else 'Failed'}"
                    for exp, fb in similar[:3]
                ])
        
        return {
            "hypothesis": hypothesis_text,
            "expression": expression,
            "metrics": metrics,
            "error": error,
            "status": experiment.status.value,
            "quality_status": experiment.quality_status,
            "failed_checks": experiment.failed_checks,
            "similar_attempts": similar_context,
        }
    
    def _get_output_format(self) -> str:
        return """{
    "observation": "What was observed in the experiment",
    "hypothesis_evaluation": "Was the hypothesis supported or refuted?",
    "hypothesis_supported": true/false/null,
    "attribution": {
        "primary_cause": "hypothesis | implementation | both | unknown",
        "confidence": 0.0-1.0,
        "evidence": ["evidence1", "evidence2"]
    },
    "decision": {
        "success": true/false,
        "reasoning": "Why this is considered success/failure",
        "should_retry_implementation": true/false
    },
    "new_hypothesis": {
        "statement": "Suggested next hypothesis to try",
        "rationale": "Why this is a good next step"
    },
    "knowledge_extraction": {
        "confident_knowledge": ["If ..., then ..."],
        "tentative_knowledge": ["Might be true: ..."],
        "should_not_conclude": ["We should NOT conclude that..."]
    }
}"""
    
    def convert_response(self, response: str) -> HypothesisFeedback:
        """Convert LLM response to HypothesisFeedback."""
        import json
        
        try:
            data = json.loads(response) if isinstance(response, str) else response
        except json.JSONDecodeError:
            data = {}
        
        return HypothesisFeedback.from_dict(data)
    
    def _generate_heuristic_feedback(
        self,
        experiment: AlphaExperiment
    ) -> HypothesisFeedback:
        """Generate feedback using heuristics (fallback)."""
        
        # Determine success
        is_success = experiment.quality_status == "PASS"
        
        # Determine attribution
        if experiment.error_type == "SYNTAX_ERROR":
            attribution = AttributionType.IMPLEMENTATION
            should_retry = True
        elif experiment.error_type == "SIMULATION_ERROR":
            attribution = AttributionType.IMPLEMENTATION
            should_retry = True
        elif experiment.quality_status == "FAIL" and experiment.metrics:
            # Has metrics but failed quality - could be hypothesis
            sharpe = experiment.metrics.get("sharpe", 0)
            if sharpe <= 0:
                attribution = AttributionType.HYPOTHESIS
                should_retry = False
            else:
                attribution = AttributionType.BOTH
                should_retry = True
        else:
            attribution = AttributionType.UNKNOWN
            should_retry = True
        
        return HypothesisFeedback(
            observations=f"Experiment {'succeeded' if is_success else 'failed'} with status {experiment.quality_status}",
            hypothesis_evaluation=f"Hypothesis {'appears supported' if is_success else 'not validated'} based on metrics",
            hypothesis_supported=is_success,
            attribution=attribution,
            decision=is_success,
            reason=f"Quality status: {experiment.quality_status}, Sharpe: {experiment.get_sharpe()}",
            should_retry_implementation=should_retry,
            should_modify_hypothesis=attribution == AttributionType.HYPOTHESIS,
        )
    
    async def generate_feedback(
        self,
        experiment: AlphaExperiment,
        trace: ExperimentTrace
    ) -> HypothesisFeedback:
        """Generate feedback using LLM."""
        
        context = self.prepare_context(experiment, trace)
        
        try:
            from backend.agents.prompts.analysis import (
                FEEDBACK_GENERATION_SYSTEM,
                build_enhanced_feedback_prompt,
            )
            
            system_prompt = FEEDBACK_GENERATION_SYSTEM
            user_prompt = build_enhanced_feedback_prompt(
                hypothesis=context["hypothesis"],
                expression=context["expression"],
                metrics=context["metrics"],
                status=context["quality_status"],
                failed_checks=context["failed_checks"],
                error=context["error"],
                similar_attempts=context["similar_attempts"],
            )
            
            response = await self.llm_service.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_format="json"
            )
            
            return self.convert_response(response)
            
        except Exception as e:
            # Fallback to heuristic
            return self._generate_heuristic_feedback(experiment)


# =============================================================================
# Complete Pipeline
# =============================================================================

@dataclass
class PipelineResult:
    """Result of running one pipeline iteration."""
    experiment: AlphaExperiment
    feedback: HypothesisFeedback
    knowledge_updated: bool = False


class AlphaMiningPipeline:
    """
    Complete Alpha Mining Pipeline.
    
    Orchestrates the full flow:
    HypothesisGen -> Hypothesis2Experiment -> ExperimentRunner -> Experiment2Feedback
    
    Usage:
        pipeline = AlphaMiningPipeline(hypothesis_gen, h2e, runner, e2f)
        result = await pipeline.run_iteration(trace)
        trace.add_experiment(result.experiment, result.feedback)
    """
    
    def __init__(
        self,
        hypothesis_gen: HypothesisGen,
        h2e: Hypothesis2Experiment,
        runner: ExperimentRunner,
        e2f: Experiment2Feedback
    ):
        self.hypothesis_gen = hypothesis_gen
        self.h2e = h2e
        self.runner = runner
        self.e2f = e2f
    
    async def run_iteration(
        self,
        trace: ExperimentTrace,
        hypothesis: Optional[Hypothesis] = None
    ) -> PipelineResult:
        """
        Run one complete pipeline iteration.
        
        Args:
            trace: Experiment history
            hypothesis: Optional pre-defined hypothesis (skip generation if provided)
            
        Returns:
            PipelineResult with experiment and feedback
        """
        # Step 1: Generate hypothesis (if not provided)
        if hypothesis is None:
            hypothesis = await self.hypothesis_gen.gen(trace)
        
        # Step 2: Convert to experiment
        experiment = await self.h2e.convert(hypothesis, trace)
        
        # Step 3: Run experiment
        experiment = await self.runner.run(experiment)
        
        # Step 4: Generate feedback
        feedback = await self.e2f.generate_feedback(experiment, trace)
        
        return PipelineResult(
            experiment=experiment,
            feedback=feedback,
            knowledge_updated=feedback.should_record_to_knowledge_base()
        )
    
    async def run_multiple(
        self,
        trace: ExperimentTrace,
        num_experiments: int = 3
    ) -> List[PipelineResult]:
        """
        Run multiple pipeline iterations.
        
        Experiments are run sequentially, each building on the trace.
        """
        results = []
        
        for i in range(num_experiments):
            result = await self.run_iteration(trace)
            
            # Add to trace
            trace.add_experiment(result.experiment, result.feedback)
            results.append(result)
            
            # Check if we should stop
            if result.feedback.should_abandon:
                break
        
        return results
