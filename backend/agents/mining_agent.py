"""
Mining Agent - High-level Entry Point
Wraps LangGraph workflow with backward-compatible interface

This module provides:
1. Backward-compatible interface (run_mining_iteration)
2. Clean access to LangGraph workflow
3. Dependency injection for testing
"""

from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.models import MiningTask, Alpha
from backend.agents.graph import MiningWorkflow, create_mining_graph
from backend.agents.services import LLMService, get_llm_service
from backend.agents.services.trace_service import TraceService
from backend.agents.strategy_agent import StrategyAgent, create_strategy_agent, RoundMetrics
from backend.adapters.brain_adapter import BrainAdapter


class MiningAgent:
    """
    Mining Agent - High-level interface for alpha mining.
    
    Now powered by LangGraph for:
    - Self-correction loops
    - Conditional routing
    - Full trace recording
    - Checkpointing support
    
    Usage:
        agent = MiningAgent(db, brain)
        alphas = await agent.run_mining_iteration(task, dataset_id, fields, operators)
    """
    
    def __init__(
        self,
        db: AsyncSession,
        brain_adapter: BrainAdapter = None,
        llm_service: LLMService = None
    ):
        """
        Initialize MiningAgent.
        
        Args:
            db: Async SQLAlchemy session
            brain_adapter: BRAIN platform adapter (optional)
            llm_service: LLM service instance (optional)
        """
        self.db = db
        self.brain = brain_adapter or BrainAdapter()
        self.llm_service = llm_service or get_llm_service()
        
        # Create LangGraph workflow
        self._workflow = create_mining_graph(
            db=db,
            brain=self.brain,
            llm_service=self.llm_service
        )
        
        # Create Strategy Agent for intelligent next-round planning
        self._strategy_agent = create_strategy_agent(llm_service=self.llm_service)
        
        logger.info("[MiningAgent] Initialized with LangGraph workflow + StrategyAgent")
    
    async def run_mining_iteration(
        self,
        task: MiningTask,
        dataset_id: str,
        fields: List[Dict],
        operators: List[Dict],
        num_alphas: int = 3,
        iteration: int = 1
    ) -> List[Alpha]:
        """
        Run a single mining iteration for a dataset.
        
        This is the backward-compatible interface that:
        1. Executes the LangGraph workflow
        2. Persists results to database
        3. Returns list of generated Alpha models
        
        Args:
            task: Mining task instance
            dataset_id: Dataset to mine
            fields: Available data fields
            operators: Available operators
            num_alphas: Target number of alphas to generate
            iteration: Current iteration number (default: 1)
            
        Returns:
            List of successfully generated Alpha models
        """
        logger.info(
            f"[MiningAgent] Starting iteration | "
            f"task={task.id} dataset={dataset_id} target={num_alphas} iter={iteration}"
        )
        
        # Initialize TraceService for Real-Time Tracing
        trace_service = TraceService(self.db, task.id, iteration=iteration)
        
        try:
            # Run LangGraph workflow with persistence
            # Pass TraceService via config
            result = await self._workflow.run_with_persistence(
                task=task,
                dataset_id=dataset_id,
                fields=fields,
                operators=operators,
                num_alphas=num_alphas,
                config={"configurable": {"trace_service": trace_service}}
            )
            
            # Convert results to Alpha models for backward compatibility
            generated_alphas = []
            for alpha_result in result.get("generated_alphas", []):
                # Query the persisted alpha
                from sqlalchemy import select
                query = select(Alpha).where(
                    Alpha.task_id == task.id,
                    Alpha.expression == alpha_result.expression
                ).order_by(Alpha.id.desc()).limit(1)
                
                db_result = await self.db.execute(query)
                alpha = db_result.scalar_one_or_none()
                
                if alpha:
                    generated_alphas.append(alpha)
            
            logger.info(
                f"[MiningAgent] Iteration complete | "
                f"alphas={len(generated_alphas)} failures={len(result.get('failures', []))}"
            )
            
            return generated_alphas
            
        except Exception as e:
            logger.error(f"[MiningAgent] Iteration failed | error={e}")
            raise
    
    async def run_workflow(
        self,
        task: MiningTask,
        dataset_id: str,
        fields: List[Dict],
        operators: List[Dict],
        num_alphas: int = 3
    ) -> Dict[str, Any]:
        """
        Run workflow and return raw result (without DB persistence).
        
        Useful for testing or when you want to handle persistence yourself.
        
        Returns:
            Dict with 'generated_alphas', 'failures', 'trace_steps'
        """
        return await self._workflow.run(
            task=task,
            dataset_id=dataset_id,
            fields=fields,
            operators=operators,
            num_alphas=num_alphas
        )
    
    async def run_evolution_loop(
        self,
        task: MiningTask,
        dataset_id: str,
        fields: List[Dict],
        operators: List[Dict],
        max_iterations: int = 10,
        target_alphas: int = 4,
        num_alphas_per_round: int = 4
    ) -> Dict[str, Any]:
        """
        Run multi-round evolution loop for alpha mining.
        
        Implements RD-Agent/Alpha-GPT style evolutionary iteration:
        - Outer loop continues until goal reached OR max iterations
        - Each round generates, simulates, evaluates alphas
        - Results accumulate across rounds
        - Early termination when target_alphas achieved
        
        Args:
            task: Mining task instance
            dataset_id: Dataset to mine
            fields: Available data fields
            operators: Available operators
            max_iterations: Maximum number of mining rounds
            target_alphas: Target number of successful alphas (daily_goal)
            num_alphas_per_round: Alphas to generate per round
            
        Returns:
            Dict with iteration stats, total_alphas, all_results
        """
        logger.info(
            f"[MiningAgent] 🚀 Starting Evolution Loop | "
            f"task={task.id} dataset={dataset_id} "
            f"max_iter={max_iterations} target={target_alphas}"
        )
        
        iteration = 0
        total_success = 0
        all_alphas = []
        all_failures = []
        
        while iteration < max_iterations:
            iteration += 1
            
            logger.info(f"[MiningAgent] === Evolution Round {iteration}/{max_iterations} ===")
            
            try:
                # Run single mining iteration
                alphas = await self.run_mining_iteration(
                    task=task,
                    dataset_id=dataset_id,
                    fields=fields,
                    operators=operators,
                    num_alphas=num_alphas_per_round,
                    iteration=iteration
                )
                
                # Count successful alphas (PASS quality status)
                round_success = len([a for a in alphas if a.quality_status == "PASS"])
                total_success += round_success
                all_alphas.extend(alphas)
                
                logger.info(
                    f"[MiningAgent] Round {iteration} complete | "
                    f"round_success={round_success} total={total_success}/{target_alphas}"
                )
                
                # Check termination condition: goal reached
                if total_success >= target_alphas:
                    logger.info(
                        f"[MiningAgent] 🎯 Goal reached! "
                        f"{total_success}/{target_alphas} alphas found in {iteration} iterations"
                    )
                    break
                
                # Check if task should stop (paused/stopped externally)
                await self.db.refresh(task)
                if task.status in ["STOPPED", "PAUSED"]:
                    logger.info(f"[MiningAgent] Task {task.status}, stopping evolution loop")
                    break
                    
            except Exception as e:
                logger.error(f"[MiningAgent] Round {iteration} failed: {e}")
                # Continue to next iteration on failure (resilience)
                continue
            
            # --- INTELLIGENT STRATEGY: RD-Agent/Alpha-GPT Style Analysis ---
            # Query recent failures for comprehensive analysis
            from backend.models import AlphaFailure
            from datetime import datetime, timedelta
            
            failures_query = select(AlphaFailure).where(
                AlphaFailure.task_id == task.id,
                AlphaFailure.created_at >= datetime.utcnow() - timedelta(minutes=5),
                AlphaFailure.is_analyzed == False
            )
            res = await self.db.execute(failures_query)
            recent_failures = res.scalars().all()
            failures_dicts = [
                {
                    "expression": f.expression, 
                    "error_message": f.error_message,
                    "error_type": f.error_type
                } 
                for f in recent_failures
            ]
            
            # Compute comprehensive metrics using StrategyAgent
            round_metrics = self._strategy_agent.compute_round_metrics(alphas, failures_dicts)
            
            # Generate intelligent next-round strategy
            next_strategy = await self._strategy_agent.generate_strategy(
                iteration=iteration,
                max_iterations=max_iterations,
                alphas=alphas,
                failures=failures_dicts,
                dataset_id=dataset_id,
                region=task.region,
                cumulative_success=total_success,
                target_goal=target_alphas
            )
            
            logger.info(
                f"[MiningAgent] Strategy generated | "
                f"action={next_strategy.action_summary} temp={next_strategy.temperature}"
            )

            # Record Comprehensive ROUND_SUMMARY with rich metrics
            try:
                summary_tracer = TraceService(self.db, task.id, initial_step_order=99, iteration=iteration)
                await summary_tracer.persist_record(
                    summary_tracer.create_record(
                        step_type="ROUND_SUMMARY",
                        status="SUCCESS",
                        input_data={
                            "round": iteration,
                            "total_alphas": round_metrics.total_alphas,
                            "target_alphas": target_alphas,
                            "cumulative_success": total_success
                        },
                        output_data={
                            "mining_success": round_metrics.passed_alphas > 0,
                            "simulated_alphas": round_metrics.simulated_alphas, # Added metric
                            "succeeded_alphas": round_metrics.passed_alphas,
                            "failed_alphas": round_metrics.failed_alphas,
                            "success_rate": round(round_metrics.success_rate, 3),
                            
                            # Quality metrics (multi-dimensional)
                            "best_sharpe": round_metrics.best_sharpe,
                            "avg_sharpe": round_metrics.avg_sharpe,
                            "best_fitness": round_metrics.best_fitness,
                            "avg_fitness": round_metrics.avg_fitness,
                            "avg_turnover": round_metrics.avg_turnover,
                            "avg_returns": round_metrics.avg_returns,
                            
                            # Failure analysis
                            "error_breakdown": {
                                "syntax_errors": round_metrics.syntax_errors,
                                "simulation_errors": round_metrics.simulation_errors,
                                "quality_failures": round_metrics.quality_failures
                            },
                            "common_error_types": round_metrics.common_error_types,
                            "problematic_fields": round_metrics.problematic_fields,
                            
                            # Intelligent next-round strategy
                            "next_strategy": {
                                "temperature": next_strategy.temperature,
                                "exploration_weight": next_strategy.exploration_weight,
                                "action": next_strategy.action_summary,
                                "reasoning": next_strategy.reasoning,
                                "focus_hypotheses": next_strategy.focus_hypotheses[:3],
                                "avoid_patterns": next_strategy.avoid_patterns[:3],
                                "amplify_patterns": next_strategy.amplify_patterns[:3],
                                "preferred_fields": next_strategy.preferred_fields[:5],
                                "avoid_fields": next_strategy.avoid_fields[:3],
                                "optimization_suggestions": next_strategy.optimization_suggestions[:2]
                            }
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Failed to record round summary: {e}")
            
            # --- FEEDBACK LOOP: Learn from this round ---
            # Reuse failures_dicts from strategy analysis above
            from backend.agents.feedback_agent import FeedbackAgent
            feedback_agent = FeedbackAgent(self.db)
            
            try:
                await feedback_agent.learn_from_round(
                    successes=alphas,
                    failures=failures_dicts,
                    iteration=iteration,
                    dataset_id=dataset_id,
                    region=task.region
                )
                
                # Mark failures as analyzed
                for f in recent_failures:
                    f.is_analyzed = True
                await self.db.commit()
                
            except Exception as e:
                logger.warning(f"[MiningAgent] Feedback learning failed: {e}")
        
        # Final summary
        logger.info(
            f"[MiningAgent] ✅ Evolution Loop Complete | "
            f"iterations={iteration} total_alphas={total_success}"
        )
        
        return {
            "iterations_completed": iteration,
            "total_success": total_success,
            "target_reached": total_success >= target_alphas,
            "all_alphas": all_alphas,
            "all_failures": all_failures
        }
    
    @property
    def workflow(self) -> MiningWorkflow:
        """Access the underlying LangGraph workflow."""
        return self._workflow


# =============================================================================
# Factory Function
# =============================================================================

def create_mining_agent(
    db: AsyncSession,
    brain: BrainAdapter = None
) -> MiningAgent:
    """
    Factory function to create MiningAgent.
    
    Usage:
        agent = create_mining_agent(db)
        alphas = await agent.run_mining_iteration(task, ...)
    """
    return MiningAgent(db=db, brain_adapter=brain)
