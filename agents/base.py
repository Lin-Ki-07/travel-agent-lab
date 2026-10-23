from abc import ABC, abstractmethod

from core.llm_client import OpenAICompatibleClient
from core.message import Message


class Agent(ABC):
    """所有 Agent 的公共基类。"""

    def __init__(
        self,
        name: str,
        llm: OpenAICompatibleClient,
        system_prompt: str,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self._history: list[Message] = []

    @abstractmethod
    def run(self, user_prompt: str) -> str:
        """运行 Agent，由具体子类实现。"""
        raise NotImplementedError

    def add_message(self, message: Message) -> None:
        """添加一条历史消息。"""
        self._history.append(message)

    def get_history(self) -> list[Message]:
        """返回历史消息副本。"""
        return self._history.copy()

    def clear_history(self) -> None:
        """清空历史消息。"""
        self._history.clear()