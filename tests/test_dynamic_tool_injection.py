"""Tests for scene-based dynamic tool injection."""

import unittest

from core.agent import Agent


class TestDynamicToolInjection(unittest.TestCase):
    def setUp(self):
        self.agent = Agent()
        self.agent.register_default_skills()

    def test_work_cv_query_selects_relevant_subset(self):
        tools = self.agent.registry.get_openai_tools(self.agent._select_tool_names(
            "帮我整理工作经历并生成最新简历，输出到 docs/cv"
        ))
        names = [tool["function"]["name"] for tool in tools]

        self.assertIn("work_cv_manage", names)
        self.assertIn("web_search", names)
        self.assertIn("knowledge_manage", names)
        self.assertIn("get_datetime", names)
        self.assertNotIn("fortune_divination", names)
        self.assertLess(len(names), len(self.agent.registry.list_skills()))

    def test_weather_query_routes_to_weather_tool(self):
        tools = self.agent.registry.get_openai_tools(self.agent._select_tool_names("今天北京天气怎么样"))
        names = [tool["function"]["name"] for tool in tools]

        self.assertIn("get_weather", names)
        self.assertNotIn("work_cv_manage", names)


if __name__ == "__main__":
    unittest.main()
