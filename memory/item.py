from dataclasses import dataclass

@dataclass(frozen=True)
class MemoryItem:
    id: str
    content: str
    created_at: str #保存时间