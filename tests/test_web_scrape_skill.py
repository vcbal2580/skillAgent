import json

from skills.web_scrape_skill import WebScrapeSkill


class _DummyResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _DummyClient:
    def __init__(self, *args, **kwargs):
        self._html = kwargs.pop("_html")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        return _DummyResponse(self._html)


def test_web_scrape_links_mode(monkeypatch):
    html = """
    <html><body>
      <a href='https://a.com'>A</a>
      <a href='https://b.com'>B</a>
    </body></html>
    """

    def _client_factory(*args, **kwargs):
        return _DummyClient(_html=html)

    monkeypatch.setattr("skills.web_scrape_skill.httpx.Client", _client_factory)

    skill = WebScrapeSkill()
    result = skill.execute(url="https://example.com", extract="links", max_items=1)

    payload = json.loads(result)
    assert payload["url"] == "https://example.com"
    assert len(payload["links"]) == 1
    assert payload["links"][0]["title"] == "A"


def test_web_scrape_structured_mode(monkeypatch):
    html = """
    <html><head><title>Demo</title></head>
    <body>
      <h1>Main</h1>
      <p>Paragraph one.</p>
    </body></html>
    """

    def _client_factory(*args, **kwargs):
        return _DummyClient(_html=html)

    monkeypatch.setattr("skills.web_scrape_skill.httpx.Client", _client_factory)

    skill = WebScrapeSkill()
    result = skill.execute(url="https://example.com", extract="structured")

    payload = json.loads(result)
    assert payload["title"] == "Demo"
    assert "Main" in payload["headings"]
    assert any("Paragraph one." in p for p in payload["paragraphs"])
