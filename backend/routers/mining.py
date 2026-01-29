from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.services.mining_service import MiningService, MiningTask, MiningStatus
from backend.tasks import run_mining_task

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
    # Use max_iterations as the effective limit if it's provided and iteration_limit is default
    # Or simply force iteration_limit to match max_iterations for consistency
    effective_limit = request.max_iterations
    
    task = await service.create_task(
        name=request.name,
        region=request.region,
        universe=request.universe,
        hypothesis=request.hypothesis,
        dataset_ids=request.dataset_ids,
        operator_ids=request.operator_ids,
        iteration_limit=effective_limit,  # Sync with max_iterations
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
    service: MiningService = Depends(get_mining_service)
):
    """Start a mining task (runs one iteration in background for now)."""
    # Verify task exists and update status
    try:
        await service.start_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Run the mining iteration in background
    # Note: In production, this should be a Celery task or similar.
    # We use FastAPI BackgroundTasks for MVP simplicity.
    # We need a new DB session for the background task because the dependency session closes.
    # However, BackgroundTasks with async dependency is tricky. 
    # For this MVP, we will rely on the service to handle its own session or 
    # we just run it here if it's fast, OR we define a wrapper.
    # BETTER APPROACH: Pass a standalone runner function that creates its own session.
    
    celery_result = run_mining_task.delay(task_id)

    return {"message": "Task started", "celery_task_id": celery_result.id}

# --- Background Runner Helper ---
# We need to import SessionLocal to create a new session
# from backend.database import AsyncSessionLocal

# async def run_mining_background(task_id: int):
#     async with AsyncSessionLocal() as db:
#         service = MiningService(db)
#         # Run iterations until limit or stopped
#         # For now, just run ONE iteration as a proof of concept loop
#         # Check task status to see if we should continue
#         await service.run_mining_iteration(task_id)
#         # Logic to loop would go here, checking DB status each time
