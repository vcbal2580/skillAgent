"""
Document Skill - parse PDF / Word / Excel files and return extracted text.
The agent can call this skill to read a document from disk or a URL,
then reason over its content or save it to the knowledge base.

Supported formats:
  .pdf   - via pypdf
  .docx  - via python-docx
  .xlsx / .xls - via openpyxl / xlrd

Install optional dependencies:
  pip install pypdf python-docx openpyxl
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from skills.base import BaseSkill


def _extract_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[Error] pypdf not installed. Run: pip install pypdf"
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_docx(path: str) -> str:
    try:
        import docx
    except ImportError:
        return "[Error] python-docx not installed. Run: pip install python-docx"
    doc = docx.Document(path)
    return "\n".join(para.text for para in doc.paragraphs)


def _extract_xlsx(path: str) -> str:
    try:
        import openpyxl
    except ImportError:
        return "[Error] openpyxl not installed. Run: pip install openpyxl"
    wb = openpyxl.load_workbook(path, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        parts.append(f"=== Sheet: {sheet.title} ===")
        for row in sheet.iter_rows(values_only=True):
            parts.append("\t".join("" if v is None else str(v) for v in row))
    return "\n".join(parts)


def extract_document(path: str) -> str:
    """Extract text from a document file. Returns the full text content."""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".docx", ".doc"):
        return _extract_docx(path)
    elif suffix in (".xlsx", ".xls"):
        return _extract_xlsx(path)
    else:
        # Try to read as plain text
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            return f"[Error] Cannot read file: {e}"


def _extract_html_text(html_bytes: bytes, encoding: str = "utf-8") -> str:
    """Extract readable text from HTML bytes.

    Strategy:
    1. Detect encoding from <meta charset> / <meta http-equiv> if not given
    2. Prefer content inside <main>, <article>, <body> (in priority order)
    3. Skip script / style / nav / footer / header noise
    4. Insert line-breaks at block-level elements for readability
    5. Collapse blank lines and deduplicate repeated whitespace
    """
    from html.parser import HTMLParser
    import re as _re

    SKIP_TAGS = {
        "script", "style", "noscript", "head", "meta", "link",
        "svg", "iframe", "nav", "footer", "aside", "form",
        "button", "input", "select", "option",
    }
    BLOCK_TAGS = {
        "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "tr", "td", "th", "br", "hr", "section",
        "article", "main", "blockquote", "pre", "code",
        "header", "figcaption", "caption",
    }
    PRIORITY_TAGS = ("main", "article", "body")  # prefer in this order

    class _Extractor(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self._skip = 0
            self.parts: list[str] = []
            # track priority region
            self._region: dict[str, list[str]] = {t: [] for t in PRIORITY_TAGS}
            self._in_region: list[str] = []  # stack of active priority tags
            self._depth: dict[str, int] = {t: 0 for t in PRIORITY_TAGS}
            # meta charset detection
            self.detected_encoding: str | None = None

        def handle_starttag(self, tag, attrs):
            tag = tag.lower()
            attr_dict = dict(attrs)
            # Detect charset from <meta>
            if tag == "meta":
                cs = attr_dict.get("charset", "")
                if cs:
                    self.detected_encoding = cs
                elif attr_dict.get("http-equiv", "").lower() == "content-type":
                    ct = attr_dict.get("content", "")
                    m = _re.search(r"charset=([^\s;]+)", ct, _re.I)
                    if m:
                        self.detected_encoding = m.group(1)
            if tag in SKIP_TAGS:
                self._skip += 1
            if tag in BLOCK_TAGS and self._skip == 0:
                self.parts.append("\n")
            if tag in PRIORITY_TAGS:
                self._depth[tag] += 1
                if self._depth[tag] == 1:
                    self._in_region.append(tag)

        def handle_endtag(self, tag):
            tag = tag.lower()
            if tag in SKIP_TAGS and self._skip > 0:
                self._skip -= 1
            if tag in BLOCK_TAGS and self._skip == 0:
                self.parts.append("\n")
            if tag in PRIORITY_TAGS and self._depth[tag] > 0:
                self._depth[tag] -= 1
                if self._depth[tag] == 0 and self._in_region and self._in_region[-1] == tag:
                    self._in_region.pop()

        def handle_data(self, data):
            if self._skip:
                return
            stripped = data.strip()
            if not stripped:
                return
            self.parts.append(stripped)

    # ── Decode with best-effort encoding ──────────────────────────────
    parser = _Extractor()
    # First pass: detect encoding from meta tags
    try:
        parser.feed(html_bytes[:4096].decode("utf-8", errors="replace"))
    except Exception:
        pass
    detected = parser.detected_encoding
    if detected:
        try:
            html_str = html_bytes.decode(detected, errors="replace")
        except (LookupError, UnicodeDecodeError):
            html_str = html_bytes.decode(encoding, errors="replace")
    else:
        html_str = html_bytes.decode(encoding, errors="replace")

    # Full parse
    parser2 = _Extractor()
    try:
        parser2.feed(html_str)
    except Exception:
        pass

    raw_text = " ".join(parser2.parts)
    # Collapse excess whitespace / blank lines
    raw_text = _re.sub(r"[ \t]+", " ", raw_text)
    raw_text = _re.sub(r"\n{3,}", "\n\n", raw_text)
    return raw_text.strip()


def _extract_feishu(url: str, token: str = None) -> str:
    """Extract content from a Feishu/Lark wiki or doc URL via Open API.

    Requires a user_access_token or tenant_access_token configured as
    `feishu.token` in config.yaml.

    Supported URL patterns:
      https://*.feishu.cn/wiki/<node_token>
      https://*.feishu.cn/docx/<document_id>
      https://*.larkoffice.com/wiki/<node_token>
      https://*.larksuite.com/wiki/<node_token>
    """
    import re
    import json
    import urllib.request
    import urllib.error

    if not token:
        try:
            from core.config import config
            token = config.get("feishu.token", None)
        except Exception:
            pass

    if not token:
        return (
            "[Error] Feishu/Lark documents require authentication.\n"
            "Please set your user_access_token in config.yaml:\n\n"
            "feishu:\n"
            "  token: \"u-xxxxxxxxxxxxxxxxxxxx\"\n\n"
            "Get your token at: https://open.feishu.cn/ → Developer Console → token"
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # Detect base domain (feishu.cn / larkoffice.com / larksuite.com)
    m = re.match(r"https?://[^/]*?(feishu\.cn|larkoffice\.com|larksuite\.com)", url)
    base = f"https://open.{m.group(1)}" if m else "https://open.feishu.cn"

    def _api_get(path: str) -> dict:
        req = urllib.request.Request(f"{base}{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    # ── Case 1: wiki URL ──────────────────────────────────────────────
    wiki_m = re.search(r"/wiki/([A-Za-z0-9]+)", url)
    if wiki_m:
        node_token = wiki_m.group(1)
        try:
            # Get node info to find obj_type and obj_token
            node_resp = _api_get(f"/open-apis/wiki/v2/spaces/nodes?token={node_token}")
            if node_resp.get("code") != 0:
                return f"[Error] Feishu API: {node_resp.get('msg', 'unknown error')}"
            node = node_resp.get("data", {}).get("node", {})
            obj_type = node.get("obj_type", "")
            obj_token = node.get("obj_token", node_token)
        except Exception as e:
            # Fall through to raw content attempt
            obj_type = "docx"
            obj_token = node_token

        # Get raw text content from the resolved document
        try:
            if obj_type in ("docx", "doc", ""):
                content_resp = _api_get(f"/open-apis/docx/v1/documents/{obj_token}/raw_content")
                if content_resp.get("code") == 0:
                    return content_resp.get("data", {}).get("content", "")
            # Fallback: try sheet blocks
            blocks_resp = _api_get(
                f"/open-apis/docx/v1/documents/{obj_token}/blocks?document_revision_id=-1&page_size=200"
            )
            if blocks_resp.get("code") == 0:
                texts = []
                for blk in blocks_resp.get("data", {}).get("items", []):
                    for elem in blk.get("text", {}).get("elements", []):
                        t = elem.get("text_run", {}).get("content", "")
                        if t:
                            texts.append(t)
                return "\n".join(texts)
        except urllib.error.HTTPError as e:
            return f"[Error] Feishu API HTTP {e.code}: {e.reason}"
        except Exception as e:
            return f"[Error] Feishu API error: {e}"

    # ── Case 2: docx URL ─────────────────────────────────────────────
    docx_m = re.search(r"/docx/([A-Za-z0-9]+)", url)
    if docx_m:
        doc_id = docx_m.group(1)
        try:
            content_resp = _api_get(f"/open-apis/docx/v1/documents/{doc_id}/raw_content")
            if content_resp.get("code") == 0:
                return content_resp.get("data", {}).get("content", "")
            return f"[Error] Feishu API: {content_resp.get('msg', 'unknown error')}"
        except Exception as e:
            return f"[Error] Feishu API error: {e}"

    return f"[Error] Unrecognised Feishu URL pattern: {url}"


def _fetch_with_playwright(url: str) -> str:
    """Render a JS-heavy page with a headless Chromium browser and return its text.

    Falls back gracefully if playwright is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return ""

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Give JS-rendered content extra time to settle
            page.wait_for_timeout(3000)
            # Use inner_text to get the rendered visible text directly,
            # which works reliably for SPAs like Feishu that don't support SSR.
            text = page.inner_text("body")
            browser.close()
        return text.strip()
    except Exception as e:
        return f"[Error] Playwright render failed: {e}"


