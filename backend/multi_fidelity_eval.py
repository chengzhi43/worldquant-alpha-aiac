"""
Multi-Fidelity Evaluation Module - Tiered simulation for efficiency.

P2-2: Multi-fidelity evaluation
- Fast screening with small testPeriod
- Full validation only for top candidates
- Budget-aware simulation scheduling

This significantly reduces simulation costs while maintaining quality.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class FidelityLevel(Enum):
    """Simulation fidelity levels"""
    QUICK = "QUICK"      # P0Y3M - 3 months, fast screening
    MEDIUM = "MEDIUM"    # P1Y0M - 1 year, balance
    FULL = "FULL"        # P2Y0M - 2 years, final validation


@dataclass
class FidelityConfig:
    """Configuration for each fidelity level"""
    level: FidelityLevel
    test_period: str
    min_sharpe: float  # Minimum Sharpe to pass to next level
    min_fitness: float
    max_turnover: float
    
    @classmethod
    def quick(cls) -> "FidelityConfig":
        return cls(
            level=FidelityLevel.QUICK,
            test_period="P0Y3M",  # 3 months
            min_sharpe=1.0,       # Lower threshold for quick screen
            min_fitness=0.4,
            max_turnover=0.8
        )
    
    @classmethod
    def medium(cls) -> "FidelityConfig":
        return cls(
            level=FidelityLevel.MEDIUM,
            test_period="P1Y0M",  # 1 year
            min_sharpe=1.3,
            min_fitness=0.5,
            max_turnover=0.75
        )
    
    @classmethod
    def full(cls) -> "FidelityConfig":
        return cls(
            level=FidelityLevel.FULL,
            test_period="P2Y0M",  # 2 years
            min_sharpe=1.5,
            min_fitness=0.6,
            max_turnover=0.7
        )


@dataclass
class EvaluationResult:
    """Result of multi-fidelity evaluation"""
    expression: str
    passed: bool
    final_level: FidelityLevel
    
    # Metrics at each level
    quick_metrics: Optional[Dict] = None
    medium_metrics: Optional[Dict] = None
    full_metrics: Optional[Dict] = None
    
    # Timing
    quick_time_ms: int = 0
    medium_time_ms: int = 0
    full_time_ms: int = 0
    
    # Status
    alpha_id: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def total_time_ms(self) -> int:
        return self.quick_time_ms + self.medium_time_ms + self.full_time_ms
    
    @property
    def best_metrics(self) -> Optional[Dict]:
        """Return metrics from highest completed level"""
        if self.full_metrics:
            return self.full_metrics
        if self.medium_metrics:
            return self.medium_metrics
        return self.quick_metrics


class MultiFidelityEvaluator:
    """
    Multi-fidelity evaluation pipeline.
    
    Strategy:
    1. Quick screen all candidates with short testPeriod
    2. Medium evaluation for promising candidates
    3. Full evaluation only for near-PASS candidates
    
    This can reduce simulation costs by 60-80% while maintaining quality.
    """
    
    def __init__(
        self,
        brain_adapter,
        quick_config: Optional[FidelityConfig] = None,
        medium_config: Optional[FidelityConfig] = None,
        full_config: Optional[FidelityConfig] = None,
        skip_medium: bool = False,  # Go directly from quick to full
        quick_pass_ratio: float = 0.3,  # Top 30% of quick pass to next level
        medium_pass_ratio: float = 0.5,  # Top 50% of medium pass to full
    ):
        self.brain = brain_adapter
        self.quick_config = quick_config or FidelityConfig.quick()
        self.medium_config = medium_config or FidelityConfig.medium()
        self.full_config = full_config or FidelityConfig.full()
        self.skip_medium = skip_medium
        self.quick_pass_ratio = quick_pass_ratio
        self.medium_pass_ratio = medium_pass_ratio
        
    async def evaluate_batch(
        self,
        expressions: List[str],
        region: str = "USA",
        universe: str = "TOP3000",
        delay: int = 1,
        decay: int = 4,
        neutralization: str = "SUBINDUSTRY",
        max_full_evals: int = 10
    ) -> List[EvaluationResult]:
        """
        Evaluate batch of expressions using multi-fidelity approach.
        
        Args:
            expressions: List of alpha expressions
            max_full_evals: Maximum number of full evaluations (budget control)
            
        Returns:
            List of EvaluationResult with metrics at appropriate fidelity
        """
        import time
        
        results = []
        
        # =================================================================
        # STAGE 1: Quick screening (all candidates)
        # =================================================================
        logger.info(f"[MultiFidelity] Stage 1: Quick screening {len(expressions)} candidates")
        
        quick_results = []
        start = time.time()
        
        for expr in expressions:
            result = EvaluationResult(expression=expr, passed=False, final_level=FidelityLevel.QUICK)
            
            try:
                sim_result = await self.brain.simulate_alpha(
                    expression=expr,
                    region=region,
                    universe=universe,
                    delay=delay,
                    decay=decay,
                    neutralization=neutralization,
                    test_period=self.quick_config.test_period
                )
                
                if sim_result.get("success"):
                    result.quick_metrics = sim_result.get("metrics", {})
                    result.alpha_id = sim_result.get("alpha_id")
                    
                    # Check if passes quick thresholds
                    sharpe = result.quick_metrics.get("sharpe", 0) or 0
                    fitness = result.quick_metrics.get("fitness", 0) or 0
                    turnover = result.quick_metrics.get("turnover", 1) or 1
                    
                    if (sharpe >= self.quick_config.min_sharpe and
                        fitness >= self.quick_config.min_fitness and
                        turnover <= self.quick_config.max_turnover):
                        result.passed = True
                else:
                    result.error = sim_result.get("error", "Quick sim failed")
                    
            except Exception as e:
                result.error = str(e)
                
            result.quick_time_ms = int((time.time() - start) * 1000)
            quick_results.append(result)
            start = time.time()
            
        # Sort by quick score for next stage selection
        def quick_score(r: EvaluationResult) -> float:
            if not r.quick_metrics:
                return -999
            return (r.quick_metrics.get("sharpe", 0) or 0) * (r.quick_metrics.get("fitness", 0) or 0)
        
        quick_results.sort(key=quick_score, reverse=True)
        
        # Select top candidates for next stage
        passed_quick = [r for r in quick_results if r.passed]
        n_next = min(
            int(len(passed_quick) * self.quick_pass_ratio),
            max_full_evals * 2  # Allow 2x buffer for medium stage
        )
        candidates_for_next = passed_quick[:max(n_next, 1)] if passed_quick else []
        
        logger.info(f"[MultiFidelity] Quick stage: {len(passed_quick)}/{len(expressions)} passed, "
                   f"{len(candidates_for_next)} advancing")
        
        # =================================================================
        # STAGE 2: Medium evaluation (optional)
        # =================================================================
        if not self.skip_medium and candidates_for_next:
            logger.info(f"[MultiFidelity] Stage 2: Medium eval {len(candidates_for_next)} candidates")
            
            for result in candidates_for_next:
                start = time.time()
                
                try:
                    sim_result = await self.brain.simulate_alpha(
                        expression=result.expression,
                        region=region,
                        universe=universe,
                        delay=delay,
                        decay=decay,
                        neutralization=neutralization,
                        test_period=self.medium_config.test_period
                    )
                    
                    if sim_result.get("success"):
                        result.medium_metrics = sim_result.get("metrics", {})
                        result.final_level = FidelityLevel.MEDIUM
                        
                        sharpe = result.medium_metrics.get("sharpe", 0) or 0
                        fitness = result.medium_metrics.get("fitness", 0) or 0
                        turnover = result.medium_metrics.get("turnover", 1) or 1
                        
                        result.passed = (
                            sharpe >= self.medium_config.min_sharpe and
                            fitness >= self.medium_config.min_fitness and
                            turnover <= self.medium_config.max_turnover
                        )
                    else:
                        result.passed = False
                        result.error = sim_result.get("error")
                        
                except Exception as e:
                    result.passed = False
                    result.error = str(e)
                    
                result.medium_time_ms = int((time.time() - start) * 1000)
                
            # Select for full evaluation
            passed_medium = [r for r in candidates_for_next if r.passed]
            n_full = min(int(len(passed_medium) * self.medium_pass_ratio), max_full_evals)
            candidates_for_full = passed_medium[:max(n_full, 1)] if passed_medium else []
            
            logger.info(f"[MultiFidelity] Medium stage: {len(passed_medium)}/{len(candidates_for_next)} passed, "
                       f"{len(candidates_for_full)} advancing to full")
        else:
            candidates_for_full = candidates_for_next[:max_full_evals]
            
        # =================================================================
        # STAGE 3: Full evaluation (final candidates)
        # =================================================================
        if candidates_for_full:
            logger.info(f"[MultiFidelity] Stage 3: Full eval {len(candidates_for_full)} candidates")
            
            for result in candidates_for_full:
                start = time.time()
                
                try:
                    sim_result = await self.brain.simulate_alpha(
                        expression=result.expression,
                        region=region,
                        universe=universe,
                        delay=delay,
                        decay=decay,
                        neutralization=neutralization,
                        test_period=self.full_config.test_period
                    )
                    
                    if sim_result.get("success"):
                        result.full_metrics = sim_result.get("metrics", {})
                        result.alpha_id = sim_result.get("alpha_id")  # Use full sim's alpha_id
                        result.final_level = FidelityLevel.FULL
                        
                        sharpe = result.full_metrics.get("sharpe", 0) or 0
                        fitness = result.full_metrics.get("fitness", 0) or 0
                        turnover = result.full_metrics.get("turnover", 1) or 1
                        
                        result.passed = (
                            sharpe >= self.full_config.min_sharpe and
                            fitness >= self.full_config.min_fitness and
                            turnover <= self.full_config.max_turnover
                        )
                    else:
                        result.passed = False
                        result.error = sim_result.get("error")
                        
                except Exception as e:
                    result.passed = False
                    result.error = str(e)
                    
                result.full_time_ms = int((time.time() - start) * 1000)
                
        # Combine all results
        # Full evaluated candidates are already in quick_results, just ensure final state
        final_passed = [r for r in quick_results if r.passed and r.final_level == FidelityLevel.FULL]
        
        logger.info(f"[MultiFidelity] Complete: {len(final_passed)}/{len(expressions)} final PASS")
        
        return quick_results
    
    def estimate_savings(self, total_candidates: int, pass_rates: Tuple[float, float, float] = (0.3, 0.5, 0.8)) -> Dict:
        """
        Estimate simulation cost savings vs full evaluation.
        
        Args:
            total_candidates: Number of candidates to evaluate
            pass_rates: (quick_pass_rate, medium_pass_rate, full_pass_rate)
        """
        quick_pass, medium_pass, full_pass = pass_rates
        
        # Traditional: all candidates get full eval
        traditional_sims = total_candidates
        traditional_time_factor = 1.0  # Full testPeriod
        
        # Multi-fidelity
        quick_sims = total_candidates
        quick_time_factor = 0.15  # ~3 months vs 2 years
        
        medium_candidates = int(total_candidates * quick_pass * self.quick_pass_ratio)
        medium_sims = medium_candidates if not self.skip_medium else 0
        medium_time_factor = 0.5  # 1 year vs 2 years
        
        full_candidates = int(medium_candidates * medium_pass * self.medium_pass_ratio)
        full_sims = full_candidates
        full_time_factor = 1.0
        
        # Calculate equivalent full-sim cost
        mf_cost = (
            quick_sims * quick_time_factor +
            medium_sims * medium_time_factor +
            full_sims * full_time_factor
        )
        
        traditional_cost = traditional_sims * traditional_time_factor
        
        savings = 1 - (mf_cost / traditional_cost) if traditional_cost > 0 else 0
        
        return {
            "traditional_equivalent_sims": traditional_sims,
            "multi_fidelity_equivalent_sims": round(mf_cost, 1),
            "savings_percentage": round(savings * 100, 1),
            "breakdown": {
                "quick_sims": quick_sims,
                "medium_sims": medium_sims,
                "full_sims": full_sims,
            }
        }
