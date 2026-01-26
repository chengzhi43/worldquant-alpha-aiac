from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.analysis_service import AnalysisService

router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
    responses={404: {"description": "Not found"}},
)

def get_analysis_service(db: AsyncSession = Depends(get_db)):
    return AnalysisService(db)

@router.get("/dashboard/stats")
async def get_dashboard_stats(service: AnalysisService = Depends(get_analysis_service)):
    return await service.get_dashboard_stats()

@router.get("/alphas/recent")
async def get_recent_alphas(limit: int = 10, service: AnalysisService = Depends(get_analysis_service)):
    alphas = await service.get_recent_alphas(limit)
    return alphas

@router.get("/alphas/{alpha_id}")
async def get_alpha_details(alpha_id: int, service: AnalysisService = Depends(get_analysis_service)):
    alpha = await service.get_alpha_details(alpha_id)
    if not alpha:
        return {"error": "Alpha not found"}
    return alpha
