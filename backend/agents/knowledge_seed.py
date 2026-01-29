"""
Knowledge Base Seeder - Enhanced with 101 Alphas Patterns

This module provides comprehensive seed data for the knowledge base:
1. Dataset-category-specific success patterns
2. Region-specific optimizations
3. Validated pitfalls from common failures
4. Operator combination recommendations

Reference: 101 Formulaic Alphas (Kakushadze, 2016), Alpha-GPT, WorldQuant BRAIN best practices
"""

import asyncio
import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
from backend.models import KnowledgeEntry
from backend.config import settings
from loguru import logger


# =============================================================================
# 101 FORMULAIC ALPHAS - Core Patterns (Kakushadze 2016)
# =============================================================================

ALPHA_101_PATTERNS = [
    # Price-Volume Momentum Patterns
    {
        "pattern": "rank(ts_argmax(signed_power(if_else(returns > 0, ts_std_dev(returns, 20), close), 2), 5))",
        "description": "Alpha#1: Ranks based on argmax of conditional volatility. Captures volatility clustering.",
        "dataset_categories": ["pv", "price"],
        "expected_sharpe": 1.2,
        "regions": ["USA", "ASI", "EUR"]
    },
    {
        "pattern": "-1 * ts_corr(rank(ts_delta(log(volume), 2)), rank(divide(subtract(close, open), open)), 6)",
        "description": "Alpha#2: Volume-price correlation reversal. Negative correlation suggests mean reversion.",
        "dataset_categories": ["pv", "price"],
        "expected_sharpe": 1.3,
        "regions": ["USA", "GLB"]
    },
    {
        "pattern": "-1 * ts_corr(rank(open), rank(volume), 10)",
        "description": "Alpha#3: Open-volume rank correlation. Contrarian signal.",
        "dataset_categories": ["pv"],
        "expected_sharpe": 1.1,
        "regions": ["USA", "ASI"]
    },
    {
        "pattern": "-1 * ts_rank(rank(low), 9)",
        "description": "Alpha#4: Double-ranked low reversal. Mean reversion on oversold.",
        "dataset_categories": ["pv", "price"],
        "expected_sharpe": 1.0,
        "regions": ["USA", "EUR"]
    },
    {
        "pattern": "rank(subtract(open, divide(ts_sum(vwap, 10), 10))) * -1 * abs(rank(subtract(close, vwap)))",
        "description": "Alpha#5: VWAP deviation momentum. Captures institutional flow.",
        "dataset_categories": ["pv"],
        "expected_sharpe": 1.4,
        "regions": ["USA", "GLB"]
    },
    {
        "pattern": "-1 * ts_corr(open, volume, 10)",
        "description": "Alpha#6: Simple open-volume correlation reversal.",
        "dataset_categories": ["pv"],
        "expected_sharpe": 1.0,
        "regions": ["USA", "ASI", "EUR"]
    },
    {
        "pattern": "if_else(ts_mean(volume, 20) < volume, -1 * ts_rank(abs(ts_delta(close, 7)), 60) * sign(ts_delta(close, 7)), -1)",
        "description": "Alpha#7: Volume-confirmed price momentum reversal.",
        "dataset_categories": ["pv"],
        "expected_sharpe": 1.2,
        "regions": ["USA", "GLB"]
    },
    {
        "pattern": "-1 * rank(subtract(multiply(ts_sum(open, 5), ts_sum(returns, 5)), ts_delay(multiply(ts_sum(open, 5), ts_sum(returns, 5)), 10)))",
        "description": "Alpha#8: Open-returns momentum differential.",
        "dataset_categories": ["pv", "price"],
        "expected_sharpe": 1.1,
        "regions": ["USA", "ASI"]
    },
    # Fundamental Patterns
    {
        "pattern": "ts_rank(ts_delta(divide(close, ts_mean(close, 200)), 5), 20)",
        "description": "Price relative to 200-day mean momentum. Long-term trend following.",
        "dataset_categories": ["pv", "fundamental"],
        "expected_sharpe": 1.3,
        "regions": ["USA", "EUR", "GLB"]
    },
    {
        "pattern": "rank(ts_zscore(eps_growth, 60))",
        "description": "Earnings growth surprise. Captures post-earnings drift.",
        "dataset_categories": ["fundamental", "analyst"],
        "expected_sharpe": 1.5,
        "regions": ["USA", "EUR"]
    },
]

# =============================================================================
# DATASET CATEGORY SPECIFIC PATTERNS
# =============================================================================

