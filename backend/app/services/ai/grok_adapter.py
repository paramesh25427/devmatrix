import httpx
from app.core.config import settings
from app.services.ai.base import BaseAIAdapter
from app.services.ai.exceptions import (
    AuthenticationError,
    RateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    InvalidResponseError,
    AIProviderError,
)


class GrokAdapter(BaseAIAdapter):
    """First fallback adapter for xAI Grok API."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        enabled: bool = None,
        timeout: float = None,
    ):
        self._api_key = api_key if api_key is not None else settings.grok_api_key
        self._model = model or settings.grok_model
        self._base_url = (base_url or settings.grok_base_url).rstrip("/")
        self._enabled = enabled if enabled is not None else settings.grok_enabled
        self._timeout = timeout or settings.grok_timeout_seconds

    @property
    def provider_name(self) -> str:
        return "grok"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._enabled and self._api_key and not self._api_key.startswith("placeholder-"))

    async def generate_json_text(self, system_instruction: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise AuthenticationError("xAI Grok API key is not configured or is set to placeholder.", self.provider_name, 401)

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"xAI Grok API request timed out after {self._timeout}s.", self.provider_name) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error contacting xAI Grok API: {str(exc)}", self.provider_name) from exc

        status_code = response.status_code
        if status_code in (401, 403):
            raise AuthenticationError(f"xAI Grok authentication failed ({status_code}).", self.provider_name, status_code)
        elif status_code == 429:
            raise RateLimitError("xAI Grok rate limit or quota exceeded (429).", self.provider_name, status_code)
        elif status_code in (500, 502, 503, 504):
            raise ProviderUnavailableError(f"xAI Grok server error ({status_code}).", self.provider_name, status_code)
        elif status_code != 200:
            raise AIProviderError(f"xAI Grok returned HTTP {status_code}: {response.text[:200]}", self.provider_name, status_code)

        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise InvalidResponseError("xAI Grok response contained no choices.", self.provider_name, status_code)
            content = choices[0].get("message", {}).get("content")
            if not content:
                raise InvalidResponseError("xAI Grok choice contained empty content.", self.provider_name, status_code)
            return content
        except (ValueError, KeyError) as exc:
            raise InvalidResponseError(f"Failed to parse xAI Grok response: {str(exc)}", self.provider_name) from exc
