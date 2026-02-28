"""
Base skill class - all skills must inherit from this.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """
    Abstract base class for all agent skills.
    
    To create a new skill:
    1. Inherit from BaseSkill
    2. Set name, description
    3. Define parameters (OpenAI function calling schema)
    4. Implement execute()
    
    Example:
        class MySkill(BaseSkill):
            name = "my_skill"
            description = "Does something useful"
            parameters = {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "The input"}
                },
                "required": ["input"]
            }
            
            def execute(self, **kwargs) -> str:
                return f"Result: {kwargs['input']}"
    """

    # Skill metadata - override in subclasses
    name: str = ""
    description: str = ""
    parameters: dict = {"type": "object", "properties": {}}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the skill with the given parameters.
        
        Args:
            **kwargs: Parameters matching the schema defined in `parameters`
            
        Returns:
            A string result to be sent back to the LLM
        """
        pass

    def get_tool_definition(self) -> dict:
        """Get the OpenAI function-calling tool definition.

        The base definition is built from the class attributes, then
        language-specific prompt overrides from prompts/<lang>.yaml are
        merged in via prompt_loader so LLM-facing text reflects the active
        language without touching skill logic.
        """
        from core.prompt_loader import overlay
        base = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
        return overlay(self.name, base)
