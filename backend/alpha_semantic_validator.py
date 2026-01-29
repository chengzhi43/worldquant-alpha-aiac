"""
Alpha Semantic Validator - Enhanced validation with MATRIX/VECTOR type constraints.

This module provides semantic validation beyond syntax checking:
1. Field existence validation
2. Operator existence validation  
3. MATRIX/VECTOR type constraint enforcement
4. Expression deduplication
5. Diversity scoring

P0-1: Core type/signature validation
"""

import re
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class FieldType(Enum):
    """BRAIN platform field types"""
    MATRIX = "MATRIX"  # Time-series data, supports ts_* operators
    VECTOR = "VECTOR"  # Cross-sectional/static data, supports vec_* operators
    GROUP = "GROUP"    # Grouping fields (sector, industry, etc.)
    UNKNOWN = "UNKNOWN"


@dataclass
class FieldInfo:
    """Field metadata for validation"""
    field_id: str
    field_type: FieldType = FieldType.UNKNOWN
    coverage: float = 1.0
    alpha_count: int = 0
    pyramid_multiplier: float = 1.0
    description: str = ""
    
    @classmethod
    def from_dict(cls, d: Dict) -> "FieldInfo":
        field_type_str = d.get("type", "MATRIX")
        try:
            field_type = FieldType(field_type_str.upper()) if field_type_str else FieldType.UNKNOWN
        except ValueError:
            field_type = FieldType.UNKNOWN
            
        return cls(
            field_id=d.get("id") or d.get("name", ""),
            field_type=field_type,
            coverage=d.get("coverage", 1.0) or 1.0,
            alpha_count=d.get("alpha_count", 0) or 0,
            pyramid_multiplier=d.get("pyramid_multiplier", 1.0) or 1.0,
            description=d.get("description", "")
        )


# Operators that REQUIRE time-series (MATRIX) input
TS_OPERATORS = {
    "ts_std_dev", "ts_mean", "ts_delay", "ts_corr", "ts_zscore", "ts_returns",
    "ts_product", "ts_backfill", "ts_scale", "ts_entropy", "ts_step", "ts_sum",
    "ts_co_kurtosis", "ts_decay_exp_window", "ts_av_diff", "ts_kurtosis",
    "ts_min_max_diff", "ts_arg_max", "ts_max", "ts_min_max_cps", "ts_rank",
    "ts_ir", "ts_theilsen", "ts_weighted_decay", "ts_quantile", "ts_min",
    "ts_count_nans", "ts_covariance", "ts_co_skewness", "ts_min_diff",
    "ts_decay_linear", "ts_moment", "ts_arg_min", "ts_regression", "ts_skewness",
    "ts_max_diff", "ts_median", "ts_delta", "ts_poly_regression",
    "ts_target_tvr_decay", "ts_target_tvr_delta_limit", "ts_target_tvr_hump",
    "ts_delta_limit", "ts_vector_neut", "ts_vector_proj", "ts_percentage",
    "ts_partial_corr", "ts_triple_corr", "ts_rank_gmean_amean_diff",
    "days_from_last_change", "last_diff_value", "inst_tvr", "hump_decay",
    "jump_decay", "kth_element", "hump"
}

# Operators that work with VECTOR fields
VEC_OPERATORS = {
    "vec_kurtosis", "vec_min", "vec_count", "vec_sum", "vec_skewness",
    "vec_max", "vec_avg", "vec_range", "vec_choose", "vec_powersum",
    "vec_stddev", "vec_percentage", "vec_ir", "vec_norm", "vec_filter"
}

# Group operators that require GROUP type second argument
GROUP_OPERATORS = {
    "group_min", "group_mean", "group_median", "group_max", "group_rank",
    "group_vector_proj", "group_normalize", "group_extra", "group_backfill",
    "group_scale", "group_count", "group_zscore", "group_std_dev", "group_sum",
    "group_neutralize", "group_multi_regression", "group_cartesian_product",
    "group_coalesce", "group_percentage", "group_vector_neut"
}

# Built-in group fields
BUILTIN_GROUPS = {"sector", "subindustry", "industry", "exchange", "country", "market"}


