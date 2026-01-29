import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database import init_db, AsyncSessionLocal
from backend.services.mining_service import MiningService, MiningTask
from backend.agents.agent_hub import agent_hub
from backend.adapters.brain_adapter import get_brain_adapter

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_mining")

async def test_workflow():
    logger.info("Initializing DB...")
    await init_db()
    
    async with AsyncSessionLocal() as db:
        service = MiningService(db)
        
        # 1. Create Task
        logger.info("Creating Mining Task...")
        task = await service.create_task(
            name="Test Task 1",
            region="USA",
            universe="TOP3000",
            hypothesis="Volume increases precede price increases",
            dataset_ids=["dataset_volume_1"],
            operator_ids=["ts_mean", "ts_std"],
            iteration_limit=1
        )
        logger.info(f"Task Created: {task.id} - {task.status}")
        
        # 2. Start Task (Simulate endpoint call)
        logger.info("Starting Task...")
        await service.start_task(task.id)
        
        # 3. Run Iteration
        logger.info("Running Mining Iteration...")
        # Note: In real app this is background. We call directly here.
        await service.run_mining_iteration(task.id)
        
        # 4. Verification
        logger.info("Verifying Results...")
        # Re-fetch task to check updates
        await db.refresh(task)
        logger.info(f"Task Status after run: {task.status}")
        logger.info(f"Current Iteration: {task.current_iteration}")
        
        if task.current_iteration == 1:
            logger.info("SUCCESS: Iteration count incremented.")
        else:
            logger.error(f"FAILURE: Iteration count mismatch. Got {task.current_iteration}")

if __name__ == "__main__":
    try:
        # Check if environment variables are set (warn if not)
        if not os.getenv("BRAIN_EMAIL"):
            logger.warning("BRAIN_EMAIL not set. Simulation might fail if not mocked.")
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set. Generation will fail.")
            
        asyncio.run(test_workflow())
    except Exception as e:
        logger.error(f"Test Failed: {e}")
