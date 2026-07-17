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

    _ALWAYS_ON_TOOLS = ["web_search", "knowledge_manage", "get_datetime"]
    _SCENE_TOOL_KEYWORDS = [
        (
            ["work_cv_manage"],
            ["简历", "工作经历", "时间轴", "项目经历", "docs/cv", "原始工作", "工作项目", "cv", "resume"],
        ),
        (
            ["git_daily_summary"],
            ["git", "commit", "提交", "日报", "周报", "代码总结", "提交总结"],
        ),
        (
            ["news_workflow", "web_search"],
            ["新闻", "热点", "资讯", "舆情", "时间轴", "最新动态", "实时新闻"],
        ),
        (
            ["get_weather"],
            ["天气", "气温", "下雨", "预报", "温度"],
        ),
        (
            ["wecom_notify"],
            ["企业微信", "wecom", "通知群里", "推送消息", "发消息给群"],
        ),
        (
            ["knowledge_manage"],
            ["记住", "保存知识", "知识库", "查一下之前", "回忆", "存入"],
        ),
        (
            ["document_skill"],
            ["文档", "pdf", "docx", "xlsx", "excel", "word", "表格", "解析文件"],
        ),
        (
            ["fortune_divination", "tarot_career_reading", "today_luck", "huangli_today"],
            ["算卦", "塔罗", "运势", "黄历", "今日宜", "占卜"],
        ),
    ]

    def __init__(self):
        self.llm = LLMClient()
        self.context = ContextManager()
        self.registry = SkillRegistry()
        self.max_tool_calls = config.get("agent.max_tool_calls", 5)
        self.last_usage = self._zero_usage()

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
        from skills.work_cv_skill import WorkCVSkill

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
        self.registry.register(WorkCVSkill())

    def _select_tool_names(self, user_input: str) -> list[str]:
        """Choose a small relevant tool set for the current user message."""
        text = (user_input or "").lower()
        selected: list[str] = []

        for tool_name in self._ALWAYS_ON_TOOLS:
            if tool_name not in selected:
                selected.append(tool_name)

        for tool_names, keywords in self._SCENE_TOOL_KEYWORDS:
            if any(keyword.lower() in text for keyword in keywords):
                for tool_name in tool_names:
                    if tool_name not in selected:
                        selected.append(tool_name)

        return selected

    # ------------------------------------------------------------------
    # Multimodal entry points
    # ------------------------------------------------------------------

    def chat_with_image(self, user_input: str, image_source: str) -> str:
        """Process text + image input and return agent response.

        Args:
            user_input: The text prompt from the user.
            image_source: URL or local file path of the image.
        """
        usage_total = self._zero_usage()
        self.context.add_user_message(user_input)
        tools = self.registry.get_openai_tools(self._select_tool_names(user_input))

        # First call uses vision model with image attached
        response_msg = self.llm.chat_with_image(
            messages=self.context.get_messages(),
            image_source=image_source,
            tools=tools if tools else None,
        )
        self._accumulate_usage(usage_total)

        if not response_msg.tool_calls:
            answer = response_msg.content or ""
            return self._finish_answer(answer, usage_total)

        # If the vision response triggered tool calls, hand off to normal loop
        self.context.add_assistant_tool_calls(response_msg)
        return self._tool_call_loop(initial_response_msg=response_msg, tools=tools, usage_total=usage_total)

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
        usage_total = self._zero_usage()
        self.context.add_user_message(user_input)

        tools = self.registry.get_openai_tools(self._select_tool_names(user_input))
        iterations = 0

        while iterations < self.max_tool_calls:
            iterations += 1

            # Call LLM
            response_msg = self.llm.chat(
                messages=self.context.get_messages(),
                tools=tools if tools else None,
            )
            self._accumulate_usage(usage_total)

            # If no tool calls, we have the final answer
            if not response_msg.tool_calls:
                answer = response_msg.content or ""
                return self._finish_answer(answer, usage_total)

            # Process tool calls
            self.context.add_assistant_tool_calls(response_msg)
            self._execute_tool_calls(response_msg)

        # Exhausted tool-call iterations - ask LLM for a final answer without tools
        return self._finalize(usage_total)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _tool_call_loop(self, initial_response_msg, tools: list, usage_total: dict) -> str:
        """Continue tool-call iteration from an existing response message."""
        self._execute_tool_calls(initial_response_msg)
        iterations = 1
        while iterations < self.max_tool_calls:
            iterations += 1
            response_msg = self.llm.chat(
                messages=self.context.get_messages(),
                tools=tools if tools else None,
            )
            self._accumulate_usage(usage_total)
            if not response_msg.tool_calls:
                answer = response_msg.content or ""
                return self._finish_answer(answer, usage_total)
            self.context.add_assistant_tool_calls(response_msg)
            self._execute_tool_calls(response_msg)
        return self._finalize(usage_total)

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

    def _finalize(self, usage_total: dict) -> str:
        """Ask LLM for a final answer without tools after exhausting iterations."""
        from core.i18n import _
        response_msg = self.llm.chat(
            messages=self.context.get_messages(),
            tools=None,
        )
        self._accumulate_usage(usage_total)
        answer = response_msg.content or _("Sorry, something went wrong. Please try again.")
        return self._finish_answer(answer, usage_total)

    def _zero_usage(self) -> dict:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _accumulate_usage(self, usage_total: dict) -> None:
        usage = self.llm.last_usage or {}
        usage_total["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
        usage_total["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
        usage_total["total_tokens"] += int(usage.get("total_tokens", 0) or 0)

    @staticmethod
    def _format_usage(usage_total: dict) -> str:
        return (
            f"\n\n[Token Usage] prompt={usage_total['prompt_tokens']}, "
            f"completion={usage_total['completion_tokens']}, total={usage_total['total_tokens']}"
        )

    def _finish_answer(self, answer: str, usage_total: dict) -> str:
        self.last_usage = usage_total.copy()
        final_answer = (answer or "") + self._format_usage(usage_total)
        self.context.add_assistant_message(final_answer)
        return final_answer

    def reset(self):
        """Reset conversation history."""
        self.context.clear()
