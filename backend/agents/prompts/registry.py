"""
Prompt template registry for dynamic selection.

Enables runtime selection and customization of prompt templates.
Supports both Python-defined and YAML-loaded prompts.
"""

from typing import Callable, Optional, Dict, Any

from backend.agents.prompts.generation import (
    ALPHA_GENERATION_SYSTEM,
    build_alpha_generation_prompt,
)
from backend.agents.prompts.hypothesis import (
    HYPOTHESIS_SYSTEM,
    DISTILL_SYSTEM,
    build_hypothesis_prompt,
    build_distill_prompt,
)
from backend.agents.prompts.validation import (
    SELF_CORRECT_SYSTEM,
    OPTIMIZATION_SYSTEM,
    build_self_correct_prompt,
    build_optimization_prompt,
)
from backend.agents.prompts.analysis import (
    ROUND_ANALYSIS_SYSTEM,
    FEEDBACK_GENERATION_SYSTEM,
    build_round_analysis_prompt,
    build_feedback_prompt,
)
from backend.agents.prompts.loader import get_prompt_loader


class PromptRegistry:
    """
    Registry for prompt templates, enabling runtime selection and customization.
    
    Supports two modes:
    1. Python-defined prompts (default, for type safety and IDE support)
    2. YAML-loaded prompts (for easy customization without code changes)
    
    The `prefer_yaml` flag controls which source is used.
    """
    
    # Python-defined system prompts (default)
    _system_prompts = {
        "alpha_generation": ALPHA_GENERATION_SYSTEM,
        "hypothesis": HYPOTHESIS_SYSTEM,
        "distill": DISTILL_SYSTEM,
        "self_correct": SELF_CORRECT_SYSTEM,
        "optimization": OPTIMIZATION_SYSTEM,
        "round_analysis": ROUND_ANALYSIS_SYSTEM,
        "feedback_generation": FEEDBACK_GENERATION_SYSTEM,
    }
    
    # Mapping from registry names to YAML categories
    _yaml_category_mapping = {
        "alpha_generation": "alpha_generation",
        "hypothesis": "hypothesis_generation",
        "distill": "hypothesis_generation",  # Part of hypothesis category
        "self_correct": "self_correction",
        "optimization": "optimization",
        "round_analysis": "round_analysis",
        "feedback_generation": "feedback_generation",
    }
    
    # Python-defined user prompt builders
    _user_prompt_builders = {
        "alpha_generation": build_alpha_generation_prompt,
        "hypothesis": build_hypothesis_prompt,
        "distill": build_distill_prompt,
        "self_correct": build_self_correct_prompt,
        "optimization": build_optimization_prompt,
        "round_analysis": build_round_analysis_prompt,
        "feedback_generation": build_feedback_prompt,
    }
    
    # Configuration
    _prefer_yaml: bool = False  # Default to Python-defined for type safety
    
    @classmethod
    def set_prefer_yaml(cls, prefer: bool) -> None:
        """
        Set whether to prefer YAML-loaded prompts over Python-defined ones.
        
        Args:
            prefer: If True, try YAML first; if False (default), use Python
        """
        cls._prefer_yaml = prefer
    
    @classmethod
    def get_system_prompt(cls, prompt_type: str) -> str:
        """
        Get system prompt by type.
        
        Args:
            prompt_type: Type of prompt (e.g., "alpha_generation", "hypothesis")
            
        Returns:
            System prompt string
        """
        if cls._prefer_yaml:
            yaml_category = cls._yaml_category_mapping.get(prompt_type, prompt_type)
            loader = get_prompt_loader()
            yaml_prompt = loader.get(yaml_category, "system")
            if yaml_prompt:
                return yaml_prompt
        
        return cls._system_prompts.get(prompt_type, "")
    
    @classmethod
    def get_user_prompt_builder(cls, prompt_type: str) -> Optional[Callable]:
        """
        Get user prompt builder function by type.
        
        Args:
            prompt_type: Type of prompt
            
        Returns:
            Builder function or None
        """
        return cls._user_prompt_builders.get(prompt_type)
    
    @classmethod
    def get_output_format(cls, prompt_type: str) -> str:
        """
        Get output format/schema for a prompt type.
        
        Args:
            prompt_type: Type of prompt
            
        Returns:
            Output format string (JSON schema)
        """
        yaml_category = cls._yaml_category_mapping.get(prompt_type, prompt_type)
        loader = get_prompt_loader()
        return loader.get(yaml_category, "output_format", "")
    
    @classmethod
    def register_system_prompt(cls, name: str, prompt: str) -> None:
        """
        Register a custom system prompt.
        
        Args:
            name: Name for the prompt
            prompt: Prompt content
        """
        cls._system_prompts[name] = prompt
    
    @classmethod
    def register_user_prompt_builder(cls, name: str, builder: Callable) -> None:
        """
        Register a custom user prompt builder.
        
        Args:
            name: Name for the builder
            builder: Builder function
        """
        cls._user_prompt_builders[name] = builder
    
    @classmethod
    def register_yaml_mapping(cls, registry_name: str, yaml_category: str) -> None:
        """
        Register a mapping from registry name to YAML category.
        
        Args:
            registry_name: Name used in registry
            yaml_category: Category name in YAML file
        """
        cls._yaml_category_mapping[registry_name] = yaml_category
    
    @classmethod
    def list_available(cls) -> Dict[str, bool]:
        """
        List all available prompt types and their sources.
        
        Returns:
            Dict mapping prompt type to whether it has a YAML version
        """
        loader = get_prompt_loader()
        yaml_categories = set(loader.list_categories())
        
        result = {}
        for name in cls._system_prompts.keys():
            yaml_cat = cls._yaml_category_mapping.get(name, name)
            result[name] = yaml_cat in yaml_categories
        
        return result
    
    @classmethod
    def get_hypothesis_specification(cls) -> str:
        """
        Get the hypothesis specification guidelines.
        
        This provides standards for generating quality hypotheses.
        """
        loader = get_prompt_loader()
        return loader.get("hypothesis_specification", "", 
            default="""
            1. The hypothesis should be precise, testable, and directly actionable.
            2. Each hypothesis should focus on a single direction per experiment.
            3. The hypothesis should be informed by previous experiment results.
            4. Consider the expected market behavior or inefficiency.
            """)
    
    @classmethod
    def get_knowledge_format(cls) -> Dict[str, str]:
        """
        Get the knowledge transfer format templates.
        
        Returns:
            Dict with "rule_template" and "pattern_template"
        """
        loader = get_prompt_loader()
        knowledge_config = loader.get_all("knowledge_format")
        
        if not knowledge_config:
            # Default formats
            return {
                "rule_template": "If [observable condition], then [expected outcome or recommended action].",
                "pattern_template": "Pattern: [name]\nObservation: [what]\nFrequency: [how often]\nRecommendation: [action]"
            }
        
        return knowledge_config
