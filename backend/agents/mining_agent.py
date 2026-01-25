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
        operators: List[str],
        num_alphas: int = 3
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
            
        Returns:
            List of successfully generated Alpha models
        """
        logger.info(
            f"[MiningAgent] Starting iteration | "
            f"task={task.id} dataset={dataset_id} target={num_alphas}"
        )
        
        # Initialize TraceService for Real-Time Tracing
        trace_service = TraceService(self.db, task.id)
        
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
        operators: List[str],
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
