"""
Skill registry - manages skill registration and dispatch.
"""

from typing import Any
from skills.base import BaseSkill


class SkillRegistry:
    """Central registry for all agent skills."""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        """Register a skill instance."""
        if not skill.name:
            raise ValueError(f"Skill {type(skill).__name__} must have a name")
        self._skills[skill.name] = skill

    def unregister(self, name: str):
        """Remove a skill by name."""
        self._skills.pop(name, None)

    def get(self, name: str) -> BaseSkill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def execute(self, name: str, kwargs: dict) -> str:
        """Execute a skill by name with arguments."""
        skill = self._skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'"
        try:
            return skill.execute(**kwargs)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    def get_openai_tools(self) -> list[dict]:
        """Get all skills as OpenAI tool definitions."""
        return [skill.get_tool_definition() for skill in self._skills.values()]

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())
