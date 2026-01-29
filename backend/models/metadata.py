"""
Metadata Models - Dataset and field metadata

Contains DatasetMetadata, DataField, Operator, and related models.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func

from backend.database import SQLAlchemyBase


class DatasetMetadata(SQLAlchemyBase):
    """
    Dataset Metadata - Information about BRAIN datasets.
    """
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint('dataset_id', 'region', 'universe', name='uq_dataset_region_universe'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(100), nullable=False)
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
    mining_weight = Column(Float, default=1.0)
    
    # Brain Fields
    date_coverage = Column(Float)
    themes = Column(JSONB)
    resources = Column(JSONB)
    
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Mining stats
    alpha_success_count = Column(Integer, default=0)
    alpha_fail_count = Column(Integer, default=0)


class DataField(SQLAlchemyBase):
    """
    Data Field - Information about fields within datasets.
    
    Real API structure from get_datafields:
    - id: field ID (e.g., "assets", "close")
    - description: field description
    - dataset: nested object {id, name}
    - category: nested object {id, name}
    - subcategory: nested object {id, name}
    - region, delay, universe
    - type: MATRIX, VECTOR, GROUP
    - dateCoverage, coverage
    - userCount, alphaCount
    - pyramidMultiplier
    - themes: list of theme objects
    """
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
    field_type = Column(String(50))  # VECTOR, MATRIX, GROUP
    description = Column(Text)
    
    # Category info (API returns nested objects, we store IDs)
    category = Column(String(100))       # category.id
    category_name = Column(String(200))  # category.name
    subcategory = Column(String(100))    # subcategory.id
    subcategory_name = Column(String(200))  # subcategory.name
    
    # Metrics from API
    date_coverage = Column(Float)        # dateCoverage
    coverage = Column(Float)             # coverage
    pyramid_multiplier = Column(Float)   # pyramidMultiplier
    user_count = Column(Integer)         # userCount
    alpha_count = Column(Integer)        # alphaCount
    
    # Themes (stored as JSON)
    themes = Column(JSONB, default=[])
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Operator(SQLAlchemyBase):
    """
    Operator - BRAIN platform operators.
    
    Real API structure from get_operators:
    - name: operator name (e.g., "ts_rank", "add")
    - category: operator category (e.g., "Arithmetic", "Time Series")
    - scope: list of scopes ["COMBO", "REGULAR", "SELECTION"]
    - definition: usage definition (e.g., "ts_rank(x, d)")
    - description: detailed description
    - documentation: documentation URL path (e.g., "/operators/ts_rank")
    - level: operator level (e.g., "ALL")
    """
    __tablename__ = "operators"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(100))
    description = Column(Text)
    definition = Column(Text)
    scope = Column(ARRAY(String))
    level = Column(String(50))
    documentation = Column(String(200))  # API returns this field
    syntax = Column(Text)  # Legacy field
    param_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class OperatorBlacklist(SQLAlchemyBase):
    """
    Operator Blacklist - Operators that should not be used.
    """
    __tablename__ = "operator_blacklist"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    operator_name = Column(String(100), unique=True, nullable=False)
    error_message = Column(Text)
    first_seen_at = Column(DateTime, server_default=func.now())
    hit_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)


class Region(SQLAlchemyBase):
    """
    Region - Market regions.
    """
    __tablename__ = "regions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Universe(SQLAlchemyBase):
    """
    Universe - Stock universes.
    """
    __tablename__ = "universes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"))
    code = Column(String(50), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Neutralization(SQLAlchemyBase):
    """
    Neutralization - Neutralization methods.
    """
    __tablename__ = "neutralizations"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class PyramidMultiplier(SQLAlchemyBase):
    """
    Pyramid Multiplier - Multipliers by category/region.
    """
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


class Template(SQLAlchemyBase):
    """
    Template - Alpha expression templates.
    """
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
    """
    Template Variable - Variables in templates.
    """
    __tablename__ = "template_variables"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    variable_name = Column(String(100), nullable=False)
    config_type = Column(String(50), nullable=False)
    allowed_values = Column(JSONB)
    default_value = Column(String(200))
