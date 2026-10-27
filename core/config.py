import os
from dataclasses import dataclass


SUPPORTED_PROVIDERS = {
    "openai",
    "deepseek",
    "ollama",
    "vllm",
    "modelscope",
}


@dataclass(frozen=True)
class AgentConfig:
    max_steps: int = 5
    max_history_messages: int = 20

    def __post_init__(self):
        if self.max_steps < 1:
            raise ValueError("max_steps 必须大于等于 1")
        
        if self.max_history_messages < 2:
            raise ValueError("max_history_messages 必须大于等于 2")

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "5")),
            max_history_messages=int(os.getenv("AGENT_MAX_HISTORY_MESSAGES", "20")),
        )


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "openai"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout: float = 60.0
    temperature: float = 0.7

    def __post_init__(self):
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"不支持的 LLM provider: {self.provider}")

        if self.timeout <= 0:
            raise ValueError("timeout 必须大于 0")

        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature 必须在 0 到 2 之间")

    @classmethod
    def from_env(cls) -> "LLMConfig":
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

        default_base_urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "ollama": "http://localhost:11434/v1",
            "vllm": "http://localhost:8000/v1",
            "modelscope": "https://api-inference.modelscope.cn/v1",
        }

        api_key_names = {
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "ollama": "OLLAMA_API_KEY",
            "vllm": "VLLM_API_KEY",
            "modelscope": "MODELSCOPE_API_KEY",
        }

        api_key_name = api_key_names.get(provider, "OPENAI_API_KEY")
        api_key = os.getenv(api_key_name, "")

        # 兼容你目前使用 OPENAI_API_KEY 保存 DeepSeek 密钥的方式
        if provider == "deepseek" and not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "")

        if provider in {"ollama", "vllm"} and not api_key:
            api_key = "local"

        return cls(
            provider=provider,
            model=os.getenv("MODEL_ID", ""),
            api_key=api_key,
            base_url=os.getenv(
                "OPENAI_BASE_URL",
                default_base_urls.get(provider, ""),
            ),
            timeout=float(os.getenv("LLM_TIMEOUT", "60")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )