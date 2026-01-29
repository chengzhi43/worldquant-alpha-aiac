"""
Prompt Loader for loading prompts from YAML configuration.

Based on RD-Agent's prompt loading pattern:
- Loads prompts from YAML files
- Supports Jinja2 templating
- Falls back to Python defaults if YAML not found

Usage:
    loader = PromptLoader()
    system_prompt = loader.get("hypothesis_generation", "system")
    output_format = loader.get("hypothesis_generation", "output_format")
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from jinja2 import Template


class PromptLoader:
    """
    Load and manage prompts from YAML configuration files.
    
    Follows RD-Agent's pattern of externalized prompt configuration,
    allowing easy modification without code changes.
    """
    
    _instance: Optional['PromptLoader'] = None
    _prompts: Dict[str, Any] = {}
    
    def __new__(cls) -> 'PromptLoader':
        """Singleton pattern - only one loader instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_prompts()
        return cls._instance
    
    def _load_prompts(self) -> None:
        """Load prompts from YAML file."""
        yaml_path = Path(__file__).parent / "prompts.yaml"
        
        if yaml_path.exists():
            with yaml_path.open(encoding="utf-8") as f:
                self._prompts = yaml.safe_load(f) or {}
        else:
            self._prompts = {}
    
    def reload(self) -> None:
        """Reload prompts from file (useful for hot-reloading)."""
        self._load_prompts()
    
    def get(self, category: str, key: str, default: Optional[str] = None) -> str:
        """
        Get a prompt by category and key.
        
        Args:
            category: Prompt category (e.g., "hypothesis_generation")
            key: Key within category (e.g., "system", "output_format")
            default: Default value if not found
            
        Returns:
            The prompt string, or default if not found
        """
        category_data = self._prompts.get(category, {})
        if isinstance(category_data, dict):
            return category_data.get(key, default or "")
        return default or ""
    
    def get_rendered(
        self,
        category: str,
        key: str,
        context: Optional[Dict[str, Any]] = None,
        default: Optional[str] = None
    ) -> str:
        """
        Get a prompt rendered with Jinja2 template variables.
        
        Args:
            category: Prompt category
            key: Key within category
            context: Variables to inject into the template
            default: Default value if not found
            
        Returns:
            The rendered prompt string
        """
        template_str = self.get(category, key, default)
        if not template_str:
            return default or ""
        
        try:
            template = Template(template_str)
            return template.render(context or {})
        except Exception as e:
            # Fall back to unrendered if template fails
            return template_str
    
    def get_all(self, category: str) -> Dict[str, str]:
        """
        Get all prompts in a category.
        
        Args:
            category: Prompt category
            
        Returns:
            Dictionary of all prompts in the category
        """
        category_data = self._prompts.get(category, {})
        if isinstance(category_data, dict):
            return {k: v for k, v in category_data.items() if isinstance(v, str)}
        return {}
    
    def list_categories(self) -> list:
        """List all available prompt categories."""
        return list(self._prompts.keys())
    
    def get_output_schema(self, category: str) -> str:
        """
        Get the output format/schema for a category.
        
        Convenience method since output formats are commonly needed.
        """
        return self.get(category, "output_format", "")
    
    def get_system_prompt(self, category: str) -> str:
        """
        Get the system prompt for a category.
        
        Convenience method since system prompts are commonly needed.
        """
        return self.get(category, "system", "")


# Global instance for convenience
_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get the global prompt loader instance."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader


def get_prompt(category: str, key: str, default: Optional[str] = None) -> str:
    """
    Convenience function to get a prompt.
    
    Args:
        category: Prompt category
        key: Key within category
        default: Default value if not found
    """
    return get_prompt_loader().get(category, key, default)


def get_rendered_prompt(
    category: str,
    key: str,
    context: Optional[Dict[str, Any]] = None,
    default: Optional[str] = None
) -> str:
    """
    Convenience function to get a rendered prompt.
    
    Args:
        category: Prompt category
        key: Key within category
        context: Template variables
        default: Default value if not found
    """
    return get_prompt_loader().get_rendered(category, key, context, default)


# Exports
__all__ = [
    "PromptLoader",
    "get_prompt_loader",
    "get_prompt",
    "get_rendered_prompt",
]
