from abc import ABC, abstractmethod


class BaseAIAdapter(ABC):
    """Abstract interface for AI requirement extraction adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'grok', 'nvidia_nim')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model name."""
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required API keys and endpoints are configured and enabled."""
        pass

    @abstractmethod
    async def generate_json_text(self, system_instruction: str, user_prompt: str) -> str:
        """
        Executes a completion request and returns the raw JSON text response.
        Must raise appropriate AIProviderError subclasses on failure.
        """
        pass
