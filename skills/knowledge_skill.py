"""
Knowledge management skill - save, search, list, delete personal knowledge.
"""

from skills.base import BaseSkill
from knowledge.knowledge_manager import KnowledgeManager


class KnowledgeSkill(BaseSkill):
    name = "knowledge_manage"
    description = (
        "管理个人知识库。可以保存新知识、搜索已有知识、列出所有知识、或删除知识条目。"
        "当用户想记住某些信息、或者你需要查找之前存储的信息时使用。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["save", "search", "list", "delete"],
                "description": "操作类型: save=保存知识, search=搜索知识, list=列出知识, delete=删除知识",
            },
            "content": {
                "type": "string",
                "description": "保存时：要保存的知识内容；搜索时：搜索查询；删除时：知识ID",
            },
            "tags": {
                "type": "string",
                "description": "保存时可选的标签，用逗号分隔，如 'python,编程,技巧'",
            },
        },
        "required": ["action"],
    }

    def __init__(self):
        self.km = KnowledgeManager()

    def execute(self, action: str, content: str = "", tags: str = "") -> str:
        try:
            if action == "save":
                if not content:
                    return "错误: 保存知识需要提供content参数"
                tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                doc_id = self.km.save(content=content, tags=tag_list)
                return f"✅ 知识已保存 (ID: {doc_id})\n内容: {content[:100]}..."

            elif action == "search":
                if not content:
                    return "错误: 搜索知识需要提供content作为查询"
                results = self.km.search(content)
                if not results:
                    return "未找到相关知识。"
                formatted = []
                for r in results:
                    tags_str = r["metadata"].get("tags", "")
                    formatted.append(
                        f"- [ID: {r['id']}] {r['text'][:200]}"
                        f"{f' (标签: {tags_str})' if tags_str else ''}"
                    )
                return f"找到 {len(results)} 条相关知识:\n" + "\n".join(formatted)

            elif action == "list":
                items = self.km.list_all()
                if not items:
                    return "知识库为空。"
                formatted = []
                for item in items:
                    tags_str = item["metadata"].get("tags", "")
                    formatted.append(
                        f"- [ID: {item['id']}] {item['text'][:100]}"
                        f"{f' (标签: {tags_str})' if tags_str else ''}"
                    )
                return f"知识库共 {len(items)} 条:\n" + "\n".join(formatted)

            elif action == "delete":
                if not content:
                    return "错误: 删除知识需要提供content参数作为知识ID"
                success = self.km.delete(content)
                return f"✅ 知识 {content} 已删除" if success else f"❌ 删除失败，未找到ID: {content}"

            else:
                return f"未知操作: {action}，支持: save/search/list/delete"

        except Exception as e:
            return f"知识库操作出错: {str(e)}"
