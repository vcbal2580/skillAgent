"""
Knowledge management skill - save, search, list, delete personal knowledge.
"""

from skills.base import BaseSkill
from knowledge.knowledge_manager import KnowledgeManager


class KnowledgeSkill(BaseSkill):
    name = "knowledge_manage"
    description = (
        "Manage the personal knowledge base. Save new knowledge, search existing entries, "
        "list all entries, or delete entries. Use when the user wants to remember something "
        "or you need to retrieve previously stored information."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["save", "search", "list", "delete"],
                "description": "Operation: save=save knowledge, search=search knowledge, list=list all, delete=delete entry",
            },
            "content": {
                "type": "string",
                "description": "For save: text to store; for search: query string; for delete: knowledge ID",
            },
            "tags": {
                "type": "string",
                "description": "Optional comma-separated tags, e.g. 'python,programming,tips'",
            },
        },
        "required": ["action"],
    }

    def __init__(self):
        self.km = KnowledgeManager()

    def execute(self, action: str, content: str = "", tags: str = "") -> str:
        from core.i18n import _
        try:
            if action == "save":
                if not content:
                    return _("Error: 'content' is required to save knowledge")
                tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                doc_id = self.km.save(content=content, tags=tag_list)
                return f"\u2705 Knowledge saved (ID: {doc_id})\nContent: {content[:100]}..."

            elif action == "search":
                if not content:
                    return _("Error: 'content' is required as the search query")
                results = self.km.search(content)
                if not results:
                    return _("No related knowledge found.")
                formatted = []
                for r in results:
                    tags_str = r["metadata"].get("tags", "")
                    formatted.append(
                        f"- [ID: {r['id']}] {r['text'][:200]}"
                        + (f" (tags: {tags_str})" if tags_str else "")
                    )
                return f"Found {len(results)} related entries:\n" + "\n".join(formatted)

            elif action == "list":
                items = self.km.list_all()
                if not items:
                    return _("Knowledge base is empty.")
                formatted = []
                for item in items:
                    tags_str = item["metadata"].get("tags", "")
                    formatted.append(
                        f"- [ID: {item['id']}] {item['text'][:100]}"
                        + (f" (tags: {tags_str})" if tags_str else "")
                    )
                return f"Knowledge base has {len(items)} entries:\n" + "\n".join(formatted)

            elif action == "delete":
                if not content:
                    return _("Error: 'content' must be the knowledge ID to delete")
                success = self.km.delete(content)
                return (
                    f"\u2705 Knowledge '{content}' deleted"
                    if success
                    else f"\u274c Delete failed - ID not found: {content}"
                )

            else:
                return _("Unknown action: %s. Supported: save / search / list / delete") % action

        except Exception as e:
            return f"Knowledge operation error: {e}"
