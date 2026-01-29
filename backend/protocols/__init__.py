"""
Protocols Module - Abstract interfaces for dependency injection and testability

This module defines protocols (abstract interfaces) that allow:
1. Dependency Inversion: High-level modules depend on abstractions, not implementations
2. Testability: Easy mocking by implementing protocols with test doubles
3. Flexibility: Swap implementations without changing client code
"""

from backend.protocols.brain_protocol import (
    BrainProtocol,
    SimulationResult,
    SimulationSettings,
    SimulationMetrics,
    SubmissionCheck,
    DatasetInfo,
    DataFieldInfo,
    OperatorInfo,
)
from backend.protocols.llm_protocol import (
    LLMProtocol,
    LLMResponse,
)
from backend.protocols.repository_protocol import (
    RepositoryProtocol,
    CRUDRepositoryProtocol,
)

__all__ = [
    # Brain Protocol
    "BrainProtocol",
    "SimulationResult",
    "SimulationSettings",
    "SimulationMetrics",
    "SubmissionCheck",
    "DatasetInfo",
    "DataFieldInfo",
    "OperatorInfo",
    # LLM Protocol
    "LLMProtocol",
    "LLMResponse",
    # Repository Protocol
    "RepositoryProtocol",
    "CRUDRepositoryProtocol",
]
