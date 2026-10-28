from memory.item import MemoryItem
from memory.sqlite_store import SQLiteMemoryStore


MEMORY_HELP = (
    "长期记忆命令：\n"
    "/remember 内容：保存记忆\n"
    "/memories：查看最近 10 条记忆\n"
    "/recall 关键词：搜索记忆\n"
    "/update ID 新内容：更新指定记忆\n"
    "/forget ID：删除指定记忆\n"
    "/memory-help：查看本帮助"
)

LIST_REQUESTS = {
    "我保存的长期记忆是什么",
    "我保存了哪些长期记忆",
    "查看长期记忆",
    "查看我的长期记忆",
    "列出长期记忆",
}


def format_memories(items: list[MemoryItem]) -> str:
    """将记忆项转换为可直接展示的文本。"""
    if not items:
        return "没有找到记忆。"

    return "\n\n".join(
        f"ID: {item.id}\n内容: {item.content}"
        for item in items
    )


def handle_memory_command(
    text: str,
    store: SQLiteMemoryStore,
) -> str | None:
    """处理确定的记忆请求；普通问题返回 None。"""
    text = text.strip()

    if not text:
        return None

    # 仅匹配明确的查看请求，不猜测含糊的修改或删除意图。
    normalized = text.rstrip("？?。！!")
    if normalized in LIST_REQUESTS:
        text = "/memories"

    parts = text.split(maxsplit=1)
    command = parts[0]
    argument = parts[1].strip() if len(parts) == 2 else ""

    if command == "/memory-help":
        return MEMORY_HELP

    if command == "/remember":
        if not argument:
            return "用法：/remember 要保存的内容"

        item = store.add(argument)
        return f"记忆已保存。ID: {item.id}\n内容: {item.content}"

    if command == "/memories":
        if argument:
            return "用法：/memories"

        items = store.list_recent(limit=10)

        if not items:
            return "当前没有保存的长期记忆。"

        return (
            "最近保存的长期记忆（最多 10 条）：\n"
            + format_memories(items)
        )

    if command == "/recall":
        if not argument:
            return "用法：/recall 关键词"

        items = store.search(argument, limit=10)
        return format_memories(items)

    if command == "/update":
        update_parts = argument.split(maxsplit=1)

        if len(update_parts) != 2:
            return "用法：/update 完整ID 新内容"

        memory_id, content = update_parts
        updated = store.update(memory_id, content)

        if not updated:
            return "未找到指定 ID 的记忆，请先用 /memories 或 /recall 查询。"

        return f"记忆已更新。ID: {memory_id}\n内容: {content.strip()}"

    if command == "/forget":
        if not argument or len(argument.split()) != 1:
            return "用法：/forget 完整ID"

        deleted = store.delete(argument)

        if not deleted:
            return "未找到指定 ID 的记忆，请先用 /memories 或 /recall 查询。"

        return f"记忆已删除。ID: {argument}"

    if command.startswith("/"):
        return f"未知命令：{command}\n{MEMORY_HELP}"

    return None