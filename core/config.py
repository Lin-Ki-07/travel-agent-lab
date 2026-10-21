import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    max_steps: int = 5

    def __post_init__(self):
        if self.max_steps < 1:
            raise ValueError("max_steps 必须大于等于 1")

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "5")),
        )