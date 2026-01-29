"""
Test Fixtures - Mock implementations and test data factories

This module provides:
- Mock implementations of external services (BRAIN, LLM)
- Test data factories
- Common test utilities
"""

from backend.tests.fixtures.mock_brain import MockBrainAdapter
from backend.tests.fixtures.mock_llm import MockLLMService

__all__ = [
    "MockBrainAdapter",
    "MockLLMService",
]