@dataclass
class SemanticValidationResult:
    """Result of semantic validation"""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Extracted info
    used_fields: Set[str] = field(default_factory=set)
    used_operators: Set[str] = field(default_factory=set)
    field_types_used: Set[str] = field(default_factory=set)
    
    # Metrics
    complexity_score: float = 0.0
    diversity_score: float = 0.0
    
    def add_error(self, msg: str):
        self.errors.append(msg)
        self.valid = False
        
    def add_warning(self, msg: str):
        self.warnings.append(msg)


class AlphaSemanticValidator:
    """
    Enhanced semantic validator for alpha expressions.
    
    Validates:
    - Field existence in dataset
    - Operator existence in platform
    - Type constraints (MATRIX vs VECTOR)
    - Coverage warnings
    """
    
    def __init__(
        self,
        fields: Optional[List[Dict]] = None,
        operators: Optional[List[str]] = None,
        strict_field_check: bool = True,
        strict_type_check: bool = True
    ):
        """
        Initialize validator with dataset context.
        
        Args:
            fields: List of field dicts with id, type, coverage, etc.
            operators: List of allowed operator names
            strict_field_check: If True, unknown fields are errors; if False, warnings
            strict_type_check: If True, type mismatches are errors; if False, warnings
        """
        self.strict_field_check = strict_field_check
        self.strict_type_check = strict_type_check
        
        # Build field lookup
        self.field_map: Dict[str, FieldInfo] = {}
        if fields:
            for f in fields:
                info = FieldInfo.from_dict(f)
                if info.field_id:
                    self.field_map[info.field_id.lower()] = info
        
        # Build operator set
        self.allowed_operators: Set[str] = set()
        if operators:
            self.allowed_operators = {op.lower() for op in operators}
        else:
            # Default: allow all known operators
            self.allowed_operators = TS_OPERATORS | VEC_OPERATORS | GROUP_OPERATORS
            
        # Regex patterns for parsing
        self._field_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
        self._func_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
        
    def validate(self, expression: str) -> SemanticValidationResult:
        """
        Perform semantic validation on an expression.
        
        Args:
            expression: Alpha expression string
            
        Returns:
            SemanticValidationResult with errors, warnings, and extracted info
        """
        result = SemanticValidationResult()
        
        if not expression or not expression.strip():
            result.add_error("Empty expression")
            return result
            
        expression = expression.strip()
        
        # 1. Extract operators used
        operators_used = self._extract_operators(expression)
        result.used_operators = operators_used
        
        # 2. Extract fields used (identifiers not matching operators)
        fields_used = self._extract_fields(expression, operators_used)
        result.used_fields = fields_used
        
        # 3. Validate operators exist
        for op in operators_used:
            op_lower = op.lower()
            if self.allowed_operators and op_lower not in self.allowed_operators:
                # Check against all known operators
                all_known = TS_OPERATORS | VEC_OPERATORS | GROUP_OPERATORS
                if op_lower not in all_known:
                    result.add_error(f"Unknown operator: {op}")
                    
        # 4. Validate fields exist and collect type info
        matrix_fields = set()
        vector_fields = set()
        unknown_fields = set()
        
        for field_id in fields_used:
            field_lower = field_id.lower()
            
            # Skip built-in groups
            if field_lower in BUILTIN_GROUPS:
                continue
                
            # Skip numeric literals and keywords
            if field_lower in {"true", "false", "nan", "inf"}:
                continue
                
            if field_lower in self.field_map:
                info = self.field_map[field_lower]
                result.field_types_used.add(info.field_type.value)
                
                if info.field_type == FieldType.MATRIX:
                    matrix_fields.add(field_id)
                elif info.field_type == FieldType.VECTOR:
                    vector_fields.add(field_id)
                    
                # Coverage warning
                if info.coverage < 0.5:
                    result.add_warning(f"Low coverage field: {field_id} ({info.coverage:.1%})")
            else:
                unknown_fields.add(field_id)
                
        # Handle unknown fields
        for field_id in unknown_fields:
            msg = f"Field not found in dataset: {field_id}"
            if self.strict_field_check:
                result.add_error(msg)
            else:
                result.add_warning(msg)
                
        # 5. Type constraint validation
        type_errors = self._validate_type_constraints(
            expression, operators_used, matrix_fields, vector_fields
        )
        for err in type_errors:
            if self.strict_type_check:
                result.add_error(err)
            else:
                result.add_warning(err)
                
        # 6. Calculate complexity score
        result.complexity_score = len(operators_used) + len(fields_used) * 0.5
        
        return result
    
    def _extract_operators(self, expression: str) -> Set[str]:
        """Extract function/operator names from expression"""
        operators = set()
        for match in self._func_pattern.finditer(expression):
            operators.add(match.group(1))
        return operators
    
    def _extract_fields(self, expression: str, operators: Set[str]) -> Set[str]:
        """Extract field identifiers (non-operator identifiers)"""
        fields = set()
        op_lower = {op.lower() for op in operators}
        
        # Keywords and built-ins to skip
        skip = {
            "true", "false", "nan", "inf",
            "sector", "subindustry", "industry", "exchange", "country", "market",
            "std", "k", "mode", "lag", "rettype", "filter", "scale", "rate",
            "constant", "percentage", "driver", "sigma", "lower", "upper",
            "target", "dest", "event", "sensitivity", "force", "h", "t", "period",
            "stddev", "factor", "usetd", "limit", "gaussian", "uniform", "cauchy",
            "buckets", "range", "nth", "precise", "longscale", "shortscale"
        }
        
        for match in self._field_pattern.finditer(expression):
            ident = match.group(1)
            ident_lower = ident.lower()
            
            # Skip if it's an operator
            if ident_lower in op_lower:
                continue
                
            # Skip keywords/params
            if ident_lower in skip:
                continue
                
            # Skip pure numbers (shouldn't match pattern but just in case)
            if ident.isdigit():
                continue
                
            fields.add(ident)
            
        return fields
    
    def _validate_type_constraints(
        self,
        expression: str,
        operators: Set[str],
        matrix_fields: Set[str],
        vector_fields: Set[str]
    ) -> List[str]:
        """
        Validate that field types match operator requirements.
        
        Key rules:
        - ts_* operators work best with MATRIX fields (time-series)
        - vec_* operators require VECTOR fields
        - Using VECTOR fields with ts_* may cause issues
        """
        errors = []
        
        expr_lower = expression.lower()
        
        for op in operators:
            op_lower = op.lower()
            
            # Check ts_* operators with VECTOR fields
            if op_lower in TS_OPERATORS:
                # Look for vec_ prefix fields being passed to ts_ functions
                # This is a heuristic - we look for vector field names near ts_ calls
                for vf in vector_fields:
                    # Simple heuristic: if vector field appears right after ts_xxx(
                    pattern = rf'{op_lower}\s*\(\s*{re.escape(vf.lower())}'
                    if re.search(pattern, expr_lower):
                        errors.append(
                            f"Type mismatch: VECTOR field '{vf}' used as first arg of time-series operator '{op}'. "
                            f"Consider using vec_* wrapper or MATRIX equivalent."
                        )
                        
            # Check vec_* operators - they expect aggregation over vector dimensions
            if op_lower in VEC_OPERATORS:
                # vec_* operators on MATRIX fields is actually fine (aggregates across vector dim)
                pass
                
        return errors


