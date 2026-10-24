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


class GeminiAdapter(BaseAIAdapter):
    """Primary adapter for Google Gemini API (gemini-2.5-flash)."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        enabled: bool = None,
        timeout: float = None,
    ):
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model or settings.gemini_model
        self._enabled = enabled if enabled is not None else settings.gemini_enabled
        self._timeout = timeout or settings.gemini_timeout_seconds

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._enabled and self._api_key and not self._api_key.startswith("placeholder-"))

    async def generate_json_text(self, system_instruction: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise AuthenticationError("Gemini API key is not configured or is set to placeholder.", self.provider_name, 401)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Gemini API request timed out after {self._timeout}s.", self.provider_name) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error contacting Gemini API: {str(exc)}", self.provider_name) from exc

        status_code = response.status_code
        err_msg = ""
        retry_delay = parse_retry_after(response.headers.get("retry-after"))
        if status_code != 200:
            try:
                err_json = response.json()
                if isinstance(err_json, dict) and "error" in err_json:
                    err_obj = err_json["error"]
                    err_msg = err_obj.get("message", "")
                    if retry_delay is None:
                        for d in err_obj.get("details", []):
                            if isinstance(d, dict) and "retryDelay" in d:
                                delay_str = str(d["retryDelay"]).rstrip("s")
                                retry_delay = max(0.0, float(delay_str))
            except Exception:
                err_msg = response.text[:200]

        if status_code in (401, 403):
            raise AuthenticationError(f"Gemini authentication failed ({status_code}): {err_msg or response.text[:200]}", self.provider_name, status_code)
        elif status_code == 429:
            msg = f"Gemini rate limit or quota exceeded (429): {err_msg}" if err_msg else "Gemini rate limit or quota exceeded (429)."
            raise RateLimitError(msg, self.provider_name, status_code, retry_after=retry_delay)
        elif status_code in (500, 502, 503, 504):
            msg = f"Gemini server error ({status_code}): {err_msg}" if err_msg else f"Gemini server error ({status_code})."
            raise ProviderUnavailableError(msg, self.provider_name, status_code, retry_after=retry_delay)
        elif status_code != 200:
            raise AIProviderError(f"Gemini returned HTTP {status_code}: {err_msg or response.text[:200]}", self.provider_name, status_code)

        try:
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise InvalidResponseError("Gemini response contained no candidates.", self.provider_name, status_code)
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                raise InvalidResponseError("Gemini candidate contained no text content.", self.provider_name, status_code)
            return parts[0]["text"]
        except (ValueError, KeyError) as exc:
            raise InvalidResponseError(f"Failed to parse Gemini response payload: {str(exc)}", self.provider_name) from exc
