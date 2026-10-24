import asyncio
import json
import logging
import re
import time
from typing import List, Tuple, Optional

from pydantic import ValidationError as PydanticValError

from app.core.config import settings
from app.schemas.document import ExtractionResult
from app.schemas.requirement import ProjectRequirementsData, ProviderAttemptLog
from app.services.ai.base import BaseAIAdapter
from app.services.ai.exceptions import (
    AIProviderError,
    AuthenticationError,
    RateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    InvalidResponseError,
    AllProvidersFailedError,
)
from app.services.ai.gemini_adapter import GeminiAdapter
from app.services.ai.grok_adapter import GrokAdapter
from app.services.ai.nvidia_adapter import NvidiaNimAdapter
from app.services.ai.prompt import SYSTEM_INSTRUCTION, build_user_prompt

logger = logging.getLogger("devmatrix.ai.router")


def strip_markdown_fences(text: str) -> str:
    """Strips markdown code fences (```json ... ```) from model output."""
    clean = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return clean


def is_permanent_quota_error(error_message: str) -> bool:
    """Checks if an HTTP 429 error represents permanent quota exhaustion rather than a short transient rate limit."""
    msg = error_message.lower()
    permanent_indicators = [
        "insufficient_quota",
        "quota exceeded for quota metric ... and limit 'requests per day'",
        "per day",
        "daily limit",
        "billing",
        "credit",
        "plan",
        "exceeded your current quota",
    ]
    return any(indicator in msg for indicator in permanent_indicators)


