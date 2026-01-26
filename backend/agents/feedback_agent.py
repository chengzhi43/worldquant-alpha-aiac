"""
Feedback Agent - Analyzes failures and evolves the knowledge base
Implements the CoSTEER (Collaborative Evolving Strategy) feedback loop
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.models import AlphaFailure, KnowledgeEntry, Alpha
from backend.agents.prompts import FAILURE_ANALYSIS_SYSTEM, FAILURE_ANALYSIS_USER
from backend.config import settings

import openai
from loguru import logger


class FeedbackAgent:
    """
    Feedback Agent - Responsible for:
    1. Analyzing failure patterns
    2. Updating the knowledge base
    3. Generating prompt improvements
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = getattr(settings, 'OPENAI_MODEL', 'deepseek-chat')
    
    async def run_daily_feedback(self) -> Dict:
        """
        Run the daily feedback loop:
        1. Collect today's failures
        2. Analyze patterns
        3. Update knowledge base
        """
        logger.info("Starting daily feedback analysis...")
        
        # Get today's failures
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        failures_query = select(AlphaFailure).where(
            AlphaFailure.created_at >= start_of_day,
            AlphaFailure.is_analyzed == False
        )
        result = await self.db.execute(failures_query)
        failures = result.scalars().all()
        
        if not failures:
            logger.info("No new failures to analyze")
            return {"status": "no_failures", "analyzed": 0}
        
        logger.info(f"Analyzing {len(failures)} failures...")
        
        # Group by error type
        error_distribution = Counter(f.error_type for f in failures)
        
        # Get sample failures for each type
        sample_failures = []
        for error_type in error_distribution.keys():
            samples = [f for f in failures if f.error_type == error_type][:3]
            for s in samples:
                sample_failures.append({
                    'expression': s.expression[:200] if s.expression else '',
                    'error_type': s.error_type,
                    'error_message': s.error_message[:200] if s.error_message else ''
                })
        
        # Use LLM to analyze patterns
        analysis = await self._analyze_with_llm(
            count=len(failures),
            error_distribution=dict(error_distribution),
            sample_failures=sample_failures
        )
        
        # Update knowledge base with new pitfalls
        new_entries = 0
        if analysis.get('patterns'):
            for pattern in analysis['patterns']:
                # Check if similar pattern already exists
                exists = await self._pattern_exists(pattern['pattern'])
                if not exists:
                    entry = KnowledgeEntry(
                        entry_type='FAILURE_PITFALL',
                        pattern=pattern['pattern'],
                        description=pattern.get('recommendation', ''),
                        meta_data={
                            'frequency': pattern.get('frequency', 0),
                            'source': 'feedback_agent',
                            'date': today.isoformat()
                        },
                        created_by='SYSTEM'
                    )
                    self.db.add(entry)
                    new_entries += 1
        
        # Mark failures as analyzed
        for failure in failures:
            failure.is_analyzed = True
        
        await self.db.commit()
        
        logger.info(f"Feedback analysis complete: {new_entries} new knowledge entries")
        
        return {
            "status": "success",
            "analyzed": len(failures),
            "new_entries": new_entries,
            "patterns": analysis.get('patterns', []),
            "improvements": analysis.get('prompt_improvements', [])
        }
    
    async def learn_from_success(self, alpha: Alpha) -> Optional[Dict]:
        """
        Learn from a successful alpha (especially if liked by human).
        Extract patterns for knowledge base.
        """
        if not alpha.expression:
            return None
        
        # Extract pattern from the alpha
        operators = alpha.operators_used or []
        pattern_parts = []
        
        # Build pattern description
        for op in operators[:3]:  # Top 3 operators
            pattern_parts.append(op)
        
        if not pattern_parts:
            return None
        
        pattern = " + ".join(pattern_parts)
        
        # Check if similar pattern exists
        exists = await self._pattern_exists(pattern)
        if exists:
            # Update usage count
            await self._increment_pattern_usage(pattern)
            return {"action": "incremented", "pattern": pattern}
        
        # Create new success pattern
        entry = KnowledgeEntry(
            entry_type='SUCCESS_PATTERN',
            pattern=pattern,
            description=alpha.hypothesis or alpha.logic_explanation or '',
            meta_data={
                'sharpe': alpha.metrics.get('sharpe') if alpha.metrics else None,
                'dataset': alpha.dataset_id,
                'region': alpha.region,
                'human_feedback': alpha.human_feedback
            },
            created_by='SYSTEM'
        )
        self.db.add(entry)
        await self.db.commit()
        
        logger.info(f"New success pattern learned: {pattern}")
        return {"action": "created", "pattern": pattern}
    
    async def update_operator_stats(self) -> Dict:
        """
        Update operator usage and failure statistics.
        """
        # Get all alphas from last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        alphas_query = select(Alpha).where(
            Alpha.created_at >= thirty_days_ago
        )
        result = await self.db.execute(alphas_query)
        alphas = result.scalars().all()
        
        # Count operator usage and success
        operator_stats = {}
        for alpha in alphas:
            operators = alpha.operators_used or []
            is_success = alpha.quality_status == 'PASS'
            
            for op in operators:
                if op not in operator_stats:
                    operator_stats[op] = {'usage': 0, 'success': 0}
                operator_stats[op]['usage'] += 1
                if is_success:
                    operator_stats[op]['success'] += 1
        
        # Update operator_prefs table
        from backend.models import OperatorPreference
        
        for op_name, stats in operator_stats.items():
            failure_rate = 1 - (stats['success'] / stats['usage']) if stats['usage'] > 0 else 0
            
            # Check if exists
            query = select(OperatorPreference).where(
                OperatorPreference.operator_name == op_name
            )
            result = await self.db.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.usage_count = stats['usage']
                existing.success_count = stats['success']
                existing.failure_rate = failure_rate
                # Auto-ban if failure rate > 80%
                if failure_rate > 0.8:
                    existing.status = 'BANNED'
            else:
                pref = OperatorPreference(
                    operator_name=op_name,
                    usage_count=stats['usage'],
                    success_count=stats['success'],
                    failure_rate=failure_rate,
                    status='ACTIVE' if failure_rate <= 0.8 else 'BANNED'
                )
                self.db.add(pref)
        
        await self.db.commit()
        return operator_stats
    
    async def _analyze_with_llm(
        self, count: int, error_distribution: Dict, sample_failures: List[Dict]
    ) -> Dict:
        """Use LLM to analyze failure patterns."""
        try:
            prompt = FAILURE_ANALYSIS_USER.format(
                count=count,
                error_distribution=json.dumps(error_distribution, indent=2),
                sample_failures=json.dumps(sample_failures, indent=2, ensure_ascii=False)
            )
            
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": FAILURE_ANALYSIS_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(self._clean_json(content))
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {"patterns": [], "prompt_improvements": []}
    
    async def _pattern_exists(self, pattern: str) -> bool:
        """Check if a pattern already exists in knowledge base."""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.pattern == pattern,
            KnowledgeEntry.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def _increment_pattern_usage(self, pattern: str):
        """Increment usage count for existing pattern."""
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.pattern == pattern
        )
        result = await self.db.execute(query)
        entry = result.scalar_one_or_none()
        if entry:
            entry.usage_count += 1
    
    def _clean_json(self, content: str) -> str:
        """Clean JSON response from LLM."""
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        return content.strip()
        
    async def learn_from_round(
        self,
        successes: List[Alpha],
        failures: List[Dict],
        iteration: int,
        dataset_id: str,
        region: str
    ) -> Dict:
        """
        Learn from a complete mining round (Successes & Failures).
        This enables evolutionary improvement between iterations.
        
        Args:
            successes: List of passed Alpha objects
            failures: List of failure dicts (from Workflow result)
            iteration: Current iteration index
            dataset_id: Context
            region: Context
            
        Returns:
            Dict with learned stats
        """
        from backend.agents.prompts import ROUND_ANALYSIS_SYSTEM, ROUND_ANALYSIS_USER
        
        # Skip if too little data to learn
        if not successes and not failures:
            return {"status": "skipped", "reason": "no_data"}
            
        logger.info(f"[Feedback] Learning from Round {iteration} (Success={len(successes)}, Fail={len(failures)})")
        
        # Prepare examples for LLM
        success_examples = "\n".join([
            f"- Expr: {a.expression}\n  Logic: {a.logic_explanation}\n  Sharpe: {a.metrics.get('sharpe', 'N/A')}"
            for a in successes[:5]
        ]) or "None"
        
        failure_examples = "\n".join([
            f"- Expr: {f.get('expression', 'N/A')[:100]}...\n  Error: {f.get('error_message', 'N/A')[:150]}"
            for f in failures[:5]
        ]) or "None"
        
        try:
            # Call LLM for analysis
            prompt = ROUND_ANALYSIS_USER.format(
                iteration=iteration,
                success_count=len(successes),
                success_examples=success_examples,
                failure_count=len(failures),
                failure_examples=failure_examples,
                dataset_id=dataset_id,
                region=region
            )
            
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ROUND_ANALYSIS_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(self._clean_json(response.choices[0].message.content))
            
            # Store learned knowledge
            new_entries = 0
            
            # 1. Store New Patterns
            for p in analysis.get("new_patterns", []):
                # Check exist
                if not await self._pattern_exists(p.get("pattern", "")):
                    entry = KnowledgeEntry(
                        entry_type='SUCCESS_PATTERN',
                        pattern=p.get("pattern"),
                        description=p.get("description"),
                        meta_data={
                            'round': iteration,
                            'score': p.get("score"),
                            'source': 'evolution_loop'
                        }
                    )
                    self.db.add(entry)
                    new_entries += 1

            # 2. Store New Pitfalls
            for p in analysis.get("new_pitfalls", []):
                if not await self._pattern_exists(p.get("pattern", "")):
                    entry = KnowledgeEntry(
                        entry_type='FAILURE_PITFALL',
                        pattern=p.get("pattern"),
                        description=p.get("description"),
                        meta_data={
                            'round': iteration,
                            'recommendation': p.get("recommendation"),
                            'source': 'evolution_loop'
                        }
                    )
                    self.db.add(entry)
                    new_entries += 1
            
            await self.db.commit()
            logger.info(f"[Feedback] Round learning complete. Added {new_entries} knowledge entries.")
            
            return {
                "new_entries": new_entries,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"[Feedback] Learn from round failed: {e}")
            return {"error": str(e)}
