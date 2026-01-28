"""
RAG Service - Knowledge base retrieval for mining patterns
"""

from typing import Dict, List, Optional
from datetime import datetime
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
        """Get top success patterns by usage count, prioritizing dataset-specific ones."""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == 'SUCCESS_PATTERN',
            KnowledgeEntry.is_active == True
        ).order_by(KnowledgeEntry.usage_count.desc()).limit(limit * 3)  # Get more for filtering
        
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        # Separate into dataset-specific and generic patterns
        dataset_specific = []
        generic_patterns = []
        
        for entry in entries:
            metadata = entry.meta_data or {}
            pattern_dataset = metadata.get('dataset')
            pattern_region = metadata.get('region')
            
            # Skip if region doesn't match (when specified)
            if region and pattern_region and pattern_region != region:
                continue
            
            pattern_info = {
                'pattern': entry.pattern,
                'description': entry.description,
                'usage_count': entry.usage_count,
                'metadata': metadata
            }
            
            # Categorize by dataset relevance
            if dataset_id and pattern_dataset == dataset_id:
                dataset_specific.append(pattern_info)
            elif not pattern_dataset:
                # Only include generic patterns if they're truly generic (no dataset specified)
                # Don't include patterns from other datasets
                generic_patterns.append(pattern_info)
        
        # Prioritize dataset-specific patterns, fill with generic if needed
        patterns = dataset_specific[:limit]
        if len(patterns) < limit:
            patterns.extend(generic_patterns[:limit - len(patterns)])
        
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
        ).limit(1)
        result = await self.db.execute(query)
        dataset = result.scalars().first()
        
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
    
    # =========================================================================
    # P0-fix-1: Knowledge Feedback Loop - Write patterns back to KB
    # =========================================================================
    
    async def record_failure_pattern(
        self,
        expression: str,
        error_type: str,
        metrics: Dict = None,
        region: str = None,
        dataset_id: str = None
    ) -> bool:
        """
        Record a failure pattern to the knowledge base.
        
        This is the KEY feedback loop that enables learning from failures.
        Called after evaluation identifies a failed alpha.
        """
        from backend.knowledge_extraction import expression_to_skeleton, extract_operator_chain
        
        try:
            # Extract pattern skeleton (structural, not specific)
            skeleton = expression_to_skeleton(expression)
            op_chain = extract_operator_chain(expression)
            
            # Check if similar pattern already exists
            existing = await self._find_similar_pitfall(skeleton, region)
            
            if existing:
                # Update existing pattern's failure count
                existing.meta_data = existing.meta_data or {}
                existing.meta_data['failure_count'] = existing.meta_data.get('failure_count', 0) + 1
                existing.meta_data['last_failure'] = datetime.now().isoformat()
                if metrics:
                    existing.meta_data['avg_sharpe'] = metrics.get('sharpe', 0)
                logger.debug(f"[RAGService] Updated existing pitfall | skeleton={skeleton[:50]}")
            else:
                # Create new pitfall entry
                description = self._generate_pitfall_description(error_type, metrics, op_chain)
                
                new_entry = KnowledgeEntry(
                    pattern=skeleton,
                    description=description,
                    entry_type='FAILURE_PITFALL',
                    is_active=True,
                    usage_count=0,
                    meta_data={
                        'region': region,
                        'dataset': dataset_id,
                        'error_type': error_type,
                        'operator_chain': op_chain[:5] if op_chain else [],
                        'example_expression': expression[:200],
                        'failure_count': 1,
                        'sharpe': metrics.get('sharpe', 0) if metrics else 0,
                        'fitness': metrics.get('fitness', 0) if metrics else 0,
                        'created_at': datetime.now().isoformat()
                    }
                )
                self.db.add(new_entry)
                logger.info(f"[RAGService] Created new pitfall | skeleton={skeleton[:50]} error={error_type}")
            
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"[RAGService] Failed to record pitfall | error={e}")
            await self.db.rollback()
            return False
    
    async def record_success_pattern(
        self,
        expression: str,
        metrics: Dict,
        region: str = None,
        dataset_id: str = None,
        alpha_id: str = None
    ) -> bool:
        """
        Record a success pattern to the knowledge base.
        
        Called when an alpha passes all quality thresholds.
        """
        from backend.knowledge_extraction import expression_to_skeleton, extract_operator_chain
        
        try:
            skeleton = expression_to_skeleton(expression)
            op_chain = extract_operator_chain(expression)
            
            # Check if similar pattern exists
            existing = await self._find_similar_success(skeleton, region)
            
            if existing:
                # Update existing pattern
                existing.usage_count += 1
                existing.meta_data = existing.meta_data or {}
                existing.meta_data['success_count'] = existing.meta_data.get('success_count', 0) + 1
                existing.meta_data['last_success'] = datetime.now().isoformat()
                # Update running average metrics
                n = existing.meta_data.get('success_count', 1)
                old_sharpe = existing.meta_data.get('avg_sharpe', 0)
                existing.meta_data['avg_sharpe'] = (old_sharpe * (n-1) + metrics.get('sharpe', 0)) / n
                logger.info(f"[RAGService] Updated success pattern | skeleton={skeleton[:50]}")
            else:
                # Create new success pattern
                description = f"Sharpe: {metrics.get('sharpe', 0):.2f}, Fitness: {metrics.get('fitness', 0):.2f}"
                
                new_entry = KnowledgeEntry(
                    pattern=skeleton,
                    description=description,
                    entry_type='SUCCESS_PATTERN',
                    is_active=True,
                    usage_count=1,
                    meta_data={
                        'region': region,
                        'dataset': dataset_id,
                        'operator_chain': op_chain[:5] if op_chain else [],
                        'example_expression': expression[:200],
                        'alpha_id': alpha_id,
                        'success_count': 1,
                        'avg_sharpe': metrics.get('sharpe', 0),
                        'avg_fitness': metrics.get('fitness', 0),
                        'created_at': datetime.now().isoformat()
                    }
                )
                self.db.add(new_entry)
                logger.info(f"[RAGService] Created new success pattern | skeleton={skeleton[:50]}")
            
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"[RAGService] Failed to record success | error={e}")
            await self.db.rollback()
            return False
    
    async def _find_similar_pitfall(self, skeleton: str, region: str = None) -> Optional[KnowledgeEntry]:
        """Find existing pitfall with similar skeleton"""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == 'FAILURE_PITFALL',
            KnowledgeEntry.pattern == skeleton,
            KnowledgeEntry.is_active == True
        )
        if region:
            # Also match patterns without region (global)
            pass  # We'll match exact skeleton first
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _find_similar_success(self, skeleton: str, region: str = None) -> Optional[KnowledgeEntry]:
        """Find existing success pattern with similar skeleton"""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == 'SUCCESS_PATTERN',
            KnowledgeEntry.pattern == skeleton,
            KnowledgeEntry.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    def _generate_pitfall_description(self, error_type: str, metrics: Dict, op_chain: List) -> str:
        """Generate human-readable pitfall description"""
        parts = []
        
        if error_type == 'LOW_SHARPE':
            sharpe = metrics.get('sharpe', 0) if metrics else 0
            parts.append(f"低Sharpe ({sharpe:.2f})")
        elif error_type == 'LOW_FITNESS':
            fitness = metrics.get('fitness', 0) if metrics else 0
            parts.append(f"低Fitness ({fitness:.2f})")
        elif error_type == 'HIGH_TURNOVER':
            turnover = metrics.get('turnover', 0) if metrics else 0
            parts.append(f"高Turnover ({turnover:.2f})")
        elif error_type == 'HIGH_CORRELATION':
            parts.append("高相关性 - 与现有alpha重复")
        elif error_type == 'NEGATIVE_SIGNAL':
            parts.append("负信号 - 方向相反")
        else:
            parts.append(f"失败类型: {error_type}")
        
        if op_chain:
            parts.append(f"算子链: {' → '.join(op_chain[:3])}")
        
        return "; ".join(parts)
