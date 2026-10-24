import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional


def parse_retry_after(header_value: Optional[str]) -> Optional[float]:
    """
    Parses an HTTP Retry-After header value (seconds or RFC 2822 / 1123 HTTP date).
    Returns delay in seconds as float, or None if missing or unparseable.
    """
    if not header_value:
        return None
    cleaned = str(header_value).strip()
    if not cleaned:
        return None
    # 1. Try parsing as numeric seconds (integer or float)
    try:
        val = float(cleaned)
        return max(0.0, val)
    except ValueError:
        pass
    # 2. Try parsing as HTTP-date
    try:
        dt = parsedate_to_datetime(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        diff = (dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        return max(0.0, diff)
    except Exception:
        return None


class AIProviderError(Exception):
    """Base exception for AI provider adapter failures."""
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.retry_after = retry_after


class RateLimitError(AIProviderError):
    """Transient rate limit or quota exhaustion (HTTP 429)."""
    pass


class AuthenticationError(AIProviderError):
    """Permanent authentication/authorization error (HTTP 401, 403)."""
    pass


class ProviderTimeoutError(AIProviderError):
    """Request timeout when contacting provider."""
    pass


class ProviderUnavailableError(AIProviderError):
    """Transient server error or service unavailable (HTTP 500, 502, 503)."""
    pass


class InvalidResponseError(AIProviderError):
    """Provider response was empty, not valid JSON, or structurally unusable."""
    pass


class ValidationError(AIProviderError):
    """Provider response failed Pydantic schema validation after allowed repair attempts."""
    pass


class AllProvidersFailedError(Exception):
    """Raised when every configured provider in the fallback chain has been exhausted."""
    def __init__(self, message: str, attempt_history: List[dict]):
        super().__init__(message)
        self.message = message
        self.attempt_history = attempt_history
