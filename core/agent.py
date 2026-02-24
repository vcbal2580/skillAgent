"""
Agent orchestrator - the brain that coordinates LLM, skills, and context.
"""

import json
from core.llm import LLMClient
from core.context import ContextManager
from core.config import config
from skills.registry import SkillRegistry


class Agent:
    """Main agent that orchestrates LLM calls with tool/skill execution."""

    def __init__(self):
        self.llm = LLMClient()
        self.context = ContextManager()
        self.registry = SkillRegistry()
        self.max_tool_calls = config.get("agent.max_tool_calls", 5)

    def register_default_skills(self):
        """Register all built-in skills."""
        from skills.web_search import WebSearchSkill
        from skills.knowledge_skill import KnowledgeSkill
        from skills.datetime_skill import DateTimeSkill

        self.registry.register(WebSearchSkill())
        self.registry.register(KnowledgeSkill())
        self.registry.register(DateTimeSkill())

    def chat(self, user_input: str) -> str:
        """
        Process user input and return agent response.
        Handles multi-turn tool calling automatically.
        """
        self.context.add_user_message(user_input)

        tools = self.registry.get_openai_tools()
        iterations = 0

        while iterations < self.max_tool_calls:
            iterations += 1

            # Call LLM
            response_msg = self.llm.chat(
                messages=self.context.get_messages(),
                tools=tools if tools else None,
            )

            # If no tool calls, we have the final answer
            if not response_msg.tool_calls:
                answer = response_msg.content or ""
                self.context.add_assistant_message(answer)
                return answer

            # Process tool calls
            self.context.add_assistant_tool_calls(response_msg)

            for tool_call in response_msg.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                # Execute the skill
                result = self.registry.execute(func_name, func_args)

                # Add result to context
                self.context.add_tool_result(
                    tool_call_id=tool_call.id,
                    name=func_name,
                    content=str(result),
                )

        # If we exhausted tool call iterations, get a final response without tools
        response_msg = self.llm.chat(
            messages=self.context.get_messages(),
            tools=None,
        )
        answer = response_msg.content or "抱歉，处理过程中遇到问题，请重试。"
        self.context.add_assistant_message(answer)
        return answer

    def reset(self):
        """Reset conversation history."""
        self.context.clear()
