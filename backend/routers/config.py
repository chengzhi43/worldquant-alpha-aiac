"""
Config Router - System configuration management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import SystemConfig, OperatorPreference

router = APIRouter(
    prefix="/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ThresholdsConfig(BaseModel):
    sharpe_min: float = 1.5
    turnover_max: float = 0.7
    fitness_min: float = 0.6
    returns_min: float = 0.0
    max_dd_max: float = 0.3

class DiversityConfig(BaseModel):
    max_correlation: float = 0.7

class FullConfig(BaseModel):
    quality_thresholds: Optional[ThresholdsConfig] = None
    diversity_thresholds: Optional[DiversityConfig] = None
    daily_budget: Optional[dict] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("")
async def get_all_config(db: AsyncSession = Depends(get_db)):
    """Get all system configuration."""
    query = select(SystemConfig)
    result = await db.execute(query)
    configs = result.scalars().all()
    
    return {c.key: c.value for c in configs}


@router.get("/{key}")
async def get_config(key: str, db: AsyncSession = Depends(get_db)):
    """Get a specific configuration value."""
    query = select(SystemConfig).where(SystemConfig.key == key)
    result = await db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
    
    return {key: config.value}


@router.put("/thresholds")
async def update_thresholds(
    thresholds: ThresholdsConfig,
    db: AsyncSession = Depends(get_db)
):
    """Update quality thresholds."""
    await db.execute(
        update(SystemConfig)
        .where(SystemConfig.key == "quality_thresholds")
        .values(value=thresholds.model_dump())
    )
    await db.commit()
    
    return {"message": "Thresholds updated", "thresholds": thresholds.model_dump()}


@router.put("/diversity")
async def update_diversity(
    diversity: DiversityConfig,
    db: AsyncSession = Depends(get_db)
):
    """Update diversity thresholds."""
    await db.execute(
        update(SystemConfig)
        .where(SystemConfig.key == "diversity_thresholds")
        .values(value=diversity.model_dump())
    )
    await db.commit()
    
    return {"message": "Diversity config updated", "diversity": diversity.model_dump()}


@router.get("/operators")
async def get_operator_prefs(db: AsyncSession = Depends(get_db)):
    """Get all operator preferences."""
    query = select(OperatorPreference).order_by(OperatorPreference.usage_count.desc())
    result = await db.execute(query)
    operators = result.scalars().all()
    
    return [
        {
            "operator_name": op.operator_name,
            "status": op.status,
            "usage_count": op.usage_count,
            "success_count": op.success_count,
            "failure_rate": op.failure_rate
        }
        for op in operators
    ]


@router.put("/operators/{operator_name}")
async def update_operator_pref(
    operator_name: str,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    """Update operator status (ACTIVE, BANNED, DEPRECATED)."""
    if status not in ["ACTIVE", "BANNED", "DEPRECATED"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    await db.execute(
        update(OperatorPreference)
        .where(OperatorPreference.operator_name == operator_name)
        .values(status=status)
    )
    await db.commit()
    
    return {"message": f"Operator {operator_name} set to {status}"}
