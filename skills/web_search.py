"""
Web search skill - uses DuckDuckGo for free web search.
"""

from skills.base import BaseSkill


class WebSearchSkill(BaseSkill):
    name = "web_search"
    description = "搜索互联网获取最新信息。当你需要查找实时信息、新闻、或不确定的知识时使用。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
            },
            "max_results": {
                "type": "integer",
                "description": "最大返回结果数，默认5",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 5) -> str:
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return "未找到相关搜索结果。"

            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"{i}. **{r.get('title', 'N/A')}**\n"
                    f"   {r.get('body', 'N/A')}\n"
                    f"   链接: {r.get('href', 'N/A')}"
                )
            return "\n\n".join(formatted)

        except Exception as e:
            return f"搜索出错: {str(e)}"