CATEGORY_PATTERNS = {
    # Price-Volume (pv) Patterns
    "pv": [
        {
            "pattern": "ts_rank(ts_decay_linear(ts_corr(close, volume, 10), 5), 20)",
            "description": "Decayed price-volume correlation rank. Effective for momentum capture.",
            "expected_sharpe": 1.2
        },
        {
            "pattern": "rank(divide(ts_delta(close, 5), ts_std_dev(close, 20)))",
            "description": "Risk-adjusted momentum. Sharpe-like signal construction.",
            "expected_sharpe": 1.4
        },
        {
            "pattern": "ts_rank(divide(vwap, close), 10) * -1",
            "description": "VWAP premium reversal. Institutional flow indicator.",
            "expected_sharpe": 1.3
        },
        {
            "pattern": "ts_rank(subtract(ts_mean(close, 10), ts_mean(close, 30)), 5)",
            "description": "Moving average crossover momentum.",
            "expected_sharpe": 1.1
        },
        {
            "pattern": "rank(multiply(ts_delta(volume, 1), ts_delta(close, 1)))",
            "description": "Volume-price co-movement. Confirmation signal.",
            "expected_sharpe": 1.0
        },
    ],
    
    # Analyst/Estimates Patterns
    "analyst": [
        {
            "pattern": "ts_rank(ts_delta(eps_est, 20), 10)",
            "description": "Earnings estimate revision momentum.",
            "expected_sharpe": 1.6
        },
        {
            "pattern": "rank(subtract(actual_eps, est_eps))",
            "description": "Earnings surprise rank. Post-announcement drift.",
            "expected_sharpe": 1.5
        },
        {
            "pattern": "ts_zscore(divide(target_price, close), 60)",
            "description": "Analyst target price deviation. Value signal.",
            "expected_sharpe": 1.3
        },
        {
            "pattern": "ts_rank(recommendation_change, 20)",
            "description": "Analyst recommendation momentum.",
            "expected_sharpe": 1.4
        },
        {
            "pattern": "rank(multiply(estimate_revisions_up, inverse(estimate_revisions_down)))",
            "description": "Upward revision ratio. Sentiment indicator.",
            "expected_sharpe": 1.2
        },
    ],
    
    # Fundamental Patterns
    "fundamental": [
        {
            "pattern": "rank(divide(book_value, market_cap))",
            "description": "Book-to-market ratio. Classic value factor.",
            "expected_sharpe": 1.2
        },
        {
            "pattern": "ts_rank(ts_delta(roe, 252), 20)",
            "description": "ROE improvement momentum. Quality factor.",
            "expected_sharpe": 1.3
        },
        {
            "pattern": "rank(divide(free_cash_flow, enterprise_value))",
            "description": "FCF yield. Cash generation quality.",
            "expected_sharpe": 1.4
        },
        {
            "pattern": "rank(subtract(gross_margin, ts_mean(gross_margin, 252)))",
            "description": "Margin expansion. Profitability improvement.",
            "expected_sharpe": 1.2
        },
        {
            "pattern": "ts_zscore(divide(revenue_growth, asset_growth), 60)",
            "description": "Growth quality. Revenue vs asset growth ratio.",
            "expected_sharpe": 1.1
        },
    ],
    
    # News/Sentiment Patterns
    "news": [
        {
            "pattern": "ts_rank(vec_avg(sentiment_score), 5)",
            "description": "Sentiment momentum. News-driven signal.",
            "expected_sharpe": 1.1
        },
        {
            "pattern": "rank(multiply(vec_count(news_articles), vec_avg(sentiment_score)))",
            "description": "Volume-weighted sentiment. High coverage confirmation.",
            "expected_sharpe": 1.2
        },
        {
            "pattern": "ts_zscore(vec_sum(headline_sentiment), 20)",
            "description": "Headline sentiment z-score. Short-term momentum.",
            "expected_sharpe": 1.0
        },
        {
            "pattern": "ts_rank(subtract(vec_avg(positive_mentions), vec_avg(negative_mentions)), 10)",
            "description": "Net sentiment momentum. Trend following on news.",
            "expected_sharpe": 1.1
        },
    ],
    
    # Other/Alternative Data Patterns
    "other": [
        {
            "pattern": "ts_rank(vec_avg(field), 20)",
            "description": "Generic ranked average for vector fields.",
            "expected_sharpe": 0.8
        },
        {
            "pattern": "rank(ts_delta(vec_sum(field), 5))",
            "description": "Generic momentum on summed vector field.",
            "expected_sharpe": 0.9
        },
        {
            "pattern": "ts_zscore(vec_avg(field), 60)",
            "description": "Long-term z-score normalization.",
            "expected_sharpe": 0.7
        },
    ],
}

