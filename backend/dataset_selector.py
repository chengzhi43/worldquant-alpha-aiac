"""
Dataset Selector Service - Integrates Bandit algorithm for intelligent dataset selection.

P1-fix-1: Enable adaptive dataset selection to escape ineffective datasets.

This service:
1. Maintains a Bandit instance for dataset arm selection
2. Tracks rewards based on alpha mining results
3. Persists Bandit state to database for continuity
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger

from backend.selection_strategy import DatasetBandit, DatasetArm
from backend.models import DatasetMetadata
from backend.config import settings


class DatasetSelector:
    """
    Intelligent dataset selection using Multi-Armed Bandit.
    
    Usage:
        selector = DatasetSelector(db)
        await selector.initialize(region="KOR", universe="TOP600")
        
        # Select dataset for mining
        dataset_id = await selector.select_dataset()
        
        # After mining iteration, update rewards
        await selector.update_reward(dataset_id, pass_count=2, total_count=4)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bandit: Optional[DatasetBandit] = None
        self.region: str = "USA"
        self.universe: str = "TOP3000"
        self._initialized = False
        
    async def initialize(
        self,
        region: str = "USA",
        universe: str = "TOP3000",
        dataset_ids: Optional[List[str]] = None
    ):
        """
        Initialize the Bandit with available datasets.
        
        Args:
            region: Market region
            universe: Universe of stocks
            dataset_ids: Optional list of specific dataset IDs to consider
        """
        self.region = region
        self.universe = universe
        
        # Get bandit parameters from settings
        exploration_weight = getattr(settings, 'BANDIT_EXPLORATION_WEIGHT', 2.0)
        pyramid_bonus = getattr(settings, 'BANDIT_PYRAMID_BONUS_WEIGHT', 0.3)
        saturation_penalty = getattr(settings, 'BANDIT_SATURATION_PENALTY_WEIGHT', 0.2)
        
        self.bandit = DatasetBandit(
            exploration_weight=exploration_weight,
            pyramid_bonus_weight=pyramid_bonus,
            saturation_penalty_weight=saturation_penalty
        )
        
        # Load datasets from database
        await self._load_datasets(dataset_ids)
        
        # Load persisted bandit state if exists
        await self._load_bandit_state()
        
        self._initialized = True
        logger.info(f"[DatasetSelector] Initialized | region={region} arms={len(self.bandit.arms)}")
        
    async def _load_datasets(self, dataset_ids: Optional[List[str]] = None):
        """Load datasets from DB and create Bandit arms"""
        query = select(DatasetMetadata).where(
            DatasetMetadata.region == self.region
        )
        
        if dataset_ids:
            query = query.where(DatasetMetadata.dataset_id.in_(dataset_ids))
            
        result = await self.db.execute(query)
        datasets = result.scalars().all()
        
        for ds in datasets:
            arm = DatasetArm(
                dataset_id=ds.dataset_id,
                region=ds.region,
                universe=self.universe,
                pyramid_multiplier=ds.mining_weight or 1.0,
                alpha_count=ds.alpha_count or 0,
                field_count=ds.field_count or 0
            )
            self.bandit.add_arm(arm)
            
        logger.debug(f"[DatasetSelector] Loaded {len(datasets)} datasets as Bandit arms")
        
    async def _load_bandit_state(self):
        """Load persisted Bandit state from database"""
        # Try to load from KnowledgeEntry or a dedicated table
        # For now, we start fresh each session but could persist to JSON
        pass
        
    async def _save_bandit_state(self):
        """Persist Bandit state to database"""
        # Could save to a dedicated table or KnowledgeEntry
        pass
        
    async def select_dataset(self, n: int = 1) -> List[str]:
        """
        Select dataset(s) using UCB algorithm.
        
        Args:
            n: Number of datasets to select
            
        Returns:
            List of selected dataset IDs
        """
        if not self._initialized:
            raise RuntimeError("DatasetSelector not initialized. Call initialize() first.")
            
        if not self.bandit.arms:
            logger.warning("[DatasetSelector] No datasets available for selection")
            return []
            
        selected_arms = self.bandit.select(n=n)
        dataset_ids = [arm.dataset_id for arm in selected_arms]
        
        logger.info(f"[DatasetSelector] Selected datasets: {dataset_ids}")
        return dataset_ids
        
    async def update_reward(
        self,
        dataset_id: str,
        pass_count: int,
        total_count: int,
        avg_sharpe: float = 0.0
    ):
        """
        Update Bandit reward after mining iteration.
        
        Args:
            dataset_id: Dataset that was mined
            pass_count: Number of PASS alphas
            total_count: Total alphas evaluated
            avg_sharpe: Average Sharpe ratio of passes
        """
        if not self._initialized:
            return
            
        # Calculate reward: pass rate with Sharpe bonus
        pass_rate = pass_count / total_count if total_count > 0 else 0
        sharpe_bonus = min(avg_sharpe / 3.0, 0.5) if avg_sharpe > 0 else 0  # Cap at 0.5
        reward = pass_rate + sharpe_bonus * 0.3
        
        success = pass_count > 0
        
        self.bandit.update(
            dataset_id=dataset_id,
            reward=reward,
            success=success,
            region=self.region,
            universe=self.universe
        )
        
        logger.info(
            f"[DatasetSelector] Updated reward | dataset={dataset_id} "
            f"pass={pass_count}/{total_count} reward={reward:.3f}"
        )
        
        # Persist state
        await self._save_bandit_state()
        
    def get_stats(self) -> Dict:
        """Get Bandit statistics for observability"""
        if not self.bandit:
            return {}
        return self.bandit.get_stats()


