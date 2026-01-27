
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from backend.models import KnowledgeEntry
from backend.config import settings

# Common successful patterns in alpha mining
SUCCESS_PATTERNS = [
    {
        "pattern": "ts_decay_linear(rank(ts_zscore(field, 22)), 10)",
        "description": "Linear decay of ranked z-score. Effective for smoothing noisy signals while maintaining cross-sectional rank.",
        "score": 0.85
    },
    {
        "pattern": "ts_mean(field, 20) - ts_mean(field, 10)",
        "description": "Dual moving average crossover/divergence. Captures trend reversals or momentum depending on sign.",
        "score": 0.75
    },
    {
        "pattern": "rank(ts_delta(field, 5))",
        "description": "Ranked 5-day delta. Captures short-term momentum relative to market.",
        "score": 0.70
    },
    {
        "pattern": "group_neutralize(field, sector)",
        "description": "Sector neutralization. Essential for fundamental data to remove sector bets.",
        "score": 0.90
    },
    {
        "pattern": "trade_when(volume > ts_mean(volume, 20), delta(close, 1), -1)",
        "description": "Volume-confirmed price move. Signals based on price changes accompanied by volume spikes.",
        "score": 0.65
    }
]

# Common pitfalls to avoid
PITFALLS = [
    {
        "pattern": "ts_corr(field, field, 10)",
        "description": "Self-correlation is always 1 or error. Avoid correlating a field with itself.",
        "error_type": "LOGIC_ERROR",
        "severity": "high"
    },
    {
        "pattern": "rank(industry)",
        "description": "Ranking a categorical field like industry is invalid. Use group_neutralize instead.",
        "error_type": "SEMANTIC_ERROR",
        "severity": "high"
    },
    {
        "pattern": "ts_mean(field, 0)",
        "description": "Window size must be positive. 0 causes errors.",
        "error_type": "PARAMETER_ERROR",
        "severity": "medium"
    },
    {
        "pattern": "ts_zscore(field, 1)",
        "description": "Z-score with window 1 is always 0 or NaN. Window must be > 1.",
        "error_type": "PARAMETER_ERROR",
        "severity": "medium"
    }
]

async def seed_knowledge_base():
    """Seed the database with initial knowledge."""
    print("Connecting to database...")
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Checking existing entries...")
        # Check if already seeded
        existing = await session.execute(text("SELECT count(*) FROM knowledge_entries"))
        count = existing.scalar()
        
        if count > 0:
            print(f"Knowledge base already has {count} entries. Skipping seeding.")
            return

        print("Seeding success patterns...")
        for p in SUCCESS_PATTERNS:
            entry = KnowledgeEntry(
                entry_type='SUCCESS_PATTERN',
                pattern=p['pattern'],
                description=p['description'],
                meta_data={
                    'source': 'seed_script',
                    'score': p['score'],
                    'dataset_id': 'general'
                },
                created_by='SYSTEM'
            )
            session.add(entry)
            
        print("Seeding pitfalls...")
        for p in PITFALLS:
            entry = KnowledgeEntry(
                entry_type='FAILURE_PITFALL',
                pattern=p['pattern'],
                description=p['description'],
                meta_data={
                    'source': 'seed_script',
                    'error_type': p.get('error_type'),
                    'severity': p.get('severity')
                },
                created_by='SYSTEM'
            )
            session.add(entry)
            
        await session.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