# =============================================================================
# REGION-SPECIFIC OPTIMIZATIONS
# =============================================================================

REGION_OPTIMIZATIONS = {
    "USA": {
        "recommended_universe": "TOP3000",
        "recommended_decay": 4,
        "recommended_neutralization": "SUBINDUSTRY",
        "sharpe_adjustment": 1.0,
        "notes": "Most liquid market. Standard settings work well."
    },
    "KOR": {
        "recommended_universe": "TOP600",
        "recommended_decay": 6,
        "recommended_neutralization": "INDUSTRY",
        "sharpe_adjustment": 0.8,
        "notes": "Smaller universe. Longer decay helps reduce turnover."
    },
    "ASI": {
        "recommended_universe": "MINVOL1M",
        "recommended_decay": 8,
        "recommended_neutralization": "MARKET",
        "sharpe_adjustment": 0.7,
        "notes": "Diverse markets. Use MINVOL filter for liquidity."
    },
    "EUR": {
        "recommended_universe": "TOP1500",
        "recommended_decay": 5,
        "recommended_neutralization": "SUBINDUSTRY",
        "sharpe_adjustment": 0.9,
        "notes": "Mixed liquidity. Moderate settings."
    },
    "GLB": {
        "recommended_universe": "TOP3000",
        "recommended_decay": 6,
        "recommended_neutralization": "MARKET",
        "sharpe_adjustment": 0.75,
        "notes": "Global requires market neutralization."
    },
    "IND": {
        "recommended_universe": "TOP500",
        "recommended_decay": 8,
        "recommended_neutralization": "INDUSTRY",
        "sharpe_adjustment": 0.7,
        "notes": "Small universe. Conservative settings."
    },
    "CHN": {
        "recommended_universe": "TOP2000U",
        "recommended_decay": 6,
        "recommended_neutralization": "INDUSTRY",
        "sharpe_adjustment": 0.8,
        "notes": "Unique market dynamics. Longer decay preferred."
    },
}

# =============================================================================
# COMPREHENSIVE PITFALLS
# =============================================================================

COMPREHENSIVE_PITFALLS = [
    # Syntax Errors
    {
        "pattern": "ts_corr(field, field, window)",
        "description": "Self-correlation is always 1. Avoid correlating a field with itself.",
        "error_type": "LOGIC_ERROR",
        "severity": "high"
    },
    {
        "pattern": "ts_zscore(field, 1)",
        "description": "Z-score with window 1 is always 0 or NaN. Minimum window should be 2.",
        "error_type": "PARAMETER_ERROR",
        "severity": "high"
    },
    {
        "pattern": "ts_mean(field, 0)",
        "description": "Window size must be positive integer. Zero causes errors.",
        "error_type": "PARAMETER_ERROR",
        "severity": "high"
    },
    {
        "pattern": "rank(industry)",
        "description": "Cannot rank categorical fields. Use group_neutralize for sector/industry.",
        "error_type": "SEMANTIC_ERROR",
        "severity": "high"
    },
    {
        "pattern": "ts_rank(vector_field, 20)",
        "description": "VECTOR fields must use vec_* operators first (vec_sum, vec_avg, etc.) before ts_* operators.",
        "error_type": "TYPE_ERROR",
        "severity": "high"
    },
    
    # Common Quality Failures
    {
        "pattern": "ts_rank(field, 1)",
        "description": "Window too small for ts_rank. Results in high turnover. Use window >= 5.",
        "error_type": "HIGH_TURNOVER",
        "severity": "medium"
    },
    {
        "pattern": "multiply(ts_rank(a, 5), ts_rank(b, 5))",
        "description": "Product of rankings without decay leads to high turnover. Add ts_decay_linear.",
        "error_type": "HIGH_TURNOVER",
        "severity": "medium"
    },
    {
        "pattern": "raw_field without rank/zscore",
        "description": "Using raw field values without normalization leads to poor cross-sectional comparability.",
        "error_type": "LOW_SHARPE",
        "severity": "medium"
    },
    {
        "pattern": "ts_sum(field, 250) without decay",
        "description": "Very long lookback without decay is slow to adapt. Add decay or use shorter window.",
        "error_type": "SLOW_ADAPTATION",
        "severity": "low"
    },
    
    # Simulation Failures
    {
        "pattern": "divide(a, b) where b can be zero",
        "description": "Division by zero causes NaN. Use pasteurize() or add small epsilon.",
        "error_type": "NAN_OVERFLOW",
        "severity": "high"
    },
    {
        "pattern": "log(field) where field can be <= 0",
        "description": "Log of non-positive values is undefined. Use abs() or filter first.",
        "error_type": "NAN_OVERFLOW",
        "severity": "high"
    },
    {
        "pattern": "power(field, large_exponent)",
        "description": "Large powers cause overflow. Keep exponent <= 2 or use signed_power.",
        "error_type": "OVERFLOW",
        "severity": "medium"
    },
    
    # Dataset-Specific Pitfalls
    {
        "pattern": "ts_delta(sparse_field, 1)",
        "description": "Delta on sparse (infrequently updated) fields is mostly NaN. Use ts_backfill first.",
        "error_type": "SPARSE_DATA",
        "severity": "medium"
    },
    {
        "pattern": "vec_avg(non_vector_field)",
        "description": "vec_* operators only work on VECTOR type fields. Check field type first.",
        "error_type": "TYPE_ERROR",
        "severity": "high"
    },
]

