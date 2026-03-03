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


def extract_document_from_url(url: str) -> str:
    """Download a document from URL to a temp file and extract its text."""
    import urllib.request
    suffix = Path(url.split("?")[0]).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
    try:
        urllib.request.urlretrieve(url, tmp_path)
        return extract_document(tmp_path)
    finally:
        os.unlink(tmp_path)


class DocumentSkill(BaseSkill):
    """Parse a local document or URL and return its text for the agent to reason over."""

    name = "read_document"
    description = (
        "Read and extract text from a document file (PDF, Word .docx, Excel .xlsx) "
        "given a local file path or a public URL. "
        "Use this when the user asks to analyse, summarize, or query a document."
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
