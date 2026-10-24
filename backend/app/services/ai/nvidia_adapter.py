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
    parse_retry_after,
)


class NvidiaNimAdapter(BaseAIAdapter):
    """Second fallback adapter for NVIDIA NIM API."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        endpoint: str = None,
        enabled: bool = None,
        timeout: float = None,
        max_tokens: int = None,
    ):
        self._api_key = api_key if api_key is not None else settings.nvidia_nim_api_key
        self._model = model or settings.nvidia_nim_model
        self._endpoint = (endpoint or settings.nvidia_nim_endpoint).rstrip("/")
        self._enabled = enabled if enabled is not None else settings.nvidia_nim_enabled
        self._timeout = timeout or settings.nvidia_nim_timeout_seconds
        self._max_tokens = max_tokens if max_tokens is not None else settings.nvidia_nim_max_tokens

    @property
    def provider_name(self) -> str:
        return "nvidia_nim"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._enabled and self._api_key and not self._api_key.startswith("placeholder-"))

    async def generate_json_text(self, system_instruction: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise AuthenticationError("NVIDIA NIM API key is not configured or is set to placeholder.", self.provider_name, 401)

        url = f"{self._endpoint}/chat/completions" if not self._endpoint.endswith("/chat/completions") else self._endpoint
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
            "temperature": 0.2,
        }
        if self._max_tokens:
            payload["max_tokens"] = self._max_tokens

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"NVIDIA NIM request timed out after {self._timeout}s.", self.provider_name) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error contacting NVIDIA NIM: {str(exc)}", self.provider_name) from exc

        status_code = response.status_code
        err_msg = ""
        retry_delay = parse_retry_after(response.headers.get("retry-after"))
        if status_code != 200:
            try:
                err_json = response.json()
                if isinstance(err_json, dict):
                    err_msg = err_json.get("error", {}).get("message") or err_json.get("message", "")
            except Exception:
                err_msg = response.text[:200]

        if status_code in (401, 403):
            raise AuthenticationError(f"NVIDIA NIM authentication failed ({status_code}): {err_msg or response.text[:200]}", self.provider_name, status_code)
        elif status_code == 429:
            msg = f"NVIDIA NIM rate limit or quota exceeded (429): {err_msg}" if err_msg else "NVIDIA NIM rate limit or quota exceeded (429)."
            raise RateLimitError(msg, self.provider_name, status_code, retry_after=retry_delay)
        elif status_code in (500, 502, 503, 504):
            msg = f"NVIDIA NIM server error ({status_code}): {err_msg}" if err_msg else f"NVIDIA NIM server error ({status_code})."
            raise ProviderUnavailableError(msg, self.provider_name, status_code, retry_after=retry_delay)
        elif status_code != 200:
            raise AIProviderError(f"NVIDIA NIM returned HTTP {status_code}: {err_msg or response.text[:200]}", self.provider_name, status_code)

        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise InvalidResponseError("NVIDIA NIM response contained no choices.", self.provider_name, status_code)
            choice = choices[0]
            finish_reason = choice.get("finish_reason")
            if finish_reason == "length":
                raise InvalidResponseError(
                    "NVIDIA NIM response truncated due to token limit (finish_reason='length').",
                    self.provider_name,
                    status_code,
                )
            content = choice.get("message", {}).get("content")
            if not content:
                raise InvalidResponseError("NVIDIA NIM choice contained empty content.", self.provider_name, status_code)
            return content
        except (ValueError, KeyError) as exc:
            raise InvalidResponseError(f"Failed to parse NVIDIA NIM response: {str(exc)}", self.provider_name) from exc
