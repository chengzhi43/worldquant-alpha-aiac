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
        
        logger.info("[MiningAgent] Initialized with LangGraph workflow")
    
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
            
            # --- ADAPTIVE STRATEGY: Adjust Parameters for Next Round ---
            # Calculate success rate for this round
            round_success = len([a for a in alphas if a.quality_status == "PASS"])
            success_rate = round_success / max(len(alphas), 1)
            
            # 1. Adjust Temperature (Exploration vs Exploitation)
            # If failed (0 success), increase temperature to explore more
            # If succeeded, decrease temperature to exploit (stabilize)
            # 1. Adjust Temperature (Exploration vs Exploitation)
            # If failed (0 success), increase temperature to explore more
            # If succeeded, decrease temperature to exploit (stabilize)
            current_temp = 0.7 # Default
            strategy_msg = "保持当前策略"
            
            if round_success == 0:
                new_temp = min(1.0, current_temp + 0.1 * (iteration % 3 + 1))
                strategy_msg = f"探索模式: 上轮全败，提升 Temperature {current_temp}->{new_temp} 以增加多样性"
                logger.info(f"[Strategy] Round failed. Increasing Temp: {current_temp} -> {new_temp} (Exploration)")
            else:
                new_temp = max(0.1, current_temp - 0.05 * round_success)
                strategy_msg = f"收敛模式: 上轮成功 {round_success} 个，降低 Temperature {current_temp}->{new_temp} 以稳定产出"
                logger.info(f"[Strategy] Round success. Decreasing Temp: {current_temp} -> {new_temp} (Exploitation)")
            
            # Calculate best stats
            best_sharpe = -999.0
            for a in alphas:
                if a.quality_status == "PASS" and a.metrics:
                    # Handle both obj and dict metrics
                    m = a.metrics
                    s = m.get("sharpe", -999.0) if isinstance(m, dict) else -999.0
                    if s > best_sharpe:
                        best_sharpe = s
            
            if best_sharpe == -999.0:
                best_sharpe = None

            # Record Strategy Trace (Ephemeral Service)
            # Use a high step_order (e.g. 99) to ensure it appears at the end
            try:
                summary_tracer = TraceService(self.db, task.id, initial_step_order=99, iteration=iteration)
                await summary_tracer.persist_record(
                    summary_tracer.create_record(
                        step_type="ROUND_SUMMARY",
                        status="SUCCESS",
                        input_data={
                            "round_success": round_success,
                            "total_alphas": len(alphas),
                            "target_alphas": target_alphas
                        },
                        output_data={
                            "mining_success": round_success > 0,
                            "total_alphas": len(alphas),
                            "succeeded_alphas": round_success,
                            "success_rate": success_rate,
                            "best_sharpe": best_sharpe,
                            "next_strategy": {
                                "temperature": new_temp,
                                "action": strategy_msg,
                                "exploration_weight": 0.5 + (0.1 * iteration) if round_success == 0 else 0.5 # Simple heuristic
                            }
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Failed to record round summary: {e}")
            
            # --- FEEDBACK LOOP: Learn from this round ---
            # Extract failures from the result dict (need to capture failures from run_mining_iteration or workflow)
            # Since run_mining_iteration only returns successes, we need failures too.
            # We'll use a hack here: Query failures from DB for this task created in last minute
            # Ideally, run_mining_iteration should return both, but we kept it back-compat.
            # Let's improve run_evolution_loop by using workflow.run_with_persistence directly to get full stats
            # OR we just query the DB for failures created in this round
            
            from backend.agents.feedback_agent import FeedbackAgent
            feedback_agent = FeedbackAgent(self.db)
            
            # Query recent failures for this task
            from backend.models import AlphaFailure
            from datetime import datetime, timedelta
            
            # Simple heuristic: failures created in last 5 minutes for this task
            # A more robust way would be to get trace steps from current round
            failures_query = select(AlphaFailure).where(
                AlphaFailure.task_id == task.id,
                AlphaFailure.created_at >= datetime.utcnow() - timedelta(minutes=5),
                AlphaFailure.is_analyzed == False
            )
            res = await self.db.execute(failures_query)
            recent_failures = res.scalars().all()
            
            # Convert to dict format for feedback agent
            failures_dicts = [
                {"expression": f.expression, "error_message": f.error_message} 
                for f in recent_failures
            ]
            
            try:
                await feedback_agent.learn_from_round(
                    successes=alphas,
                    failures=failures_dicts,
                    iteration=iteration,
                    dataset_id=dataset_id,
                    region=task.region
                )
                
                # Mark as analyzed
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
