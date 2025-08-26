"""
Prompts module - Contains prompt templates for agents.

This module houses all prompt templates used by agents, organized by
agent type and use case for easy management and versioning.
"""

from .sales_prompts import SalesPrompts
from .default_prompts import DefaultPrompts

__all__ = [
    "SalesPrompts",
    "DefaultPrompts"
]