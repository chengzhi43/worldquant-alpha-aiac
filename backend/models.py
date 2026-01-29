"""
Models - Backward compatibility module

This file re-exports all models from the new modular structure
at backend/models/ for backward compatibility.

New code should import directly from backend.models:
    from backend.models import Alpha, MiningTask, KnowledgeEntry
"""

# Re-export everything from the models package
from backend.models import *
