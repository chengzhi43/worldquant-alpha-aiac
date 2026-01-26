from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.services.mining_service import MiningService, MiningTask, MiningStatus

router = APIRouter(
    prefix="/mining",
    tags=["mining"],
    responses={404: {"description": "Not found"}},
)

# --- Pydantic Models for Request/Response ---
class TaskCreateRequest(BaseModel):
    name: str
    region: str = "USA"
    universe: str = "TOP3000"
    hypothesis: str
    dataset_ids: List[str]
    operator_ids: List[str] = []
    iteration_limit: int = 1 # Legacy compatibility
    max_iterations: int = 10 # New field for evolution loop

class TaskResponse(BaseModel):
    id: int
    name: str
    status: str
    current_iteration: int
    iteration_limit: int
    created_at: str 
    
    class Config:
        from_attributes = True

# --- Dependency ---
def get_mining_service(db: AsyncSession = Depends(get_db)):
    return MiningService(db)

# --- Endpoints ---

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest, 
    service: MiningService = Depends(get_mining_service)
):
    """Create a new mining task."""
    task = await service.create_task(
        name=request.name,
        region=request.region,
        universe=request.universe,
        hypothesis=request.hypothesis,
        dataset_ids=request.dataset_ids,
        operator_ids=request.operator_ids,
        iteration_limit=request.iteration_limit,
        max_iterations=request.max_iterations
    )
    # Pydantic conversion handles the rest
    return TaskResponse(
        id=task.id,
        name=task.name,
        status=task.status.value,
        current_iteration=task.current_iteration,
        iteration_limit=task.iteration_limit,
        created_at=task.created_at.isoformat()
    )

@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: int, 
    background_tasks: BackgroundTasks,
    service: MiningService = Depends(get_mining_service)
):
    """Start a mining task (runs one iteration in background for now)."""
    # Verify task exists and update status
    await service.start_task(task_id)
    
    # Run the mining iteration in background
    # Note: In production, this should be a Celery task or similar.
    # We use FastAPI BackgroundTasks for MVP simplicity.
    # We need a new DB session for the background task because the dependency session closes.
    # However, BackgroundTasks with async dependency is tricky. 
    # For this MVP, we will rely on the service to handle its own session or 
    # we just run it here if it's fast, OR we define a wrapper.
    # BETTER APPROACH: Pass a standalone runner function that creates its own session.
    
    background_tasks.add_task(run_mining_background, task_id)
    
    return {"message": "Task started"}

# --- Background Runner Helper ---
# We need to import SessionLocal to create a new session
from backend.database import AsyncSessionLocal

async def run_mining_background(task_id: int):
    async with AsyncSessionLocal() as db:
        service = MiningService(db)
        # Run iterations until limit or stopped
        # For now, just run ONE iteration as a proof of concept loop
        # Check task status to see if we should continue
        await service.run_mining_iteration(task_id)
        # Logic to loop would go here, checking DB status each time
