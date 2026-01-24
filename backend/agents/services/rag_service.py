"""
RAG Service - Knowledge base retrieval for mining patterns
"""

from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.models import KnowledgeEntry, DatasetMetadata


class RAGResult:
    """RAG query result container."""
    
    def __init__(
        self,
        patterns: List[Dict] = None,
        pitfalls: List[Dict] = None,
        dataset_info: Optional[Dict] = None
    ):
        self.patterns = patterns or []
        self.pitfalls = pitfalls or []
        self.dataset_info = dataset_info
    
    def to_dict(self) -> Dict:
        return {
            "patterns": self.patterns,
            "pitfalls": self.pitfalls,
            "dataset_info": self.dataset_info
        }
    
    def get_few_shot_text(self) -> str:
        """Format patterns as few-shot examples for prompts."""
        if not self.patterns:
            return "暂无成功模式参考"
        
        return "\n".join([
            f"- {p['pattern']}: {p.get('description', '')}"
            for p in self.patterns
        ])
    
    def get_constraints_text(self) -> str:
        """Format pitfalls as negative constraints for prompts."""
        if not self.pitfalls:
            return "暂无特殊限制"
        
        return "\n".join([
            f"- 避免: {p['pattern']} (原因: {p.get('description', '')})"
            for p in self.pitfalls
        ])


class RAGService:
    """
    Knowledge base retrieval service.
    
    Features:
    - Success pattern retrieval
    - Failure pitfall retrieval  
    - Dataset metadata lookup
    - Relevance ranking
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def query(
        self,
        dataset_id: str = None,
        region: str = None,
        max_patterns: int = 5,
        max_pitfalls: int = 10
    ) -> RAGResult:
        """
        Query knowledge base for relevant patterns and pitfalls.
        
        Args:
            dataset_id: Optional dataset to filter by
            region: Optional region to filter by
            max_patterns: Maximum success patterns to return
            max_pitfalls: Maximum failure pitfalls to return
            
        Returns:
            RAGResult with patterns, pitfalls, and dataset info
        """
        logger.debug(
            f"[RAGService] Query | dataset={dataset_id} region={region}"
        )
        
        # Get success patterns
        patterns = await self._get_success_patterns(
            dataset_id=dataset_id,
            region=region,
            limit=max_patterns
        )
        
        # Get failure pitfalls
        pitfalls = await self._get_failure_pitfalls(
            dataset_id=dataset_id,
            region=region,
            limit=max_pitfalls
        )
        
        # Get dataset info
        dataset_info = None
        if dataset_id:
            dataset_info = await self._get_dataset_info(dataset_id)
        
        logger.info(
            f"[RAGService] Query complete | "
            f"patterns={len(patterns)} pitfalls={len(pitfalls)}"
        )
        
        return RAGResult(
            patterns=patterns,
            pitfalls=pitfalls,
            dataset_info=dataset_info
        )
    
    async def _get_success_patterns(
        self,
        dataset_id: str = None,
        region: str = None,
        limit: int = 5
    ) -> List[Dict]:
        """Get top success patterns by usage count."""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == 'SUCCESS_PATTERN',
            KnowledgeEntry.is_active == True
        ).order_by(KnowledgeEntry.usage_count.desc()).limit(limit)
        
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        patterns = []
        for entry in entries:
            # Filter by dataset/region if specified
            metadata = entry.meta_data or {}
            if dataset_id and metadata.get('dataset') and metadata['dataset'] != dataset_id:
                continue
            if region and metadata.get('region') and metadata['region'] != region:
                continue
            
            patterns.append({
                'pattern': entry.pattern,
                'description': entry.description,
                'usage_count': entry.usage_count,
                'metadata': metadata
            })
        
        return patterns[:limit]
    
    async def _get_failure_pitfalls(
        self,
        dataset_id: str = None,
        region: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get relevant failure pitfalls."""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == 'FAILURE_PITFALL',
            KnowledgeEntry.is_active == True
        ).order_by(KnowledgeEntry.created_at.desc()).limit(limit * 2)  # Get more for filtering
        
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        pitfalls = []
        for entry in entries:
            metadata = entry.meta_data or {}
            
            # Filter by region if specified
            if region and metadata.get('region') and metadata['region'] != region:
                continue
            
            pitfalls.append({
                'pattern': entry.pattern,
                'description': entry.description,
                'error_type': metadata.get('error_type'),
                'failure_rate': metadata.get('failure_rate')
            })
        
        return pitfalls[:limit]
    
    async def get_field_blacklist(self, region: str = None) -> List[str]:
        """Get list of blacklisted fields."""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == 'FIELD_BLACKLIST',
            KnowledgeEntry.is_active == True
        )
        
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        blacklist = []
        for entry in entries:
            metadata = entry.meta_data or {}
            if region and metadata.get('region') and metadata['region'] != region:
                continue
            
            field_name = metadata.get('field') or entry.pattern
            if field_name:
                blacklist.append(field_name)
        
        return blacklist
    
    async def _get_dataset_info(self, dataset_id: str) -> Optional[Dict]:
        """Get dataset metadata."""
        query = select(DatasetMetadata).where(
            DatasetMetadata.dataset_id == dataset_id
        )
        result = await self.db.execute(query)
        dataset = result.scalar_one_or_none()
        
        if not dataset:
            return None
        
        return {
            'dataset_id': dataset.dataset_id,
            'region': dataset.region,
            'category': dataset.category,
            'subcategory': dataset.subcategory,
            'description': dataset.description,
            'field_count': dataset.field_count,
            'mining_weight': dataset.mining_weight
        }
    
    async def increment_pattern_usage(self, pattern: str) -> bool:
        """Increment usage count for a pattern (called on successful use)."""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.pattern == pattern,
            KnowledgeEntry.is_active == True
        )
        result = await self.db.execute(query)
        entry = result.scalar_one_or_none()
        
        if entry:
            entry.usage_count += 1
            logger.debug(f"[RAGService] Incremented usage | pattern={pattern}")
            return True
        
        return False
