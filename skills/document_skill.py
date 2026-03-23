"""
Document Skill - parse PDF / Word / Excel files and return extracted text.
The agent can call this skill to read a document from disk or a URL,
then reason over its content or save it to the knowledge base.

Supported formats:
  .pdf   - via pypdf
  .docx  - via python-docx
  .xlsx  - via openpyxl
  .xls   - via xlrd
  .eml   - via Python built-in email module (no extra deps)

Install optional dependencies:
  pip install pypdf python-docx openpyxl xlrd
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from skills.base import BaseSkill


def _extract_eml(path: str) -> str:
    """Extract text from an .eml email file using Python's built-in email module.

    Handles both single emails and full thread chains:
    - Inline quoted text (lines with >) is preserved as-is in the body
    - Embedded sub-messages (message/rfc822, common in Outlook/Exchange threads)
      are recursively extracted with their own headers and body

    Lists attachment filenames but does not extract their binary content.
    """
    import email
    import email.policy
    import html as html_mod
    import re

    def _strip_html(raw_html: str) -> str:
        stripped = re.sub(r"<[^>]+>", " ", raw_html)
        stripped = html_mod.unescape(stripped)
        stripped = re.sub(r"[ \t]+", " ", stripped)
        stripped = re.sub(r"\n{3,}", "\n\n", stripped)
        return stripped.strip()

    def _iter_parts(msg):
        """Yield direct child parts without recursing into message/rfc822."""
        if msg.is_multipart():
            for part in msg.get_payload():
                yield part
        else:
            yield msg

    def _extract_msg(msg, depth: int = 0) -> str:
        """Recursively extract one email message (or sub-message) into text."""
        sections: list[str] = []

        # ── Headers ──────────────────────────────────────────────────
        header_lines = []
        for h in ("Date", "From", "To", "CC", "Subject"):
            val = msg.get(h, "")
            if val:
                header_lines.append(f"{h}: {val}")
        if header_lines:
            sections.append("\n".join(header_lines))

        # ── Walk direct MIME parts only (no auto-recurse into rfc822) ─
        plain_parts:  list[str] = []
        html_parts:   list[str] = []
        attachments:  list[str] = []
        sub_messages: list[str] = []

        def _process(part):
            ct    = part.get_content_type()
            disp  = str(part.get("Content-Disposition", ""))
            fname = part.get_filename()

            # ── Nested email thread (rfc822) ──────────────────────
            if ct == "message/rfc822":
                payload = part.get_payload()
                subs = payload if isinstance(payload, list) else [payload]
                for sub in subs:
                    if hasattr(sub, "get"):           # is a Message object
                        sub_messages.append(_extract_msg(sub, depth + 1))
                return  # do NOT recurse further into this part

            # ── Named attachment: record name only ────────────────
            if fname or "attachment" in disp.lower():
                if fname:
                    attachments.append(fname)
                return

            # ── Multipart container: process children directly ────
            if part.is_multipart():
                for child in part.get_payload():
                    _process(child)
                return

            # ── Leaf text parts ───────────────────────────────────
            if ct == "text/plain":
                try:
                    text = part.get_content()
                    if text and text.strip():
                        plain_parts.append(text.strip())
                except Exception:
                    pass
            elif ct == "text/html" and not plain_parts:
                try:
                    raw_html = part.get_content()
                    stripped = _strip_html(raw_html)
                    if stripped:
                        html_parts.append(stripped)
                except Exception:
                    pass

        _process(msg)

        body = "\n\n".join(plain_parts) if plain_parts else "\n\n".join(html_parts)
        if body:
            sections.append(body)
        if attachments:
            sections.append("[附件 / Attachments]: " + ", ".join(attachments))

        # Append embedded historical emails after current body
        for i, sub_text in enumerate(sub_messages, 1):
            sep = "─" * 40
            sections.append(f"\n{sep}\n[线程历史 {i} / Thread History {i}]\n{sep}\n{sub_text}")

        return "\n\n".join(s for s in sections if s)

    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)

    return _extract_msg(msg)


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


def _row_to_str(row, none_val="") -> str:
    """Convert a row of cell values to a tab-separated string."""
    parts = []
    for v in row:
        if v is None or v == "":
            parts.append(none_val)
        elif isinstance(v, float) and v == int(v):
            parts.append(str(int(v)))
        else:
            parts.append(str(v))
    return "\t".join(parts)


def _xlsx_sheets(path: str) -> list[tuple[str, list[str]]]:
    """Return list of (sheet_name, row_strings) for each sheet in an .xlsx file."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl not installed. Run: pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True)
    result = []
    for sheet in wb.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            if all(v is None for v in row):
                continue
            rows.append(_row_to_str(row))
        result.append((sheet.title, rows))
    return result