# =============================================================================
# OPERATOR COMBINATIONS THAT WORK WELL
# =============================================================================

EFFECTIVE_OPERATOR_COMBOS = [
    {
        "combo": "ts_rank + ts_decay_linear",
        "description": "Ranking with decay reduces turnover while maintaining signal.",
        "use_case": "momentum signals"
    },
    {
        "combo": "rank + group_neutralize",
        "description": "Neutralization after ranking removes sector bets.",
        "use_case": "fundamental factors"
    },
    {
        "combo": "ts_zscore + rank",
        "description": "Z-score normalization followed by ranking improves cross-sectional comparability.",
        "use_case": "any continuous field"
    },
    {
        "combo": "vec_sum/vec_avg + ts_rank",
        "description": "Aggregate vector fields then apply time-series operations.",
        "use_case": "news/sentiment data"
    },
    {
        "combo": "ts_delta + sign + ts_rank",
        "description": "Signed change ranked. Captures direction with ranking stability.",
        "use_case": "momentum reversals"
    },
    {
        "combo": "ts_backfill + ts_zscore",
        "description": "Fill gaps before normalization for sparse fundamental data.",
        "use_case": "quarterly reported data"
    },
]


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

async def seed_knowledge_base(force_reseed: bool = False):
    """
    Seed the database with comprehensive knowledge patterns.
    
    Args:
        force_reseed: If True, clear existing entries and reseed
    """
    logger.info("Starting knowledge base seeding...")
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check existing entries
        existing = await session.execute(text("SELECT count(*) FROM knowledge_entries"))
        count = existing.scalar()
        
        if count > 0 and not force_reseed:
            logger.info(f"Knowledge base already has {count} entries. Use force_reseed=True to reseed.")
            return count
        
        if force_reseed and count > 0:
            logger.warning(f"Force reseeding: Clearing {count} existing entries...")
            await session.execute(text("DELETE FROM knowledge_entries"))
            await session.commit()
        
        entries_added = 0
        
        # 1. Seed 101 Alphas patterns
        logger.info("Seeding 101 Alphas patterns...")
        for p in ALPHA_101_PATTERNS:
            entry = KnowledgeEntry(
                entry_type='SUCCESS_PATTERN',
                pattern=p['pattern'],
                description=p['description'],
                meta_data={
                    'source': '101_alphas',
                    'dataset_categories': p.get('dataset_categories', ['general']),
                    'expected_sharpe': p.get('expected_sharpe', 1.0),
                    'regions': p.get('regions', ['USA']),
                    'score': 0.9
                },
                usage_count=0,
                is_active=True,
                created_by='SYSTEM'
            )
            session.add(entry)
            entries_added += 1
        
        # 2. Seed category-specific patterns
        logger.info("Seeding category-specific patterns...")
        for category, patterns in CATEGORY_PATTERNS.items():
            for p in patterns:
                entry = KnowledgeEntry(
                    entry_type='SUCCESS_PATTERN',
                    pattern=p['pattern'],
                    description=p['description'],
                    meta_data={
                        'source': f'category_{category}',
                        'dataset_category': category,
                        'expected_sharpe': p.get('expected_sharpe', 1.0),
                        'score': 0.8
                    },
                    usage_count=0,
                    is_active=True,
                    created_by='SYSTEM'
                )
                session.add(entry)
                entries_added += 1
        
        # 3. Seed pitfalls
        logger.info("Seeding pitfalls...")
        for p in COMPREHENSIVE_PITFALLS:
            entry = KnowledgeEntry(
                entry_type='FAILURE_PITFALL',
                pattern=p['pattern'],
                description=p['description'],
                meta_data={
                    'source': 'comprehensive_pitfalls',
                    'error_type': p.get('error_type'),
                    'severity': p.get('severity', 'medium')
                },
                usage_count=0,
                is_active=True,
                created_by='SYSTEM'
            )
            session.add(entry)
            entries_added += 1
        
        # 4. Seed operator combinations as patterns
        logger.info("Seeding operator combinations...")
        for combo in EFFECTIVE_OPERATOR_COMBOS:
            entry = KnowledgeEntry(
                entry_type='SUCCESS_PATTERN',
                pattern=combo['combo'],
                description=combo['description'],
                meta_data={
                    'source': 'operator_combos',
                    'use_case': combo.get('use_case'),
                    'pattern_type': 'operator_combo',
                    'score': 0.7
                },
                usage_count=0,
                is_active=True,
                created_by='SYSTEM'
            )
            session.add(entry)
            entries_added += 1
        
        # 5. Seed region optimizations as metadata entries
        logger.info("Seeding region optimizations...")
        for region, config in REGION_OPTIMIZATIONS.items():
            entry = KnowledgeEntry(
                entry_type='SUCCESS_PATTERN',
                pattern=f"REGION_CONFIG:{region}",
                description=config['notes'],
                meta_data={
                    'source': 'region_config',
                    'region': region,
                    'recommended_universe': config['recommended_universe'],
                    'recommended_decay': config['recommended_decay'],
                    'recommended_neutralization': config['recommended_neutralization'],
                    'sharpe_adjustment': config['sharpe_adjustment'],
                    'pattern_type': 'region_config'
                },
                usage_count=0,
                is_active=True,
                created_by='SYSTEM'
            )
            session.add(entry)
            entries_added += 1
        
        await session.commit()
        logger.info(f"Knowledge base seeding complete! Added {entries_added} entries.")
        
        return entries_added


