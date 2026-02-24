"""
LLM client abstraction - wraps OpenAI-compatible APIs.
"""

from openai import OpenAI
from core.config import config


class LLMClient:
    """Unified LLM client supporting any OpenAI-compatible API."""

    def __init__(self):
        api_key = config.get("llm.api_key", "")
        base_url = config.get("llm.base_url", "")

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        self.client = OpenAI(**kwargs)
        self.model = config.get("llm.model", "gpt-4o-mini")
        self.temperature = config.get("llm.temperature", 0.7)
        self.max_tokens = config.get("llm.max_tokens", 2048)

    def chat(self, messages: list, tools: list = None, tool_choice: str = "auto") -> dict:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts (role, content, etc.)
            tools: Optional list of tool/function definitions
            tool_choice: "auto", "none", or "required"
            
        Returns:
            The API response message object.
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message
