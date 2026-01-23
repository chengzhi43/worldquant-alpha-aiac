from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Text, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import SQLAlchemyBase

import enum

class MiningStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class MiningTask(SQLAlchemyBase):
    __tablename__ = "mining_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String, nullable=False)
    region = Column(String, nullable=False)
    universe = Column(String, nullable=False)
    target_dataset_id = Column(String, nullable=True) # If null, auto-explore
    status = Column(String, default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED, STOPPED
    config = Column(JSON, default={}) # Budget, thresholds, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    jobs = relationship("MiningJob", back_populates="task")

class MiningJob(SQLAlchemyBase):
    __tablename__ = "mining_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("mining_tasks.id"))
    dataset_id = Column(String, nullable=True)
    datafield_list = Column(JSON, nullable=True) # Stored as JSON list of strings
    agent_version = Column(String, nullable=True)
    status = Column(String, default="RUNNING")
    result_summary = Column(JSON, default={}) # { "generated": 0, "simulated": 0, "passed": 0 }
    error_log = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    task = relationship("MiningTask", back_populates="jobs")
    alphas = relationship("Alpha", back_populates="job")

class Alpha(SQLAlchemyBase):
    __tablename__ = "alpha_base"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("mining_jobs.id"))
    alpha_id = Column(String, unique=True, index=True, nullable=True) # Brain Alpha ID
    expression = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    logic_explanation = Column(Text, nullable=True)
    
    # Metadata
    region = Column(String, nullable=True)
    universe = Column(String, nullable=True)
    dataset_id = Column(String, nullable=True)
    fields_used = Column(JSON, default=[])
    operators_used = Column(JSON, default=[])
    
    # Status
    simulation_status = Column(String, default="PENDING")
    quality_status = Column(String, default="PENDING") # PASS, REJECT
    diversity_status = Column(String, default="PENDING") # PASS, DUPLICATE
    
    # Metrics
    metrics = Column(JSON, default={}) # Sharpe, Turnover...
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    job = relationship("MiningJob", back_populates="alphas")

class AlphaFailure(SQLAlchemyBase):
    __tablename__ = "alpha_failures"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("mining_jobs.id"), nullable=True)
    expression = Column(Text, nullable=True)
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DatasetMetadata(SQLAlchemyBase):
    __tablename__ = "datasets"
    
    dataset_id = Column(String, primary_key=True)
    region = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    field_count = Column(Integer, default=0)
    alpha_count = Column(Integer, default=0)
    coverage = Column(Float, default=0.0)
    
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now())

class OperatorPreference(SQLAlchemyBase):
    __tablename__ = "operator_prefs"
    
    operator_name = Column(String, primary_key=True)
    status = Column(String, default="ACTIVE") # ACTIVE, BANNED
    failure_rate = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
