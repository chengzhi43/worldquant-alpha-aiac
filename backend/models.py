"""
AIAC 2.0 Database Models - Enhanced with Trace and Knowledge Base
Based on Alpha-GPT + RD-Agent Architecture
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Index, UniqueConstraint, Computed
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import SQLAlchemyBase

import enum


# =============================================================================
# ENUMS
# =============================================================================

class MiningStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class DatasetStrategy(str, enum.Enum):
    AUTO = "AUTO"           # Hierarchical RAG exploration
    SPECIFIC = "SPECIFIC"   # User-specified datasets


class AgentMode(str, enum.Enum):
    AUTONOMOUS = "AUTONOMOUS"   # Fully automatic
    INTERACTIVE = "INTERACTIVE"  # Pause at each step


class TraceStepType(str, enum.Enum):
    RAG_QUERY = "RAG_QUERY"
    HYPOTHESIS = "HYPOTHESIS"
    CODE_GEN = "CODE_GEN"
    VALIDATE = "VALIDATE"
    SIMULATE = "SIMULATE"
    SELF_CORRECT = "SELF_CORRECT"
    EVALUATE = "EVALUATE"


class QualityStatus(str, enum.Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    REJECT = "REJECT"


class HumanFeedback(str, enum.Enum):
    NONE = "NONE"
    LIKED = "LIKED"
    DISLIKED = "DISLIKED"


class KnowledgeEntryType(str, enum.Enum):
    SUCCESS_PATTERN = "SUCCESS_PATTERN"
    FAILURE_PITFALL = "FAILURE_PITFALL"
    FIELD_BLACKLIST = "FIELD_BLACKLIST"
    OPERATOR_STAT = "OPERATOR_STAT"


# =============================================================================
# CORE MODELS
# =============================================================================
# Note: Core models (MiningTask, TraceStep, Alpha, AlphaFailure, KnowledgeEntry)
# are defined in the "UPDATED CORE MODELS" section below (around line 500+)
# to avoid duplication and SQLAlchemy mapper conflicts.
# =============================================================================


# =============================================================================
# EXTENDED MODELS (From create_table.sql)
# =============================================================================

class AlphaPnl(SQLAlchemyBase):
    __tablename__ = "alpha_pnl"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    alpha_id = Column(Integer, index=True)
    trade_date = Column(DateTime, nullable=False)
    pnl = Column(Float)
    cumulative_pnl = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

class BrainAuthToken(SQLAlchemyBase):
    __tablename__ = "brain_auth_tokens"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, default=1)
    email = Column(String(255))
    jwt_token = Column(Text, nullable=False)
    last_auth_time = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class LLMProvider(SQLAlchemyBase):
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

class Neutralization(SQLAlchemyBase):
    __tablename__ = "neutralizations"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class Region(SQLAlchemyBase):
    __tablename__ = "regions"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Universe(SQLAlchemyBase):
    __tablename__ = "universes"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"))
    code = Column(String(50), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Operator(SQLAlchemyBase):
    __tablename__ = "operators"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(100))
    description = Column(Text)
    definition = Column(Text)
    scope = Column(ARRAY(String))
    level = Column(String(50))
    syntax = Column(Text)
    param_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class OperatorBlacklist(SQLAlchemyBase):
    __tablename__ = "operator_blacklist"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    operator_name = Column(String(100), unique=True, nullable=False)
    error_message = Column(Text)
    first_seen_at = Column(DateTime, server_default=func.now())
    hit_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

class PyramidMultiplier(SQLAlchemyBase):
    __tablename__ = "pyramid_multipliers"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    category = Column(String(100), nullable=False)
    region = Column(String(10), nullable=False)
    delay = Column(Integer, nullable=False)
    multiplier = Column(Float, nullable=False)
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class WQBCredential(SQLAlchemyBase):
    __tablename__ = "wqb_credentials"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    username_encrypted = Column(Text, nullable=False)
    password_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

# =============================================================================
# RL & TEMPLATE MODELS
# =============================================================================

class RLState(SQLAlchemyBase):
    __tablename__ = "rl_states"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    state_key = Column(String(200), unique=True, nullable=False)
    state_type = Column(String(50), nullable=False)
    q_value = Column(Float, default=0.0)
    visit_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    meta_data = Column(JSONB)  # Renamed from metadata to avoid conflict
    updated_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

class RLAction(SQLAlchemyBase):
    __tablename__ = "rl_actions"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    state_id = Column(Integer, ForeignKey("rl_states.id"))
    action_type = Column(String(100))
    action_params = Column(JSONB)
    reward = Column(Float)
    next_state_id = Column(Integer, ForeignKey("rl_states.id"))
    executed_at = Column(DateTime, server_default=func.now())

class Template(SQLAlchemyBase):
    __tablename__ = "templates"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    expression = Column(Text, nullable=False)
    alpha_type = Column(String(20), default='atom', nullable=False)
    template_configurations = Column(JSONB)
    recommended_region = Column(String(10))
    recommended_universe = Column(String(50))
    recommended_delay = Column(Integer, default=1)
    recommended_decay = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    total_generated = Column(Integer, default=0)
    avg_sharpe = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class TemplateVariable(SQLAlchemyBase):
    __tablename__ = "template_variables"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    variable_name = Column(String(100), nullable=False)
    config_type = Column(String(50), nullable=False)
    allowed_values = Column(JSONB)
    default_value = Column(String(200))

# =============================================================================
# IMPROVED METADATA MODELS
# =============================================================================

class DatasetMetadata(SQLAlchemyBase):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint('dataset_id', 'region', 'universe', name='uq_dataset_region_universe'),
        {'extend_existing': True}
    )
    
    # ID in create_table.sql is serial int, dataset_id is varchar.
    # We will map fields to match the SQL schema more closely.
    # Note: original model used dataset_id as PK string. SQL uses id(int) as PK.
    # We will adapt to SQL schema.
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(100), nullable=False) # unique constraint in SQL is composite
    region = Column(String(10), nullable=False)
    universe = Column(String(50), nullable=False, default="TOP3000")
    name = Column(String(200), nullable=False, default="")
    description = Column(Text)
    category = Column(String(100))
    subcategory = Column(String(100))
    
    # Metrics
    coverage = Column(Float)
    value_score = Column(Integer)
    user_count = Column(Integer)
    alpha_count = Column(Integer)
    field_count = Column(Integer)
    pyramid_multiplier = Column(Float)
    
    # Settings
    delay = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    mining_weight = Column(Float, default=1.0) # Kept from old model
    
    # New Brain Fields
    date_coverage = Column(Float)
    themes = Column(JSONB) # List of themes
    resources = Column(JSONB) # List of researchPapers
    
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Mining stats (legacy)
    alpha_success_count = Column(Integer, default=0)
    alpha_fail_count = Column(Integer, default=0)

class DataField(SQLAlchemyBase):
    __tablename__ = "datafields"
    __table_args__ = (
        UniqueConstraint('dataset_id', 'field_id', name='uq_datafield_dataset_field'),
        {'extend_existing': True}
    )
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    region = Column(String(10), nullable=False)
    universe = Column(String(50), nullable=False)
    delay = Column(Integer, default=1)
    field_id = Column(String(200), nullable=False)
    field_name = Column(String(200), nullable=False)
    field_type = Column(String(50)) # Brain "type": "VECTOR", "MATRIX", etc.
    description = Column(Text)
    
    # New Brain Fields
    category = Column(String(100))
    subcategory = Column(String(100))
    date_coverage = Column(Float)
    coverage = Column(Float)
    pyramid_multiplier = Column(Float)
    alpha_count = Column(Integer)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

# =============================================================================
# UPDATED CORE MODELS
# =============================================================================

class MiningTask(SQLAlchemyBase):
    """
    Mining Task - Maps to 'generation_tasks' in reference SQL or keeps as mining_tasks
    We will keep 'mining_tasks' for compatibility but align fields where possible.
    """
    __tablename__ = "mining_tasks"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(255), nullable=False)
    region = Column(String(50), nullable=False)
    universe = Column(String(100), nullable=False)
    
    dataset_strategy = Column(String(50), default="AUTO")
    target_datasets = Column(JSONB, default=[])
    agent_mode = Column(String(50), default="AUTONOMOUS")
    
    status = Column(String(50), default="PENDING")
    daily_goal = Column(Integer, default=4)
    progress_current = Column(Integer, default=0)
    
    # Evolution tracking
    current_iteration = Column(Integer, default=0)
    max_iterations = Column(Integer, default=10)
    
    config = Column(JSONB, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    trace_steps = relationship("TraceStep", back_populates="task", order_by="TraceStep.step_order")
    alphas = relationship("Alpha", back_populates="task")


class ExperimentRun(SQLAlchemyBase):
    __tablename__ = "experiment_runs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("mining_tasks.id"), nullable=False)

    status = Column(String(50), default="RUNNING")
    trigger_source = Column(String(50), default="API")
    celery_task_id = Column(String(100))

    config_snapshot = Column(JSONB, default={})
    prompt_version = Column(String(100))
    thresholds_version = Column(String(100))
    strategy_snapshot = Column(JSONB, default={})

    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime)
    error_message = Column(Text)

    task = relationship("MiningTask")

class TraceStep(SQLAlchemyBase):
    __tablename__ = "trace_steps"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("mining_tasks.id"), nullable=False)

    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=True)
    
    step_type = Column(String(50), nullable=False)
    step_order = Column(Integer, nullable=False)
    iteration = Column(Integer, default=1)
    input_data = Column(JSONB, default={})
    output_data = Column(JSONB, default={})
    
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(50), default="RUNNING")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    task = relationship("MiningTask", back_populates="trace_steps")
    alpha = relationship("Alpha", back_populates="trace_step", uselist=False)

class Alpha(SQLAlchemyBase):
    """
    Alpha - Maps to 'alphas' table in reference SQL.
    Significantly expanded fields.
    """
    __tablename__ = "alphas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    alpha_id = Column(String(20), unique=True, index=True)
    type = Column(String(20), default="REGULAR") # REGULAR, SUPER
    
    # Associations
    task_id = Column(Integer, ForeignKey("mining_tasks.id"), nullable=True)
    trace_step_id = Column(Integer, ForeignKey("trace_steps.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"))

    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=True)
    
    # Core Info
    expression = Column(Text, nullable=False)
    expression_hash = Column(String(64))
    author = Column(String(50))
    name = Column(String(200))
    region = Column(String(10), nullable=False)
    universe = Column(String(50), nullable=False)
    dataset_id = Column(String(50), nullable=True)
    
    # Settings
    delay = Column(Integer, default=1)
    decay = Column(Integer, default=0)
    neutralization = Column(String(50), default="NONE")
    truncation = Column(Float, default=0.08)
    instrument_type = Column(String(20), default="EQUITY")
    
    # Status
    status = Column(String(20), default="created") # created, simulated, submitted
    stage = Column(String(10), default="IS") # IS, OS
    quality_status = Column(String(50), default="PENDING") # Legacy support
    
    # Metrics (Flattened as per SQL, likely deprecated in favor of JSONB metrics)
    is_sharpe = Column(Float)
    is_turnover = Column(Float)
    is_fitness = Column(Float)
    is_returns = Column(Float)
    is_drawdown = Column(Float)
    is_margin = Column(Float)
    is_long_count = Column(Integer)
    is_short_count = Column(Integer)
    
    # New Brain Rich Metadata
    settings = Column(JSONB) # Full settings object
    tags = Column(ARRAY(String)) # List of tags (TEXT[])
    checks = Column(JSONB) # Warning/Fail details
    
    # Full Metrics Objects
    is_metrics = Column(JSONB) # In-Sample metrics object
    os_metrics = Column(JSONB) # Out-of-Sample metrics object
    
    # Dates
    date_created = Column(DateTime)
    date_modified = Column(DateTime)
    date_submitted = Column(DateTime)
    
    # Human Feedback
    human_feedback = Column(String(50), default="NONE")
    feedback_comment = Column(Text)
    
    # Context
    hypothesis = Column(Text)
    logic_explanation = Column(Text)
    fields_used = Column(JSONB, default=[])
    operators_used = Column(JSONB, default=[])
    
    metrics = Column(JSONB, default={}) 
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('alpha_id', name='uq_alpha_id'),
        {'extend_existing': True}
    )
    
    task = relationship("MiningTask", back_populates="alphas")
    trace_step = relationship("TraceStep", back_populates="alpha")


class AlphaFailure(SQLAlchemyBase):
    """
    Alpha Failure - Records failed alpha attempts for the feedback loop.
    Used by Feedback Agent to learn and improve.
    """
    __tablename__ = "alpha_failures"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("mining_tasks.id"), nullable=True)
    trace_step_id = Column(Integer, ForeignKey("trace_steps.id"), nullable=True)

    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=True)
    
    expression = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)  # SYNTAX_ERROR, FIELD_NOT_FOUND, TIMEOUT, etc.
    error_message = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    
    # For feedback analysis
    is_analyzed = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KnowledgeEntry(SQLAlchemyBase):
    __tablename__ = "knowledge_entries"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    entry_type = Column(String(50), nullable=False)
    pattern = Column(Text)
    description = Column(Text)
    meta_data = Column(JSONB, default={})
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50), default="SYSTEM")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

# Alias for compatibility if code uses OperatorPreference
class OperatorPreference(SQLAlchemyBase):
    __tablename__ = "operator_prefs" # Can be deprecated in favor of Operator/OperatorBlacklist
    __table_args__ = {'extend_existing': True}
    operator_name = Column(String(100), primary_key=True)
    status = Column(String(50), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_rate = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now())

class SystemConfig(SQLAlchemyBase):
    __tablename__ = "system_configs" # Note SQL name
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text)
    config_type = Column(String(50))
    description = Column(Text)
    updated_at = Column(DateTime, server_default=func.now())