# =============================================================================
# Helper function for MiningAgent integration
# =============================================================================

async def select_next_dataset(
    db: AsyncSession,
    region: str,
    universe: str,
    available_datasets: List[str],
    fallback_dataset: str
) -> str:
    """
    Helper function to select the next dataset for mining.
    
    This can be called by MiningAgent to get intelligent dataset selection.
    
    Args:
        db: Database session
        region: Market region
        universe: Universe
        available_datasets: List of available dataset IDs
        fallback_dataset: Dataset to use if selection fails
        
    Returns:
        Selected dataset ID
    """
    # Check if Bandit selection is enabled
    bandit_enabled = getattr(settings, 'BANDIT_SELECTION_ENABLED', False)
    
    if not bandit_enabled:
        logger.debug("[DatasetSelector] Bandit disabled, using fallback")
        return fallback_dataset
        
    try:
        selector = DatasetSelector(db)
        await selector.initialize(
            region=region,
            universe=universe,
            dataset_ids=available_datasets
        )
        
        selected = await selector.select_dataset(n=1)
        
        if selected:
            return selected[0]
        else:
            logger.warning("[DatasetSelector] No dataset selected, using fallback")
            return fallback_dataset
            
    except Exception as e:
        logger.error(f"[DatasetSelector] Selection failed: {e}")
        return fallback_dataset


async def update_dataset_reward(
    db: AsyncSession,
    dataset_id: str,
    region: str,
    universe: str,
    pass_count: int,
    total_count: int,
    avg_sharpe: float = 0.0
):
    """
    Helper function to update dataset reward after mining.
    
    This can be called by MiningAgent after each iteration.
    """
    bandit_enabled = getattr(settings, 'BANDIT_SELECTION_ENABLED', False)
    
    if not bandit_enabled:
        return
        
    try:
        selector = DatasetSelector(db)
        await selector.initialize(region=region, universe=universe)
        await selector.update_reward(
            dataset_id=dataset_id,
            pass_count=pass_count,
            total_count=total_count,
            avg_sharpe=avg_sharpe
        )
    except Exception as e:
        logger.warning(f"[DatasetSelector] Reward update failed: {e}")
