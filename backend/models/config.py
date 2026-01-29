"""
Config Models - System configuration and credentials

Contains SystemConfig, credentials, and auth token models.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.sql import func

from backend.database import SQLAlchemyBase


class SystemConfig(SQLAlchemyBase):
    """
    System Config - Key-value configuration storage.
    """
    __tablename__ = "system_configs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text)
    config_type = Column(String(50))
    description = Column(Text)
    updated_at = Column(DateTime, server_default=func.now())


class BrainAuthToken(SQLAlchemyBase):
    """
    Brain Auth Token - Cached authentication tokens.
    """
    __tablename__ = "brain_auth_tokens"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, default=1)
    email = Column(String(255))
    jwt_token = Column(Text, nullable=False)
    last_auth_time = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WQBCredential(SQLAlchemyBase):
    """
    WQB Credential - Encrypted WorldQuant credentials.
    """
    __tablename__ = "wqb_credentials"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    username_encrypted = Column(Text, nullable=False)
    password_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class LLMProvider(SQLAlchemyBase):
    """
    LLM Provider - Configuration for LLM providers.
    """
    __tablename__ = "llm_providers"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    model_name = Column(String(200), nullable=False)
    api_key_encrypted = Column(Text)
    base_url = Column(String(500))
    max_tokens = Column(Integer, default=4096)
    temperature = Column(Float, default=0.7)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


