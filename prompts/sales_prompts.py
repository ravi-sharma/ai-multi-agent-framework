"""Sales agent prompt templates and utilities."""

import yaml
from typing import Dict, Any
from pathlib import Path


class SalesPrompts:
    """Sales agent prompt templates."""
    
    def __init__(self):
        """Initialize sales prompts from YAML file."""
        self._prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts from YAML file."""
        prompts_file = Path(__file__).parent / "sales_prompts.yaml"
        with open(prompts_file, 'r') as f:
            return yaml.safe_load(f)
    
    def get_customer_extraction_prompt(self, subject: str, sender: str, body: str) -> str:
        """Get customer extraction prompt."""
        template = self._prompts['sales_prompts']['customer_extraction']['template']
        return template.format(
            subject=subject,
            sender=sender,
            body=body[:1000] + "..." if len(body) > 1000 else body
        )
    
    def get_intent_analysis_prompt(self, customer_email: str, company_name: str, 
                                 subject: str, body: str) -> str:
        """Get intent analysis prompt."""
        template = self._prompts['sales_prompts']['intent_analysis']['template']
        return template.format(
            customer_email=customer_email,
            company_name=company_name or "Unknown",
            subject=subject,
            body=body
        )
    
    def get_notes_generation_prompt(self, customer_email: str, company_name: str,
                                  industry: str, subject: str, body: str,
                                  primary_intent: str, customer_problems: list,
                                  urgency_level: str) -> str:
        """Get notes generation prompt."""
        template = self._prompts['sales_prompts']['notes_generation']['template']
        return template.format(
            customer_email=customer_email,
            company_name=company_name or "Unknown",
            industry=industry or "Unknown",
            subject=subject,
            body=body,
            primary_intent=primary_intent,
            customer_problems=customer_problems,
            urgency_level=urgency_level
        )
    
    def get_follow_up_email_prompt(self, customer_name: str, customer_email: str,
                                 company_name: str, original_subject: str,
                                 customer_problem: str, proposed_solution: str,
                                 urgency_level: str) -> str:
        """Get follow-up email generation prompt."""
        template = self._prompts['sales_prompts']['follow_up_email']['template']
        return template.format(
            customer_name=customer_name or "Valued Customer",
            customer_email=customer_email,
            company_name=company_name or "your organization",
            original_subject=original_subject,
            customer_problem=customer_problem,
            proposed_solution=proposed_solution,
            urgency_level=urgency_level
        )
    
    def get_prompt_parameters(self, prompt_type: str) -> Dict[str, Any]:
        """Get parameters for a specific prompt type."""
        return self._prompts['sales_prompts'].get(prompt_type, {}).get('parameters', {})