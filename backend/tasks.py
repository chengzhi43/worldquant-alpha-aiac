"""
Tasks - Backward compatibility module

This file re-exports all tasks from the new modular structure
at backend/tasks/ for backward compatibility.

New code should import directly from backend.tasks:
    from backend.tasks import run_mining_task, sync_user_alphas
"""

# Re-export everything from the tasks package
from backend.tasks import *
