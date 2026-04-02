"""
Agent orchestrator - the brain that coordinates LLM, skills, and context.
Supports multimodal input: text, image (vision), audio (STT), and documents.
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
        from skills.weather_skill import WeatherSkill
        from skills.divination_skill import DivinationSkill
        from skills.tarot_career_skill import TarotCareerSkill
        from skills.lucky_today_skill import LuckyTodaySkill
        from skills.almanac_skill import AlmanacSkill
        from skills.document_skill import DocumentSkill
        from skills.wecom_notify_skill import WeComNotifySkill
        from skills.git_summary_skill import GitSummarySkill
        from skills.news_workflow_skill import NewsWorkflowSkill
        from skills.web_scrape_skill import WebScrapeSkill
        from skills.page_generate_skill import PageGenerateSkill
        from skills.pdf_export_skill import PDFExportSkill
        from skills.workflow_dashboard_skill import WorkflowDashboardSkill
        from skills.research_workflow_skill import ResearchWorkflowSkill

        self.registry.register(WebSearchSkill())
        self.registry.register(KnowledgeSkill())
        self.registry.register(DateTimeSkill())
        self.registry.register(WeatherSkill())
        self.registry.register(DivinationSkill())
        self.registry.register(TarotCareerSkill())
        self.registry.register(LuckyTodaySkill())
        self.registry.register(AlmanacSkill())
        self.registry.register(DocumentSkill())
        self.registry.register(WeComNotifySkill())
        self.registry.register(GitSummarySkill())
        self.registry.register(NewsWorkflowSkill())
        self.registry.register(WebScrapeSkill())
        self.registry.register(PageGenerateSkill())
        self.registry.register(PDFExportSkill())
        self.registry.register(WorkflowDashboardSkill())
        self.registry.register(ResearchWorkflowSkill())

    # ------------------------------------------------------------------
    # Multimodal entry points
    # ------------------------------------------------------------------

    def chat_with_image(self, user_input: str, image_source: str) -> str:
        """Process text + image input and return agent response.

        Args:
            user_input: The text prompt from the user.
            image_source: URL or local file path of the image.
        """
        self.context.add_user_message(user_input)
        tools = self.registry.get_openai_tools()

        # First call uses vision model with image attached
        response_msg = self.llm.chat_with_image(
            messages=self.context.get_messages(),
            image_source=image_source,
            tools=tools if tools else None,
        )

        if not response_msg.tool_calls:
            answer = response_msg.content or ""
            self.context.add_assistant_message(answer)
            return answer

        # If the vision response triggered tool calls, hand off to normal loop
        self.context.add_assistant_tool_calls(response_msg)
        return self._tool_call_loop(response_msg, tools)

    def chat_with_audio(self, audio_path: str, language: str = None) -> str:
        """Transcribe audio then respond as normal text chat.

        Args:
            audio_path: Path to the audio file.
            language: Optional BCP-47 language hint.
        """
        from core.stt import get_stt_engine
        engine = get_stt_engine()
        transcribed = engine.transcribe_file(audio_path, language=language)
        if not transcribed.strip():
            return "（未能识别语音内容，请重试）"
        return self.chat(transcribed)

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
            self._execute_tool_calls(response_msg)

        # Exhausted tool-call iterations - ask LLM for a final answer without tools
        return self._finalize()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _tool_call_loop(self, initial_response_msg, tools: list) -> str:
        """Continue tool-call iteration from an existing response message."""
        self._execute_tool_calls(initial_response_msg)
        iterations = 1
        while iterations < self.max_tool_calls:
            iterations += 1
            response_msg = self.llm.chat(
                messages=self.context.get_messages(),
                tools=tools if tools else None,
            )
            if not response_msg.tool_calls:
                answer = response_msg.content or ""
                self.context.add_assistant_message(answer)
                return answer
            self.context.add_assistant_tool_calls(response_msg)
            self._execute_tool_calls(response_msg)
        return self._finalize()

    def _execute_tool_calls(self, response_msg) -> None:
        """Execute all tool calls in a response message and add results to context."""
        for tool_call in response_msg.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                func_args = {}
            result = self.registry.execute(func_name, func_args)
            self.context.add_tool_result(
                tool_call_id=tool_call.id,
                name=func_name,
                content=str(result),
            )

    def _finalize(self) -> str:
        """Ask LLM for a final answer without tools after exhausting iterations."""
        from core.i18n import _
        response_msg = self.llm.chat(
            messages=self.context.get_messages(),
            tools=None,
        )
        answer = response_msg.content or _("Sorry, something went wrong. Please try again.")
        self.context.add_assistant_message(answer)
        return answer

    def reset(self):
        """Reset conversation history."""
        self.context.clear()
