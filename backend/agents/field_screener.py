"""
Field Screener Module

Implements field screening to identify high-potential fields before alpha generation.
This significantly improves generation efficiency by focusing on informative operands.

Design Principles:
1. Template-Based Testing: Use simple templates to quickly assess field quality
2. Budget-Aware: Limit simulation calls per screening batch
3. Score-Based Ranking: Use composite scoring, not just Sharpe
4. Caching: Cache results to avoid redundant screening

Reference: 优化.md Section 3.2 (Field Screening)
"""

from __future__ import annotations
import asyncio
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Templates for field screening (simple, interpretable)
SCREENING_TEMPLATES = [
    # Momentum templates
    "rank({field})",
    "rank(ts_delta({field}, 5))",
    "rank(ts_delta({field}, 20))",
    "-rank(ts_delta({field}, 5))",  # Reversal
    
    # Volatility-adjusted
    "rank(ts_zscore({field}, 20))",
    
    # Time-series dynamics
    "rank(ts_mean({field}, 5) - ts_mean({field}, 20))",
]

# Default window options for variation
DEFAULT_WINDOWS = [5, 20, 60]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FieldScore:
    """Screening score for a single field."""
    field_id: str
    field_name: str
    category: str = ""
    best_score: float = -999.0
    best_template: str = ""
    best_sharpe: float = 0.0
    avg_score: float = 0.0
    templates_tested: int = 0
    simulations_succeeded: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "field_id": self.field_id,
            "field_name": self.field_name,
            "category": self.category,
            "best_score": round(self.best_score, 4),
            "best_template": self.best_template,
            "best_sharpe": round(self.best_sharpe, 4),
            "avg_score": round(self.avg_score, 4),
            "templates_tested": self.templates_tested,
            "simulations_succeeded": self.simulations_succeeded,
        }


@dataclass
class ScreeningResult:
    """Complete screening result for a dataset."""
    dataset_id: str
    region: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_fields: int = 0
    fields_tested: int = 0
    simulations_run: int = 0
    top_fields: List[FieldScore] = field(default_factory=list)
    problematic_fields: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "dataset_id": self.dataset_id,
            "region": self.region,
            "timestamp": self.timestamp.isoformat(),
            "total_fields": self.total_fields,
            "fields_tested": self.fields_tested,
            "simulations_run": self.simulations_run,
            "top_fields": [f.to_dict() for f in self.top_fields],
            "problematic_fields": self.problematic_fields[:10],
        }
    
    def get_top_k_field_ids(self, k: int = 20) -> List[str]:
        """Get top-k field IDs by score."""
        return [f.field_id for f in self.top_fields[:k]]


# =============================================================================
# FIELD SCREENER CLASS
# =============================================================================

