from memory.sqlite_store import SQLiteMemoryStore


def handle_memory_command(
    text: str,
    store: SQLiteMemoryStore,
) -> str | None:
    """处理记忆命令；不是本函数支持的命令时返回 None。"""
    parts = text.strip().split(maxsplit=1)

    if not parts or parts[0] != "/remember":
        return None

    if len(parts) < 2:
        return "用法：/remember 要保存的内容"

    item = store.add(parts[1])

    return f"记忆已保存。ID: {item.id}\n内容: {item.content}"