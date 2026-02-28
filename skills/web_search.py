"""
Web search skill - uses DuckDuckGo for free, API-key-free web search.
"""

from skills.base import BaseSkill


class WebSearchSkill(BaseSkill):
    name = "web_search"
    description = "Search the internet for up-to-date information. Use this when you need real-time data, news, or facts you are unsure about."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query keywords",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results, default 5",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 5) -> str:
        try:
            import os
            from ddgs import DDGS

            # primp (Rust extension used by ddgs) prints an impersonate-version warning
            # directly to OS-level stderr (fd 2), bypassing Python's logging module.
            # Redirect fd 2 to devnull for the duration of the DDGS call to suppress it.
            old_stderr_fd = os.dup(2)
            devnull_fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull_fd, 2)
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
            finally:
                os.dup2(old_stderr_fd, 2)
                os.close(old_stderr_fd)
                os.close(devnull_fd)

            if not results:
                from core.i18n import _
                return _("No search results found.")

            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"{i}. **{r.get('title', 'N/A')}**\n"
                    f"   {r.get('body', 'N/A')}\n"
                    f"   URL: {r.get('href', 'N/A')}"
                )
            return "\n\n".join(formatted)

        except Exception as e:
            return f"Search error: {e}"
