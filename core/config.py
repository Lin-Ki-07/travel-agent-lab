import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    max_steps: int = 5
    provider: str = "openai"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout: float = 60.0
    temperature: float = 0.7

    def __post_init__(self):
        if self.max_steps < 1:
            raise ValueError("max_steps 必须大于等于 1")
        
        if self.timeout <= 0:
            raise ValueError("timeout 必须大于 0")
        
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature 必须在 0 到 2 之间")
        

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "5")),
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("MODEL_ID", ""),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", ""),
            timeout=float(os.getenv("LLM_TIMEOUT", "60")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )