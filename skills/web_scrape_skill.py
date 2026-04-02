"""
Web scrape skill - fetch and extract structured data from web pages.
"""

import json
from bs4 import BeautifulSoup
import httpx
from skills.base import BaseSkill


class WebScrapeSkill(BaseSkill):
    name = "web_scrape"
    description = "Fetch a web page and extract readable content, links, or table data."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The target URL to scrape",
            },
            "extract": {
                "type": "string",
                "enum": ["text", "links", "tables", "structured"],
                "description": "Extraction mode",
                "default": "text",
            },
            "selector": {
                "type": "string",
                "description": "Optional CSS selector to narrow extraction",
            },
            "max_items": {
                "type": "integer",
                "description": "Maximum items to return in links/tables mode",
                "default": 20,
            },
        },
        "required": ["url"],
    }

    def execute(
        self,
        url: str,
        extract: str = "text",
        selector: str = "",
        max_items: int = 20,
    ) -> str:
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                html = response.text

            soup = BeautifulSoup(html, "html.parser")
            root = soup.select_one(selector) if selector else soup
            if root is None:
                return f"Selector not found: {selector}"

            mode = (extract or "text").lower()
            if mode == "links":
                links = []
                for a in root.find_all("a", href=True):
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    if href:
                        links.append({"title": title, "url": href})
                    if len(links) >= max_items:
                        break
                return json.dumps({"url": url, "links": links}, ensure_ascii=False, indent=2)

            if mode == "tables":
                tables = []
                for table in root.find_all("table")[:max_items]:
                    rows = []
                    for tr in table.find_all("tr"):
                        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                        if cells:
                            rows.append(cells)
                    if rows:
                        tables.append(rows)
                return json.dumps({"url": url, "tables": tables}, ensure_ascii=False, indent=2)

            if mode == "structured":
                payload = {
                    "url": url,
                    "title": (soup.title.get_text(strip=True) if soup.title else ""),
                    "headings": [h.get_text(" ", strip=True) for h in root.find_all(["h1", "h2", "h3"])[:20]],
                    "paragraphs": [p.get_text(" ", strip=True) for p in root.find_all("p")[:20]],
                }
                return json.dumps(payload, ensure_ascii=False, indent=2)

            text = root.get_text("\n", strip=True)
            if len(text) > 4000:
                text = text[:4000] + "\n..."
            return f"URL: {url}\n\n{text}"

        except Exception as e:
            return f"Web scrape error: {e}"
