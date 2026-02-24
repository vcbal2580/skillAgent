"""
Conversation context manager - manages message history with truncation.
"""

from typing import Optional
from core.config import config


class ContextManager:
    """Manages conversation history and context window."""

    def __init__(self, system_prompt: str = None):
        self.system_prompt = system_prompt or config.get("agent.system_prompt", "You are a helpful assistant.")
        self.max_history = config.get("agent.max_history", 20)
        self.messages: list[dict] = []

    def get_messages(self) -> list[dict]:
        """Get full message list including system prompt."""
        system_msg = {"role": "system", "content": self.system_prompt}
        return [system_msg] + self.messages

    def add_user_message(self, content: str):
        """Add a user message and trim history if needed."""
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant_message(self, content: str):
        """Add an assistant text message."""
        self.messages.append({"role": "assistant", "content": content})
        self._trim()

    def add_assistant_tool_calls(self, message):
        """Add an assistant message that contains tool calls (from API response)."""
        # Convert the OpenAI message object to a dict for storage
        msg_dict = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        self.messages.append(msg_dict)

    def add_tool_result(self, tool_call_id: str, name: str, content: str):
        """Add a tool/function result message."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })

    def clear(self):
        """Clear conversation history."""
        self.messages.clear()

    def get_summary_context(self) -> str:
        """Get a text summary of recent conversation for knowledge retrieval context."""
        recent = self.messages[-4:]  # Last 2 rounds
        parts = []
        for msg in recent:
            if msg["role"] in ("user", "assistant") and msg.get("content"):
                parts.append(msg["content"])
        return "\n".join(parts)

    def _trim(self):
        """Trim history to max_history messages (preserving pairs)."""
        max_msgs = self.max_history * 2  # Each round = user + assistant
        if len(self.messages) > max_msgs:
            self.messages = self.messages[-max_msgs:]