def _xls_sheets(path: str) -> list[tuple[str, list[str]]]:
    """Return list of (sheet_name, row_strings) for each sheet in a .xls file."""
    try:
        import xlrd
    except ImportError:
        raise ImportError("xlrd not installed. Run: pip install xlrd")
    wb = xlrd.open_workbook(path)
    result = []
    for sheet in wb.sheets():
        rows = []
        for row_idx in range(sheet.nrows):
            row = sheet.row_values(row_idx)
            if all(v == "" or v is None for v in row):
                continue
            rows.append(_row_to_str(row))
        result.append((sheet.name, rows))
    return result


def _extract_xlsx(path: str) -> str:
    """Extract text from .xlsx files using openpyxl."""
    try:
        sheets = _xlsx_sheets(path)
    except ImportError as e:
        return f"[Error] {e}"
    parts = []
    for name, rows in sheets:
        parts.append(f"\n=== Sheet: {name} ({len(rows)} rows) ===")
        parts.extend(rows)
    return "\n".join(parts)


def _extract_xls(path: str) -> str:
    """Extract text from legacy .xls files using xlrd."""
    try:
        sheets = _xls_sheets(path)
    except ImportError as e:
        return f"[Error] {e}"
    parts = []
    for name, rows in sheets:
        parts.append(f"\n=== Sheet: {name} ({len(rows)} rows) ===")
        parts.extend(rows)
    return "\n".join(parts)