class AIFallbackRouter:
    """
    Central fallback router orchestrating ordered execution of AI adapters:
    1. Primary: Google Gemini API
    2. Fallback: NVIDIA NIM
    (GrokAdapter is preserved but excluded from the active default chain)
    """

    def __init__(self, adapters: Optional[List[BaseAIAdapter]] = None):
        if adapters:
            self.adapters = adapters
        else:
            self.adapters = [
                GeminiAdapter(),
                NvidiaNimAdapter(),
            ]

    async def extract_requirements(
        self,
        extraction: ExtractionResult,
        allow_offline_fallback: bool = True,
    ) -> Tuple[ProjectRequirementsData, str, str, List[ProviderAttemptLog]]:
        """
        Executes requirement extraction following the strict fallback chain.
        Returns:
            (validated_requirements, provider_name, model_name, attempt_logs)
        Raises:
            AllProvidersFailedError if all providers fail.
        """
        attempt_history: List[ProviderAttemptLog] = []

        if getattr(settings, "demo_mode", False):
            from app.services.ai.demo_mock_adapter import DemoMockAIAdapter
            demo_adapter = DemoMockAIAdapter()
            demo_data = demo_adapter.generate_deterministic_requirements(extraction)
            attempt_history.append(
                ProviderAttemptLog(
                    provider=demo_adapter.provider_name,
                    model=demo_adapter.model_name,
                    duration_ms=10,
                    attempt_count=1,
                    status="success",
                    error_category="offline_deterministic_demo",
                )
            )
            logger.info("Demo mode enabled: Using %s for deterministic requirement extraction", demo_adapter.provider_name)
            return demo_data, demo_adapter.provider_name, demo_adapter.model_name, attempt_history

        for adapter in self.adapters:
            provider = adapter.provider_name
            model = adapter.model_name

            # Check if provider is configured and enabled
            if not adapter.is_configured:
                attempt_history.append(
                    ProviderAttemptLog(
                        provider=provider,
                        model=model,
                        duration_ms=0,
                        attempt_count=0,
                        status="skipped",
                        error_category="not_configured_or_disabled",
                    )
                )
                logger.info("Skipping unconfigured AI provider: %s (%s)", provider, model)
                continue

            max_retries = self._get_max_retries(provider)
            attempt_count = 0
            repair_attempted = False
            start_time = time.time()

            while attempt_count <= max_retries:
                attempt_count += 1
                try:
                    logger.info("Executing requirement extraction on provider: %s (%s), attempt %d", provider, model, attempt_count)
                    user_prompt = build_user_prompt(extraction)
                    raw_text = await adapter.generate_json_text(
                        system_instruction=SYSTEM_INSTRUCTION,
                        user_prompt=user_prompt,
                    )

                    # Parse and validate with Pydantic
                    validated_data = self._parse_and_validate(raw_text)

                    duration_ms = int((time.time() - start_time) * 1000)
                    attempt_history.append(
                        ProviderAttemptLog(
                            provider=provider,
                            model=model,
                            duration_ms=duration_ms,
                            attempt_count=attempt_count,
                            status="success",
                            error_category=None,
                        )
                    )
                    logger.info("Successfully extracted requirements via %s in %dms", provider, duration_ms)
                    return validated_data, provider, model, attempt_history

                except (json.JSONDecodeError, PydanticValError) as val_err:
                    duration_ms = int((time.time() - start_time) * 1000)
                    logger.warning("Provider %s output failed schema validation: %s", provider, str(val_err))

                    # Allow 1 repair attempt with explicit feedback
                    if not repair_attempted:
                        repair_attempted = True
                        try:
                            logger.info("Initiating single schema repair attempt on provider: %s", provider)
                            repair_prompt = build_user_prompt(extraction, repair_feedback=str(val_err))
                            repaired_raw = await adapter.generate_json_text(
                                system_instruction=SYSTEM_INSTRUCTION,
                                user_prompt=repair_prompt,
                            )
                            validated_data = self._parse_and_validate(repaired_raw)
                            duration_ms = int((time.time() - start_time) * 1000)
                            attempt_history.append(
                                ProviderAttemptLog(
                                    provider=provider,
                                    model=model,
                                    duration_ms=duration_ms,
                                    attempt_count=attempt_count,
                                    status="success",
                                    error_category="repaired",
                                )
                            )
                            logger.info("Successfully repaired requirements on %s in %dms", provider, duration_ms)
                            return validated_data, provider, model, attempt_history
                        except Exception as repair_exc:
                            logger.warning("Repair attempt failed on %s: %s", provider, str(repair_exc))

                    # If repair failed or already attempted, record validation failure and fall back
                    attempt_history.append(
                        ProviderAttemptLog(
                            provider=provider,
                            model=model,
                            duration_ms=duration_ms,
                            attempt_count=attempt_count,
                            status="validation_error",
                            error_category="schema_validation_failed",
                        )
                    )
                    break  # Fall back to next provider

                except AuthenticationError as auth_err:
                    # Permanent configuration error: do NOT retry endlessly
                    duration_ms = int((time.time() - start_time) * 1000)
                    attempt_history.append(
                        ProviderAttemptLog(
                            provider=provider,
                            model=model,
                            duration_ms=duration_ms,
                            attempt_count=attempt_count,
                            status="auth_error",
                            error_category="authentication_failed",
                        )
                    )
                    logger.error("Permanent authentication error on %s: %s. Aborting provider retries.", provider, str(auth_err))
                    break  # Switch to next provider immediately

                except (RateLimitError, ProviderUnavailableError, ProviderTimeoutError) as transient_err:
                    duration_ms = int((time.time() - start_time) * 1000)
                    status_name = "rate_limited" if isinstance(transient_err, RateLimitError) else "timeout" if isinstance(transient_err, ProviderTimeoutError) else "server_error"

                    # Handle permanent quota exhaustion immediately without retrying indefinitely
                    if isinstance(transient_err, RateLimitError) and is_permanent_quota_error(str(transient_err)):
                        logger.error(
                            "Permanent quota exhaustion detected on %s: %s. Aborting provider retries and falling back.",
                            provider,
                            str(transient_err),
                        )
                        attempt_history.append(
                            ProviderAttemptLog(
                                provider=provider,
                                model=model,
                                duration_ms=duration_ms,
                                attempt_count=attempt_count,
                                status="rate_limited",
                                error_category="quota_exhausted",
                            )
                        )
                        break

                    logger.warning(
                        "Transient error on %s (%s, attempt %d/%d): %s",
                        provider,
                        status_name,
                        attempt_count,
                        max_retries + 1,
                        str(transient_err),
                    )

                    if attempt_count <= max_retries:
                        # Respect provider-supplied retry guidance (Retry-After) if available, otherwise configurable backoff
                        retry_after_val = getattr(transient_err, "retry_after", None)
                        if retry_after_val is not None and retry_after_val > 0:
                            backoff_seconds = min(retry_after_val, 15.0)
                            logger.info("Using provider-supplied Retry-After delay: %.2fs on %s", backoff_seconds, provider)
                        else:
                            base_delay = settings.initial_retry_delay_seconds
                            backoff_seconds = min(base_delay * (2 ** (attempt_count - 1)), 15.0)
                            logger.info("Using exponential backoff delay: %.2fs on %s", backoff_seconds, provider)

                        await asyncio.sleep(backoff_seconds)
                    else:
                        attempt_history.append(
                            ProviderAttemptLog(
                                provider=provider,
                                model=model,
                                duration_ms=duration_ms,
                                attempt_count=attempt_count,
                                status=status_name,
                                error_category=status_name,
                            )
                        )
                        break

                except InvalidResponseError as inv_err:
                    duration_ms = int((time.time() - start_time) * 1000)
                    logger.warning("Invalid or truncated response from %s: %s", provider, str(inv_err))
                    attempt_history.append(
                        ProviderAttemptLog(
                            provider=provider,
                            model=model,
                            duration_ms=duration_ms,
                            attempt_count=attempt_count,
                            status="invalid_response",
                            error_category="truncated_or_invalid",
                        )
                    )
                    break

                except AIProviderError as gen_err:
                    duration_ms = int((time.time() - start_time) * 1000)
                    logger.warning("AI provider error on %s: %s", provider, str(gen_err))
                    attempt_history.append(
                        ProviderAttemptLog(
                            provider=provider,
                            model=model,
                            duration_ms=duration_ms,
                            attempt_count=attempt_count,
                            status="server_error",
                            error_category="provider_error",
                        )
                    )
        # If all configured providers were skipped (none configured), engage offline demo adapter
        all_unconfigured = all(a.status == "skipped" for a in attempt_history)
        if allow_offline_fallback and all_unconfigured:
            from app.services.ai.demo_mock_adapter import DemoMockAIAdapter
            demo_adapter = DemoMockAIAdapter()
            demo_data = demo_adapter.generate_deterministic_requirements(extraction)
            attempt_history.append(
                ProviderAttemptLog(
                    provider=demo_adapter.provider_name,
                    model=demo_adapter.model_name,
                    duration_ms=25,
                    attempt_count=1,
                    status="success",
                    error_category="offline_deterministic_fallback",
                )
            )
            logger.info("Engaged %s for offline requirement extraction", demo_adapter.provider_name)
            return demo_data, demo_adapter.provider_name, demo_adapter.model_name, attempt_history

        # If loop completed without returning, all providers failed
        error_msg = f"All {len(self.adapters)} AI providers in fallback sequence failed to produce validated requirements."
        logger.error(error_msg)
        raise AllProvidersFailedError(error_msg, [a.model_dump() for a in attempt_history])

    def _parse_and_validate(self, raw_text: str) -> ProjectRequirementsData:
        """Strips formatting fences, parses JSON, and validates with Pydantic."""
        cleaned = strip_markdown_fences(raw_text)
        data = json.loads(cleaned)
        return ProjectRequirementsData.model_validate(data)

    def _get_max_retries(self, provider: str) -> int:
        if provider == "gemini":
            return settings.gemini_max_retries
        elif provider == "grok":
            return settings.grok_max_retries
        elif provider == "nvidia_nim":
            return settings.nvidia_nim_max_retries
        return 2