def extract_document_from_url(url: str, feishu_token: str = None) -> str:
    """Fetch a URL and return its text content.

    Handles automatically:
    * Web page (text/html)    → plain HTTP fetch + HTML parser;
                                if result is too short (SPA / JS-rendered),
                                automatically retries with headless Chromium
    * Document file (pdf/…)   → downloads to temp file and extracts

    Args:
        url: HTTP(S) URL (including publicly accessible Feishu share links).
        feishu_token: Unused, kept for API compatibility.
    """
    import urllib.request
    import urllib.error

    # ── Build request with a realistic browser User-Agent ─────────────
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    raw = None
    content_type = "text/html"

    try:
        req = urllib.request.Request(url, headers=headers)
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        with opener.open(req, timeout=20) as resp:
            content_type = resp.headers.get("Content-Type", "text/html").lower()
            raw = resp.read()
    except urllib.error.HTTPError as e:
        # 3xx redirect loops (e.g. Feishu SPA) → let Playwright handle it
        if 300 <= e.code < 400:
            return _fetch_with_playwright(url)
        return f"[Error] HTTP {e.code}: {e.reason}\nURL: {url}"
    except Exception:
        # Redirect loop or other network issue → go straight to Playwright
        return _fetch_with_playwright(url)

    # ── HTML page → extract text ───────────────────────────────────────
    if "text/html" in content_type or "text/xml" in content_type:
        encoding = "utf-8"
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("charset="):
                encoding = part.split("=", 1)[1].strip()
                break
        text = _extract_html_text(raw, encoding)
        # SPA pages (e.g. Feishu) return a JS shell with almost no text.
        # Fall back to headless browser rendering when content is too thin.
        if len(text.strip()) < 200:
            return _fetch_with_playwright(url)
        return text

    # ── Binary document → save to temp file and extract ───────────────
    suffix = Path(url.split("?")[0]).suffix
    if not suffix:
        # Infer from Content-Type
        ct_map = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/msword": ".doc",
        }
        for ct_key, ext in ct_map.items():
            if ct_key in content_type:
                suffix = ext
                break
        suffix = suffix or ".bin"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(raw)
    try:
        return extract_document(tmp_path)
    finally:
        os.unlink(tmp_path)