class FieldScreener:
    """
    Screens fields to identify high-potential operands for alpha generation.
    
    Usage:
        screener = FieldScreener(brain_adapter)
        result = await screener.screen_fields(fields, dataset_id, region)
        top_fields = result.get_top_k_field_ids(20)
    """
    
    def __init__(
        self,
        brain_adapter: Any,
        templates: Optional[List[str]] = None,
        cache_ttl_hours: int = 24
    ):
        """
        Initialize FieldScreener.
        
        Args:
            brain_adapter: Brain adapter for simulations
            templates: Custom screening templates (uses defaults if None)
            cache_ttl_hours: Cache validity period in hours
        """
        self.brain = brain_adapter
        self.templates = templates or SCREENING_TEMPLATES
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        
        # In-memory cache (could be replaced with Redis)
        self._cache: Dict[str, ScreeningResult] = {}
    
    def _get_cache_key(self, dataset_id: str, region: str) -> str:
        """Generate cache key for a dataset/region combination."""
        return f"{dataset_id}:{region}"
    
    def _get_cached_result(self, dataset_id: str, region: str) -> Optional[ScreeningResult]:
        """Get cached result if valid."""
        key = self._get_cache_key(dataset_id, region)
        if key in self._cache:
            result = self._cache[key]
            if datetime.utcnow() - result.timestamp < self.cache_ttl:
                logger.info(f"[FieldScreener] Using cached result for {dataset_id}")
                return result
        return None
    
    def _cache_result(self, result: ScreeningResult):
        """Cache screening result."""
        key = self._get_cache_key(result.dataset_id, result.region)
        self._cache[key] = result
    
    async def screen_fields(
        self,
        fields: List[Dict],
        dataset_id: str,
        region: str = "USA",
        universe: str = "TOP3000",
        max_fields: int = 50,
        templates_per_field: int = 4,
        top_k: int = 20,
        use_cache: bool = True
    ) -> ScreeningResult:
        """
        Screen fields to identify high-potential operands.
        
        Args:
            fields: List of field dictionaries
            dataset_id: Dataset ID
            region: Market region
            universe: Stock universe
            max_fields: Maximum fields to screen (budget control)
            templates_per_field: Templates to test per field
            top_k: Number of top fields to return
            use_cache: Whether to use cached results
        
        Returns:
            ScreeningResult with ranked fields
        """
        # Check cache
        if use_cache:
            cached = self._get_cached_result(dataset_id, region)
            if cached:
                return cached
        
        logger.info(
            f"[FieldScreener] Starting screening | "
            f"dataset={dataset_id} fields={len(fields)} max={max_fields}"
        )
        
        result = ScreeningResult(
            dataset_id=dataset_id,
            region=region,
            total_fields=len(fields)
        )
        
        # Select templates to use
        templates_to_use = self.templates[:templates_per_field]
        
        # Limit fields to screen
        fields_to_screen = fields[:max_fields]
        result.fields_tested = len(fields_to_screen)
        
        # Screen each field
        field_scores: List[FieldScore] = []
        problematic: List[str] = []
        
        for f in fields_to_screen:
            field_id = f.get("id", f.get("name", ""))
            if not field_id:
                continue
            
            score = await self._screen_single_field(
                field_id=field_id,
                field_name=f.get("name", field_id),
                category=f.get("category", ""),
                templates=templates_to_use,
                region=region,
                universe=universe
            )
            
            result.simulations_run += score.templates_tested
            
            if score.best_score > -900:  # Valid score
                field_scores.append(score)
            else:
                problematic.append(field_id)
        
        # Sort by best score and take top-k
        field_scores.sort(key=lambda x: x.best_score, reverse=True)
        result.top_fields = field_scores[:top_k]
        result.problematic_fields = problematic
        
        # Cache result
        self._cache_result(result)
        
        logger.info(
            f"[FieldScreener] Complete | "
            f"top_score={result.top_fields[0].best_score if result.top_fields else 'N/A'} "
            f"simulations={result.simulations_run}"
        )
        
        return result
    
    async def _screen_single_field(
        self,
        field_id: str,
        field_name: str,
        category: str,
        templates: List[str],
        region: str,
        universe: str
    ) -> FieldScore:
        """Screen a single field using templates."""
        from alpha_scoring import calculate_alpha_score
        
        score = FieldScore(
            field_id=field_id,
            field_name=field_name,
            category=category
        )
        
        scores = []
        
        for template in templates:
            try:
                # Build expression from template
                expression = template.format(field=field_id)
                
                # Run simulation
                sim_result = await self.brain.simulate_alpha(
                    expression=expression,
                    region=region,
                    universe=universe,
                    delay=1,
                    decay=4,
                    neutralization="SUBINDUSTRY",
                    truncation=0.08
                )
                
                score.templates_tested += 1
                
                if sim_result.get("success"):
                    score.simulations_succeeded += 1
                    
                    # Calculate composite score
                    alpha_score = calculate_alpha_score(sim_result)
                    scores.append(alpha_score)
                    
                    # Track best
                    if alpha_score > score.best_score:
                        score.best_score = alpha_score
                        score.best_template = template
                        
                        # Extract Sharpe from result
                        metrics = sim_result.get("metrics", {})
                        score.best_sharpe = metrics.get("sharpe", 0)
                
            except Exception as e:
                logger.debug(f"Template {template} failed for {field_id}: {e}")
                continue
        
        # Calculate average
        if scores:
            score.avg_score = sum(scores) / len(scores)
        
        return score
    
    async def quick_screen(
        self,
        fields: List[Dict],
        dataset_id: str,
        region: str = "USA",
        top_k: int = 10
    ) -> List[str]:
        """
        Quick screening with minimal simulations.
        
        Uses only 2 templates per field, useful for rapid iteration.
        
        Returns:
            List of top field IDs
        """
        result = await self.screen_fields(
            fields=fields,
            dataset_id=dataset_id,
            region=region,
            max_fields=30,
            templates_per_field=2,
            top_k=top_k
        )
        return result.get_top_k_field_ids(top_k)
    
    def invalidate_cache(self, dataset_id: str = None, region: str = None):
        """Invalidate cached screening results."""
        if dataset_id and region:
            key = self._get_cache_key(dataset_id, region)
            if key in self._cache:
                del self._cache[key]
        elif dataset_id:
            # Invalidate all regions for dataset
            to_delete = [k for k in self._cache if k.startswith(f"{dataset_id}:")]
            for k in to_delete:
                del self._cache[k]
        else:
            # Clear all
            self._cache.clear()


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_field_screener(
    brain_adapter: Any,
    custom_templates: Optional[List[str]] = None
) -> FieldScreener:
    """
    Factory function to create FieldScreener.
    
    Usage:
        screener = create_field_screener(brain)
        result = await screener.screen_fields(fields, "model110", "USA")
    """
    return FieldScreener(
        brain_adapter=brain_adapter,
        templates=custom_templates
    )


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

async def get_screened_fields(
    brain_adapter: Any,
    fields: List[Dict],
    dataset_id: str,
    region: str = "USA",
    top_k: int = 20,
    enabled: bool = True
) -> List[Dict]:
    """
    Helper function for integration with mining workflow.
    
    If screening is enabled, returns top-k fields by score.
    Otherwise, returns original fields unchanged.
    
    Args:
        brain_adapter: Brain adapter for simulations
        fields: Original field list
        dataset_id: Dataset ID
        region: Market region
        top_k: Number of top fields to return
        enabled: Whether screening is enabled
    
    Returns:
        Filtered/reordered field list
    """
    if not enabled:
        return fields
    
    screener = FieldScreener(brain_adapter)
    result = await screener.screen_fields(
        fields=fields,
        dataset_id=dataset_id,
        region=region,
        top_k=top_k
    )
    
    # Get top field IDs
    top_ids = set(result.get_top_k_field_ids(top_k))
    
    # Reorder: top fields first, then others
    top_fields = [f for f in fields if f.get("id", f.get("name")) in top_ids]
    other_fields = [f for f in fields if f.get("id", f.get("name")) not in top_ids]
    
    return top_fields + other_fields[:10]  # Limit total returned
