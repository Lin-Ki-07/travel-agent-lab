from dataclasses import dataclass
from typing import Literal

MessageRole = Literal["user", "assistant", "tool", "system"]

@dataclass
class Message:
    role: MessageRole
    content: str

    def to_dict(self) -> dict[str, str]:
        """转换成模型 API 使用的字典格式。"""
        return {
            "role": self.role,
            "content": self.content,
        }

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"