async def get_knowledge_stats() -> Dict[str, Any]:
    """Get statistics about the knowledge base."""
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Count by type
        type_counts = await session.execute(text("""
            SELECT entry_type, count(*) as cnt 
            FROM knowledge_entries 
            WHERE is_active = true 
            GROUP BY entry_type
        """))
        
        # Top used patterns
        top_patterns = await session.execute(text("""
            SELECT pattern, usage_count 
            FROM knowledge_entries 
            WHERE entry_type = 'SUCCESS_PATTERN' AND is_active = true 
            ORDER BY usage_count DESC 
            LIMIT 5
        """))
        
        return {
            "type_counts": dict(type_counts.fetchall()),
            "top_patterns": [{"pattern": r[0][:50], "usage": r[1]} for r in top_patterns.fetchall()],
        }


def get_patterns_for_dataset_category(category: str) -> List[Dict]:
    """
    Get success patterns relevant to a dataset category.
    
    Args:
        category: Dataset category (pv, analyst, fundamental, news, other)
    
    Returns:
        List of pattern dictionaries
    """
    # Normalize category
    cat_lower = category.lower()
    
    # Map common dataset prefixes to categories
    category_mapping = {
        "pv": ["pv", "price", "volume", "trade"],
        "analyst": ["analyst", "anl", "estimate", "forecast", "recommendation"],
        "fundamental": ["fundamental", "fnd", "fin", "balance", "income", "cash"],
        "news": ["news", "sentiment", "headline", "article", "media"],
        "other": ["other", "oth", "misc", "alternative"],
    }
    
    matched_category = "other"
    for cat_key, prefixes in category_mapping.items():
        for prefix in prefixes:
            if prefix in cat_lower:
                matched_category = cat_key
                break
    
    return CATEGORY_PATTERNS.get(matched_category, CATEGORY_PATTERNS["other"])


def get_region_config(region: str) -> Dict:
    """Get recommended configuration for a region."""
    return REGION_OPTIMIZATIONS.get(region.upper(), REGION_OPTIMIZATIONS["USA"])


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Base Seeder")
    parser.add_argument("--force", action="store_true", help="Force reseed (clear existing)")
    parser.add_argument("--stats", action="store_true", help="Show knowledge base stats")
    args = parser.parse_args()
    
    if args.stats:
        stats = asyncio.run(get_knowledge_stats())
        print("\n=== Knowledge Base Statistics ===")
        print(f"Type counts: {stats['type_counts']}")
        print(f"Top patterns: {stats['top_patterns']}")
    else:
        result = asyncio.run(seed_knowledge_base(force_reseed=args.force))
        print(f"Seeding complete. Total entries: {result}")