def compute_expression_hash(expression: str) -> str:
    """
    Compute a normalized hash for expression deduplication.
    
    Normalizes:
    - Whitespace
    - Case (for operators)
    - Numeric precision
    """
    # Normalize whitespace
    normalized = " ".join(expression.split())
    
    # Normalize operator case
    for op in TS_OPERATORS | VEC_OPERATORS | GROUP_OPERATORS:
        pattern = re.compile(re.escape(op), re.IGNORECASE)
        normalized = pattern.sub(op.lower(), normalized)
        
    # Hash
    return hashlib.md5(normalized.encode()).hexdigest()


def compute_structural_similarity(expr1: str, expr2: str) -> float:
    """
    Compute structural similarity between two expressions.
    
    Based on:
    - Operator n-gram overlap
    - Field Jaccard similarity
    
    Returns: Similarity score 0.0 to 1.0
    """
    validator = AlphaSemanticValidator()
    
    # Extract operators
    ops1 = validator._extract_operators(expr1)
    ops2 = validator._extract_operators(expr2)
    
    # Extract fields
    fields1 = validator._extract_fields(expr1, ops1)
    fields2 = validator._extract_fields(expr2, ops2)
    
    # Operator overlap (Jaccard)
    if ops1 or ops2:
        op_jaccard = len(ops1 & ops2) / len(ops1 | ops2) if (ops1 | ops2) else 0
    else:
        op_jaccard = 1.0
        
    # Field overlap (Jaccard)
    if fields1 or fields2:
        field_jaccard = len(fields1 & fields2) / len(fields1 | fields2) if (fields1 | fields2) else 0
    else:
        field_jaccard = 1.0
        
    # Weighted combination
    return 0.4 * op_jaccard + 0.6 * field_jaccard