class DocumentSkill(BaseSkill):
    """Parse a local document or URL and return its text for the agent to reason over."""

    name = "read_document"
    description = (
        "Read and extract text from a document file (PDF, Word .docx, Excel .xlsx), "
        "a plain-text file, or a web page URL (including Feishu/Lark wiki pages). "
        "Use this when the user asks to analyse, summarize, or query a document or webpage."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Local file path or public URL of the document.",
            },
            "save_to_knowledge": {
                "type": "boolean",
                "description": (
                    "If true, also save the extracted text to the knowledge base "
                    "so it can be retrieved in future conversations."
                ),
            },
        },
        "required": ["source"],
    }

    def execute(self, source: str, save_to_knowledge: bool = False) -> str:
        if source.startswith("http://") or source.startswith("https://"):
            text = extract_document_from_url(source)
        else:
            if not os.path.exists(source):
                return f"[Error] File not found: {source}"
            text = extract_document(source)

        if not text.strip():
            return "[Warning] No text extracted from the document."

        # Truncate very large documents to avoid exceeding context limits
        max_chars = 12000
        truncated = text[:max_chars]
        suffix_note = f"\n\n[Document truncated at {max_chars} chars]" if len(text) > max_chars else ""

        if save_to_knowledge:
            try:
                from knowledge.knowledge_manager import KnowledgeManager
                km = KnowledgeManager()
                doc_id = km.save(
                    content=truncated,
                    tags=["document", Path(source).stem],
                )
                return truncated + suffix_note + f"\n\n[已存入知识库，ID: {doc_id}]"
            except Exception as e:
                return truncated + suffix_note + f"\n\n[存入知识库失败: {e}]"

        return truncated + suffix_note
