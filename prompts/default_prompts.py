"""Default agent prompt templates and utilities."""

import yaml
from typing import Dict, Any
from pathlib import Path


class DefaultPrompts:
    """Default agent prompt templates."""
    
    def __init__(self):
        """Initialize default prompts from YAML file."""
        self._prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts from YAML file."""
        prompts_file = Path(__file__).parent / "default_prompts.yaml"
        with open(prompts_file, 'r') as f:
            return yaml.safe_load(f)
    
    def get_enhancement_prompt(self, source: str, content: str) -> str:
        """Get enhancement prompt for default agent."""
        template = self._prompts['default_prompts']['enhancement']['template']
        return template.format(
            source=source,
            content=content
        )
    
    def get_acknowledgment_prompt(self, source: str, content_summary: str, 
                                category: str) -> str:
        """Get acknowledgment prompt."""
        template = self._prompts['default_prompts']['acknowledgment']['template']
        return template.format(
            source=source,
            content_summary=content_summary,
            category=category
        )
    
    def get_prompt_parameters(self, prompt_type: str) -> Dict[str, Any]:
        """Get parameters for a specific prompt type."""
        return self._prompts['default_prompts'].get(prompt_type, {}).get('parameters', {})