from memory.sqlite_store import SQLiteMemoryStore
from tools.base import BaseTool


class MemoryTool(BaseTool):
    def __init__(self, store: SQLiteMemoryStore):
        super().__init__(
            name="memory",
            description=(
                "管理用户明确要求保存的长期记忆。"
                "action='add' 时传 content；"
                "action='search' 时传 keyword，可传 limit；"
                "action='update' 时传 memory_id 和 content；"
                "action='delete' 时传 memory_id。"
                "修改或删除前先检索获取完整 ID，禁止编造 ID。"
            ),
        )
        self.store = store

    def run(
        self,
        action: str,
        content: str = "",
        keyword: str = "",
        memory_id: str = "",
        limit: int = 5,
    ) -> str:
        if action == "add":
            item = self.store.add(content)
            return f"记忆已保存。ID: {item.id}\n内容: {item.content}"

        if action == "search":
            items = self.store.search(keyword, limit=limit)

            if not items:
                return "没有找到匹配的记忆。"

            return "\n\n".join(
                f"ID: {item.id}\n内容: {item.content}"
                for item in items
            )

        if action == "update":
            if not memory_id.strip():
                raise ValueError("更新记忆需要提供 memory_id")

            updated = self.store.update(memory_id, content)
            return "记忆已更新。" if updated else "未找到指定 ID 的记忆。"

        if action == "delete":
            if not memory_id.strip():
                raise ValueError("删除记忆需要提供 memory_id")

            deleted = self.store.delete(memory_id)
            return "记忆已删除。" if deleted else "未找到指定 ID 的记忆。"

        raise ValueError("action 只支持 add、search、update、delete")