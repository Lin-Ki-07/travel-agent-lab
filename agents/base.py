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
        max_history_messages: int = 20,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self._history: list[Message] = []
        self.max_history_messages = max_history_messages

    @abstractmethod
    def run(self, user_prompt: str) -> str:
        """运行 Agent，由具体子类实现。"""
        raise NotImplementedError

    def add_message(self, message: Message) -> None:
        """添加消息，超限时按完整轮次删除旧历史。"""
        self._history.append(message)
        
        while len(self._history) > self.max_history_messages:
            next_round_start = next(
                (
                    index
                    for index, item in enumerate(self._history)
                    if index > 0 and item.role == "user"
                ),
                None,
            )

            if next_round_start is None:
                # 只剩当前一轮，保留完整的执行上下文。
                break

            del self._history[:next_round_start]
        
    def get_history(self) -> list[Message]:
        """返回历史消息副本。"""
        return self._history.copy()

    def clear_history(self) -> None:
        """清空历史消息。"""
        self._history.clear()