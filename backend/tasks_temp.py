
@celery_app.task(name="backend.tasks.sync_operators_from_brain")
def sync_operators_from_brain():
    """Sync operators from BRAIN platform."""
    logger.info("Syncing operators from BRAIN...")
    
    async def _run():
        async with AsyncSessionLocal() as db:
            async with BrainAdapter() as brain:
                # BrainAdapter.get_operators currently returns List[str] (names only)
                # We might need to enhance BrainAdapter to return full objects if possible
                # But for now, let's assume we get names and just ensure they exist.
                # Actually, BrainAdapter.get_operators implementation calls /operators which returns objects.
                # Let's check BrainAdapter implementation again.
                # It returns [op.get("name") ...].
                # I should ideally modify BrainAdapter to return full dicts, but to avoid breaking changes,
                # I will fetch the full list here if I could, but BrainAdapter abstraction hides it.
                # I will modify BrainAdapter later if needed. For now, I will use what I have.
                # Wait, I can modify BrainAdapter.get_operators to return dicts?
                # User asked for "Data management ... operators".
                # I'll stick to a simple sync for now.
                
                # RE-CHECK: BrainAdapter.get_operators returns List[str].
                # I will modify it to return List[Dict] if I want descriptions.
                
                # For this task, I will assume BrainAdapter returns names for now, 
                # but to be useful, I should probably fetch descriptions.
                # Let's bypass BrainAdapter.get_operators wrapper and call client directly here?
                # No, that breaks abstraction.
                
                # I will modify BrainAdapter first or update this task to handle it.
                # Let's assume BrainAdapter is updated or I update it in next step.
                # Actually, I'll update BrainAdapter.get_operators to return list of dicts.
                pass 

    # Placeholder - I will implement the task body properly in next step after updating adapter.
    return {"status": "planned"}
