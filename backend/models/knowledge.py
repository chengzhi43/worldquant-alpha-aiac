"""
Knowledge Models - Knowledge base and learning entities

Contains KnowledgeEntry, OperatorPreference, and related models.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from backend.database import SQLAlchemyBase


class KnowledgeEntry(SQLAlchemyBase):
    """
    Knowledge Entry - Stores patterns learned from mining operations.
    
    Used by RAG service to provide context for alpha generation.
    """
    __tablename__ = "knowledge_entries"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    entry_type = Column(String(50), nullable=False)  # SUCCESS_PATTERN, FAILURE_PITFALL, etc.
    pattern = Column(Text)
    description = Column(Text)
    meta_data = Column(JSONB, default={})
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50), default="SYSTEM")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class OperatorPreference(SQLAlchemyBase):
    """
    Operator Preference - Tracks operator usage statistics.
    
    Used for learning which operators are more successful.
    """
    __tablename__ = "operator_prefs"
    __table_args__ = {'extend_existing': True}
    
    operator_name = Column(String(100), primary_key=True)
    status = Column(String(50), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_rate = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now())


class RLState(SQLAlchemyBase):
    """
    RL State - Reinforcement learning state for exploration.
    """
    __tablename__ = "rl_states"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    state_key = Column(String(200), unique=True, nullable=False)
    state_type = Column(String(50), nullable=False)
    q_value = Column(Float, default=0.0)
    visit_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    meta_data = Column(JSONB)
    updated_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())


class RLAction(SQLAlchemyBase):
    """
    RL Action - Reinforcement learning action record.
    """
    __tablename__ = "rl_actions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    state_id = Column(Integer)
    action_type = Column(String(100))
    action_params = Column(JSONB)
    reward = Column(Float)
    next_state_id = Column(Integer)
    executed_at = Column(DateTime, server_default=func.now())
