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
    """Extract readable text from HTML bytes using stdlib html.parser."""
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link", "svg", "iframe"}

        def __init__(self):
            super().__init__()
            self._skip = 0
            self.parts: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag.lower() in self.SKIP_TAGS:
                self._skip += 1

        def handle_endtag(self, tag):
            if tag.lower() in self.SKIP_TAGS and self._skip > 0:
                self._skip -= 1

        def handle_data(self, data):
            if self._skip == 0:
                stripped = data.strip()
                if stripped:
                    self.parts.append(stripped)

    html_str = html_bytes.decode(encoding, errors="replace")
    parser = _TextExtractor()
    parser.feed(html_str)
    return "\n".join(parser.parts)


def extract_document_from_url(url: str, feishu_token: str = None) -> str:
    """Fetch a URL and return its text content.

    Handles two cases automatically:
    * Web page (text/html)  → extracts readable text via HTML parser
    * Document file (pdf/docx/xlsx/…) → downloads to temp file and extracts

    Args:
        url: HTTP(S) URL to fetch.
        feishu_token: Optional Feishu/Lark user_access_token for private wiki pages.
                      Configure via config.yaml key `feishu.token` or pass directly.
    """
    import urllib.request
    import urllib.error

    # ── Build request headers ──────────────────────────────────────────
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # Feishu / Lark private document token
    token = feishu_token
    if not token:
        try:
            from core.config import config
            token = config.get("feishu.token", None)
        except Exception:
            pass
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()
            raw = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return (
                f"[Error] Access denied (HTTP 403). "
                f"If this is a private Feishu/Lark document, set `feishu.token` in config.yaml "
                f"with your user_access_token.\nURL: {url}"
            )
        if e.code == 401:
            return (
                f"[Error] Authentication required (HTTP 401). "
                f"Set `feishu.token` in config.yaml.\nURL: {url}"
            )
        return f"[Error] HTTP {e.code}: {e.reason}\nURL: {url}"
    except Exception as e:
        return f"[Error] Failed to fetch URL: {e}\nURL: {url}"

    # ── HTML page → extract text ───────────────────────────────────────
    if "text/html" in content_type or "text/xml" in content_type:
        # Try to detect encoding from Content-Type header
        encoding = "utf-8"
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("charset="):
                encoding = part.split("=", 1)[1].strip()
                break
        text = _extract_html_text(raw, encoding)
        if not text.strip():
            return f"[Warning] No readable text found on page: {url}"
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