class ExpressionDeduplicator:
    """
    Track seen expressions and detect duplicates.
    
    P0-2: Deduplication gate before simulation
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.seen_hashes: Set[str] = set()
        self.seen_expressions: List[str] = []
        self.similarity_threshold = similarity_threshold
        
    def is_duplicate(self, expression: str) -> Tuple[bool, Optional[str]]:
        """
        Check if expression is a duplicate.
        
        Returns:
            (is_duplicate, reason)
        """
        expr_hash = compute_expression_hash(expression)
        
        # Exact hash match
        if expr_hash in self.seen_hashes:
            return True, "Exact duplicate (hash match)"
            
        # Structural similarity check (expensive, limit to recent)
        recent = self.seen_expressions[-100:]  # Only check last 100
        for seen in recent:
            sim = compute_structural_similarity(expression, seen)
            if sim >= self.similarity_threshold:
                return True, f"Structurally similar ({sim:.1%}) to: {seen[:50]}..."
                
        return False, None
        
    def add(self, expression: str):
        """Add expression to seen set"""
        expr_hash = compute_expression_hash(expression)
        self.seen_hashes.add(expr_hash)
        self.seen_expressions.append(expression)
        
    def clear(self):
        """Clear all seen expressions"""
        self.seen_hashes.clear()
        self.seen_expressions.clear()


# =============================================================================
# P1-4: Diversity scoring for batch evaluation
# =============================================================================

def compute_batch_diversity(expressions: List[str]) -> float:
    """
    Compute diversity score for a batch of expressions.
    
    Higher is better (more diverse).
    
    Returns: 0.0 to 1.0
    """
    if len(expressions) <= 1:
        return 1.0
        
    # Pairwise similarity
    similarities = []
    for i in range(len(expressions)):
        for j in range(i + 1, len(expressions)):
            sim = compute_structural_similarity(expressions[i], expressions[j])
            similarities.append(sim)
            
    if not similarities:
        return 1.0
        
    # Diversity = 1 - average similarity
    avg_sim = sum(similarities) / len(similarities)
    return 1.0 - avg_sim


# =============================================================================
# Integration helper for node_validate
# =============================================================================

def validate_alpha_semantically(
    expression: str,
    fields: List[Dict],
    operators: Optional[List[str]] = None,
    strict: bool = False
) -> Dict[str, Any]:
    """
    Convenience function for semantic validation.
    
    Args:
        expression: Alpha expression
        fields: List of field dicts from state
        operators: Optional list of allowed operators
        strict: If True, use strict checking
        
    Returns:
        Dict with 'valid', 'errors', 'warnings', 'used_fields', 'used_operators'
    """
    validator = AlphaSemanticValidator(
        fields=fields,
        operators=operators,
        strict_field_check=strict,
        strict_type_check=strict
    )
    
    result = validator.validate(expression)
    
    return {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "used_fields": list(result.used_fields),
        "used_operators": list(result.used_operators),
        "field_types": list(result.field_types_used),
        "complexity_score": result.complexity_score
    }
