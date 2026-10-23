from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        """执行工具，由具体工具类实现。"""
        raise NotImplementedError