def _chunk_text(text: str, chunk_chars: int = 3000, overlap: int = 200) -> list[str]:
    """Split a long text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def extract_document_chunks(path: str, chunk_chars: int = 3000) -> list[dict]:
    """Extract a document as labelled chunks suitable for knowledge base storage.

    Returns a list of dicts: {"label": str, "text": str, "meta": dict}
    Excel files are split per-sheet (then further chunked if a sheet is very large).
    PDF/DOCX/text are split into overlapping text chunks.
    """
    suffix = Path(path).suffix.lower()
    stem = Path(path).stem
    chunks: list[dict] = []

    if suffix in (".xlsx", ".xls"):
        try:
            sheets = _xlsx_sheets(path) if suffix == ".xlsx" else _xls_sheets(path)
        except ImportError as e:
            return [{"label": stem, "text": f"[Error] {e}", "meta": {}}]
        for sheet_name, rows in sheets:
            if not rows:
                continue
            header = rows[0] if rows else ""
            sheet_text = f"[文件: {stem} | Sheet: {sheet_name}]\n" + "\n".join(rows)
            if len(sheet_text) <= chunk_chars:
                chunks.append({
                    "label": f"{stem}_{sheet_name}",
                    "text": sheet_text,
                    "meta": {"file": stem, "sheet": sheet_name},
                })
            else:
                # Split large sheets into row batches, always prepend header
                batch_rows = []
                batch_chars = len(f"[文件: {stem} | Sheet: {sheet_name}]\n{header}\n")
                batch_num = 1
                for row in rows[1:]:  # skip header for counting
                    row_len = len(row) + 1
                    if batch_chars + row_len > chunk_chars and batch_rows:
                        text = f"[文件: {stem} | Sheet: {sheet_name} 第{batch_num}段]\n{header}\n" + "\n".join(batch_rows)
                        chunks.append({
                            "label": f"{stem}_{sheet_name}_p{batch_num}",
                            "text": text,
                            "meta": {"file": stem, "sheet": sheet_name, "part": batch_num},
                        })
                        batch_num += 1
                        batch_rows = [row]
                        batch_chars = len(f"[文件: {stem} | Sheet: {sheet_name} 第{batch_num}段]\n{header}\n") + row_len
                    else:
                        batch_rows.append(row)
                        batch_chars += row_len
                if batch_rows:
                    text = f"[文件: {stem} | Sheet: {sheet_name} 第{batch_num}段]\n{header}\n" + "\n".join(batch_rows)
                    chunks.append({
                        "label": f"{stem}_{sheet_name}_p{batch_num}",
                        "text": text,
                        "meta": {"file": stem, "sheet": sheet_name, "part": batch_num},
                    })
    else:
        full_text = extract_document(path)
        if full_text.startswith("[Error]"):
            return [{"label": stem, "text": full_text, "meta": {}}]
        text_chunks = _chunk_text(full_text, chunk_chars)
        for i, chunk in enumerate(text_chunks, 1):
            chunks.append({
                "label": f"{stem}_p{i}" if len(text_chunks) > 1 else stem,
                "text": chunk,
                "meta": {"file": stem, "part": i},
            })
    return chunks


def extract_document(path: str) -> str:
    """Extract text from a document file. Returns the full text content."""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".docx", ".doc"):
        return _extract_docx(path)
    elif suffix == ".xlsx":
        return _extract_xlsx(path)
    elif suffix == ".xls":
        return _extract_xls(path)
    elif suffix == ".eml":
        return _extract_eml(path)
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
        "Read and extract text from a document file (PDF, Word .docx, Excel .xlsx/.xls, "
        "Email .eml), a plain-text file, or a web page URL (including Feishu/Lark wiki pages). "
        "Use this when the user asks to analyse, summarize, query a document/webpage/email, "
        "or import a file into the knowledge base. "
        "Set save_to_knowledge=true to import the entire file into the knowledge base "
        "(Excel files are automatically split by sheet for accurate retrieval; "
        ".eml emails are split into chunks if long)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Local file path (absolute or relative) or public URL of the document.",
            },
            "save_to_knowledge": {
                "type": "boolean",
                "description": (
                    "If true, save the entire document into the knowledge base in chunks "
                    "so it can be retrieved in future conversations. "
                    "Excel files are split per-sheet automatically."
                ),
            },
        },
        "required": ["source"],
    }

    def execute(self, source: str, save_to_knowledge: bool = False) -> str:
        is_url = source.startswith("http://") or source.startswith("https://")

        if is_url:
            text = extract_document_from_url(source)
            if not text.strip():
                return "[Warning] No text extracted from the URL."
            max_chars = 12000
            truncated = text[:max_chars]
            suffix_note = f"\n\n[Document truncated at {max_chars} chars]" if len(text) > max_chars else ""
            if save_to_knowledge:
                try:
                    from knowledge.knowledge_manager import KnowledgeManager
                    km = KnowledgeManager()
                    text_chunks = _chunk_text(truncated, 3000)
                    ids = []
                    for i, chunk in enumerate(text_chunks, 1):
                        doc_id = km.save(content=chunk, tags=["document", "web"], source=source)
                        ids.append(doc_id)
                    return truncated + suffix_note + f"\n\n[已存入知识库，共 {len(ids)} 条，IDs: {', '.join(ids)}]"
                except Exception as e:
                    return truncated + suffix_note + f"\n\n[存入知识库失败: {e}]"
            return truncated + suffix_note

        # ── Local file ────────────────────────────────────────────────
        # Resolve relative paths against cwd
        resolved = source
        if not os.path.isabs(source):
            resolved = os.path.join(os.getcwd(), source)
        if not os.path.exists(resolved):
            return f"[Error] File not found: {source}\n(Looked at: {resolved})"

        suffix = Path(resolved).suffix.lower()
        stem = Path(resolved).stem

        if save_to_knowledge:
            try:
                from knowledge.knowledge_manager import KnowledgeManager
                km = KnowledgeManager()
                doc_chunks = extract_document_chunks(resolved)
                if not doc_chunks:
                    return "[Warning] No content extracted from file."
                if len(doc_chunks) == 1 and doc_chunks[0]["text"].startswith("[Error]"):
                    return doc_chunks[0]["text"]
                ids = []
                for chunk in doc_chunks:
                    tags = ["document", stem]
                    if chunk["meta"].get("sheet"):
                        tags.append(chunk["meta"]["sheet"])
                    doc_id = km.save(content=chunk["text"], tags=tags, source=resolved)
                    ids.append(doc_id)
                # Return a short preview + summary
                preview = extract_document(resolved)
                preview_short = preview[:3000]
                if suffix in (".xlsx", ".xls"):
                    return (
                        preview_short
                        + f"\n\n[Excel 文件已全量导入知识库]"
                        + f"\n[共 {len(doc_chunks)} 个分块，IDs: {', '.join(ids)}]"
                    )
                return (
                    preview_short
                    + f"\n\n[文件已导入知识库，共 {len(doc_chunks)} 个分块]"
                    + f"\n[IDs: {', '.join(ids)}]"
                )
            except Exception as e:
                import traceback
                return f"[存入知识库失败: {e}]\n{traceback.format_exc()}"

        # Just read and return (no save)
        text = extract_document(resolved)
        if not text.strip():
            return "[Warning] No text extracted from the document."
        max_chars = 12000
        truncated = text[:max_chars]
        suffix_note = f"\n\n[Document truncated at {max_chars} chars]" if len(text) > max_chars else ""
        return truncated + suffix_note
