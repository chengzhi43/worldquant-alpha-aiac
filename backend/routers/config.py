"""
Config Router - System configuration management

Includes:
- Quality thresholds
- Operator preferences
- Credentials management (Brain, LLM API)
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.database import get_db
from backend.models import SystemConfig, OperatorPreference
from backend.services.credentials_service import (
    CredentialsService, 
    CredentialKey,
    get_credentials_service
)

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


class BrainCredentialsRequest(BaseModel):
    """Request model for Brain platform credentials."""
    email: str = Field(..., description="Brain platform email")
    password: str = Field(..., description="Brain platform password")


class LLMCredentialsRequest(BaseModel):
    """Request model for LLM API credentials."""
    api_key: str = Field(..., description="API key (e.g., OpenAI, DeepSeek)")
    base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="API base URL"
    )
    model: str = Field(
        default="deepseek-chat",
        description="Model name"
    )


class CredentialStatusResponse(BaseModel):
    """Response model for credential status."""
    key: str
    masked: str
    is_set: bool
    source: Optional[str] = None
    updated_at: Optional[str] = None


# =============================================================================
# CREDENTIALS MANAGEMENT (Must be before /{key} route)
# =============================================================================

@router.get("/credentials")
async def get_credentials_status(db: AsyncSession = Depends(get_db)):
    """
    Get status of all configured credentials (masked values).
    
    Returns configuration status without exposing actual values.
    """
    service = get_credentials_service(db)
    credentials = await service.get_all_credentials_masked()
    
    return {
        "credentials": credentials,
        "message": "Use POST endpoints to update credentials"
    }


@router.post("/credentials/brain")
async def set_brain_credentials(
    credentials: BrainCredentialsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Set WorldQuant Brain platform credentials.
    
    Credentials are encrypted before storage.
    """
    from backend.adapters.brain_adapter import BrainAdapter
    
    service = get_credentials_service(db)
    
    try:
        await service.set_credential(
            CredentialKey.BRAIN_EMAIL,
            credentials.email,
            description="WorldQuant Brain platform email"
        )
        await service.set_credential(
            CredentialKey.BRAIN_PASSWORD,
            credentials.password,
            description="WorldQuant Brain platform password"
        )
        
        # Invalidate cached credentials in BrainAdapter
        BrainAdapter.invalidate_credentials_cache()
        CredentialsService.invalidate_cache()
        
        return {
            "success": True,
            "message": "Brain credentials saved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save credentials: {str(e)}"
        )


@router.post("/credentials/llm")
async def set_llm_credentials(
    credentials: LLMCredentialsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Set LLM API credentials (OpenAI, DeepSeek, etc.).
    
    Credentials are encrypted before storage.
    """
    service = get_credentials_service(db)
    
    try:
        await service.set_credential(
            CredentialKey.OPENAI_API_KEY,
            credentials.api_key,
            description="LLM API key"
        )
        await service.set_credential(
            CredentialKey.OPENAI_BASE_URL,
            credentials.base_url,
            description="LLM API base URL"
        )
        await service.set_credential(
            CredentialKey.OPENAI_MODEL,
            credentials.model,
            description="LLM model name"
        )
        
        # Invalidate credential caches
        CredentialsService.invalidate_cache()
        
        return {
            "success": True,
            "message": "LLM credentials saved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save credentials: {str(e)}"
        )


@router.post("/credentials/brain/test")
async def test_brain_credentials(db: AsyncSession = Depends(get_db)):
    """
    Test Brain platform credentials by attempting authentication.
    
    Does not return the actual credentials, only the test result.
    """
    service = get_credentials_service(db)
    result = await service.test_brain_credentials()
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Authentication failed")
        )
    
    return result


@router.delete("/credentials/{key}")
async def delete_credential(
    key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific credential.
    
    Valid keys: brain_email, brain_password, openai_api_key, openai_base_url, openai_model
    """
    valid_keys = [
        CredentialKey.BRAIN_EMAIL,
        CredentialKey.BRAIN_PASSWORD,
        CredentialKey.OPENAI_API_KEY,
        CredentialKey.OPENAI_BASE_URL,
        CredentialKey.OPENAI_MODEL,
    ]
    
    if key not in valid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid credential key. Valid keys: {valid_keys}"
        )
    
    service = get_credentials_service(db)
    deleted = await service.delete_credential(key)
    
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Credential '{key}' not found"
        )
    
    return {"success": True, "message": f"Credential '{key}' deleted"}


# =============================================================================
# THRESHOLDS & DIVERSITY
# =============================================================================

@router.get("/thresholds")
async def get_thresholds(db: AsyncSession = Depends(get_db)):
    """Get quality thresholds configuration."""
    query = select(SystemConfig).where(SystemConfig.config_key == "quality_thresholds")
    result = await db.execute(query)
    config = result.scalar_one_or_none()
    
    if config and config.config_value:
        try:
            return json.loads(config.config_value)
        except:
            return ThresholdsConfig().model_dump()
    
    return ThresholdsConfig().model_dump()


@router.put("/thresholds")
async def update_thresholds(
    thresholds: ThresholdsConfig,
    db: AsyncSession = Depends(get_db)
):
    """Update quality thresholds."""
    # Check if exists
    query = select(SystemConfig).where(SystemConfig.config_key == "quality_thresholds")
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.config_value = json.dumps(thresholds.model_dump())
    else:
        new_config = SystemConfig(
            config_key="quality_thresholds",
            config_value=json.dumps(thresholds.model_dump()),
            config_type="json",
            description="Alpha quality thresholds"
        )
        db.add(new_config)
    
    await db.commit()
    
    return {"message": "Thresholds updated", "thresholds": thresholds.model_dump()}


@router.put("/diversity")
async def update_diversity(
    diversity: DiversityConfig,
    db: AsyncSession = Depends(get_db)
):
    """Update diversity thresholds."""
    # Check if exists
    query = select(SystemConfig).where(SystemConfig.config_key == "diversity_thresholds")
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.config_value = json.dumps(diversity.model_dump())
    else:
        new_config = SystemConfig(
            config_key="diversity_thresholds",
            config_value=json.dumps(diversity.model_dump()),
            config_type="json",
            description="Alpha diversity thresholds"
        )
        db.add(new_config)
    
    await db.commit()
    
    return {"message": "Diversity config updated", "diversity": diversity.model_dump()}


# =============================================================================
# OPERATORS
# =============================================================================

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


# =============================================================================
# GENERAL CONFIG (Must be last due to {key} path param)
# =============================================================================

@router.get("")
async def get_all_config(db: AsyncSession = Depends(get_db)):
    """Get all system configuration (excluding credentials)."""
    query = select(SystemConfig).where(
        ~SystemConfig.config_key.like("credential:%")
    )
    result = await db.execute(query)
    configs = result.scalars().all()
    
    return {c.config_key: c.config_value for c in configs}
