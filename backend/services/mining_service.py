import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.services.base import BaseService
from backend.adapters.brain import brain_client
from backend.agents.agent_hub import agent_hub
from backend.models import MiningTask, MiningJob, Alpha, AlphaFailure, MiningStatus, JobStatus

logger = logging.getLogger("mining_service")

class MiningService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        
    async def create_task(self, name: str, region: str, universe: str, 
                          hypothesis: str, dataset_ids: List[str], 
                          operator_ids: List[str], iteration_limit: int = 1) -> MiningTask:
        """Creates a new mining task."""
        task = MiningTask(
            name=name,
            region=region,
            universe=universe,
            hypothesis=hypothesis,
            dataset_ids=dataset_ids,
            operator_ids=operator_ids,
            iteration_limit=iteration_limit,
            status=MiningStatus.PENDING
        )
        self.db.add(task)
        await self.commit()
        await self.db.refresh(task)
        return task

    async def start_task(self, task_id: int):
        """Starts a mining task asynchronously (placeholder for Celery)."""
        # In a real app, this would dispatch to Celery. 
        # Here we verify and update status.
        stmt = select(MiningTask).where(MiningTask.id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        task.status = MiningStatus.RUNNING
        await self.commit()
        
        # We will trigger the loop manually or via background task in main.py for this MVP
        return task

    async def run_mining_iteration(self, task_id: int):
        """Core logic for a single mining loop."""
        stmt = select(MiningTask).where(MiningTask.id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        try:
            # Create Job
            job = MiningJob(
                task_id=task.id,
                iteration_idx=task.current_iteration + 1,
                status=JobStatus.RUNNING,
                start_time=datetime.utcnow()
            )
            self.db.add(job)
            await self.commit()
            
            # 1. Prepare Context
            # Simplified: fetching names instead of full details for prompt context
            dataset_context = f"Datasets: {', '.join(task.dataset_ids)}"
            operator_context = f"Operators: {', '.join(task.operator_ids)}"
            
            # 2. Generate Alphas
            alphas_data = await agent_hub.generate_alphas(
                hypothesis=task.hypothesis,
                dataset_context=dataset_context,
                operator_context=operator_context,
                n=5 
            )
            
            if not alphas_data:
                logger.warning(f"No alphas generated for Task {task.id}")
                job.status = JobStatus.FAILED
                job.logs = "LLM generation returned empty"
                job.end_time = datetime.utcnow()
                await self.commit()
                return

            # 3. Simulate Alphas
            sim_configs = []
            for alpha_item in alphas_data:
                # Construct creating config
                config = {
                    "type": "REGULAR",
                    "region": task.region,
                    "universe": task.universe,
                    "delay": 1, 
                    "decay": 0,
                    "neutralization": "INDUSTRY", 
                    "truncation": 0.08,
                    "pasteurization": "ON",
                    "testPeriod": "P1Y", # 1 Year test
                    "regular": alpha_item.get("alpha_expression")
                }
                sim_configs.append(config)
            
            # Execute Simulation (Blocking call in adapter, but quick loop)
            # In production, this heavily needs async/await wrapper if adapter is sync
            sim_results = brain_client.simulate_batch(sim_configs)
            
            # 4. Process Results
            for i, res in enumerate(sim_results):
                expression = alphas_data[i].get("alpha_expression")
                rationale = alphas_data[i].get("economic_rationale")
                
                if res.get("status") == "SUCCESS":
                    details = res.get("detail", {})
                    metrics = {
                        "sharpe": details.get("sharpe", 0),
                        "fitness": details.get("fitness", 0),
                        "turnover": details.get("turnover", 0),
                        "returns": details.get("returns", 0)
                    }
                    
                    new_alpha = Alpha(
                        job_id=job.id,
                        expression=expression,
                        brain_alpha_id=res.get("alpha_id"),
                        metrics=metrics,
                        status="CANDIDATE" # Default to candidate
                    )
                    self.db.add(new_alpha)
                    
                else:
                    # Record Failure
                    failure = AlphaFailure(
                        job_id=job.id,
                        expression=expression,
                        error_type="SIMULATION_ERROR",
                        error_message=res.get("message", "Unknown"),
                        dataset_context=dataset_context,
                        operator_context=operator_context
                    )
                    self.db.add(failure)
            
            # Update Job & Task
            job.status = JobStatus.COMPLETED
            job.end_time = datetime.utcnow()
            
            task.current_iteration += 1
            if task.current_iteration >= task.iteration_limit:
                task.status = MiningStatus.COMPLETED
            
            await self.commit()
            
        except Exception as e:
            logger.error(f"Mining iteration failed: {e}")
            if job:
                job.status = JobStatus.FAILED
                job.logs = str(e)
                await self.commit()
