"""Reusable Ollama adapter for the configured local models."""

from __future__ import annotations

import random
import time
import uuid
from datetime import UTC, datetime

import httpx

from promptlab.adapters.base import CompletionRequest, CompletionResult
from promptlab.config import Settings
from promptlab.errors import (
    PermanentProviderError,
    TransientProviderError,
    TruncatedResponseError,
    UnknownModelError,
)
from promptlab.usage import CallRecord, compute_cost

MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 180.0
BACKOFF_BASE_SECONDS = 0.25


def _as_int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _response_text(payload: dict[str, object]) -> str | None:
    message = payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    raw = payload.get("response")
    return raw if isinstance(raw, str) else None


class OllamaAdapter:
    """One adapter class; Mistral vs Qwen is only a configured model_id."""

    provider = "ollama"

    def __init__(self, model_id: str) -> None:
        settings = Settings.from_env()
        self.model_id = model_id
        self._base_url = settings.ollama_base_url
        self._configured_model_ids = {model.model_id for model in settings.models.values()}

    def complete(self, request: CompletionRequest, run_id: str) -> CompletionResult:
        records: list[CallRecord] = []

        for attempt in range(1, MAX_ATTEMPTS + 1):
            record, error, text = self._attempt(request, run_id, attempt)
            records.append(record)
            if error is None:
                return CompletionResult(
                    succeeded=True,
                    text=text,
                    error_type=None,
                    records=records,
                )
            if not isinstance(error, TransientProviderError) or attempt == MAX_ATTEMPTS:
                return CompletionResult(
                    succeeded=False,
                    text=text if isinstance(error, TruncatedResponseError) else None,
                    error_type=type(error).__name__,
                    records=records,
                )
            time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)) + random.random() * 0.1)

        return CompletionResult(
            succeeded=False,
            text=None,
            error_type=TransientProviderError.__name__,
            records=records,
        )

    def _attempt(
        self,
        request: CompletionRequest,
        run_id: str,
        attempt: int,
    ) -> tuple[CallRecord, Exception | None, str | None]:
        if self.model_id not in self._configured_model_ids:
            error: Exception = UnknownModelError(self.model_id)
            return (
                self._record(
                    request,
                    run_id,
                    attempt,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=0,
                    stop_reason=None,
                    error=error,
                    response_text=None,
                ),
                error,
                None,
            )

        started = time.perf_counter()
        try:
            response = httpx.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": f"{request.system}\n\n{request.user_content}",
                    "stream": False,
                    "think": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_output_tokens,
                    },
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = TransientProviderError(str(exc))
            return (
                self._record(
                    request,
                    run_id,
                    attempt,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    stop_reason=None,
                    error=error,
                    response_text=None,
                ),
                error,
                None,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        status_code = response.status_code

        if status_code >= 500 or status_code == 429:
            error = TransientProviderError(f"Ollama returned HTTP {status_code}")
            return (
                self._record(
                    request,
                    run_id,
                    attempt,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    stop_reason=None,
                    error=error,
                    response_text=getattr(response, "text", None),
                ),
                error,
                None,
            )

        if status_code >= 400:
            error = PermanentProviderError(f"Ollama returned HTTP {status_code}")
            return (
                self._record(
                    request,
                    run_id,
                    attempt,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    stop_reason=None,
                    error=error,
                    response_text=getattr(response, "text", None),
                ),
                error,
                None,
            )

        try:
            payload: dict[str, object] = response.json()
        except ValueError as exc:
            error = PermanentProviderError(str(exc))
            return (
                self._record(
                    request,
                    run_id,
                    attempt,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    stop_reason=None,
                    error=error,
                    response_text=None,
                ),
                error,
                None,
            )

        text = _response_text(payload)
        input_tokens = _as_int(payload.get("prompt_eval_count"))
        output_tokens = _as_int(payload.get("eval_count"))
        done_reason = payload.get("done_reason")
        stop_reason = str(done_reason) if done_reason is not None else None

        if stop_reason == "length":
            error = TruncatedResponseError("output token ceiling was reached")
            return (
                self._record(
                    request,
                    run_id,
                    attempt,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    stop_reason=stop_reason,
                    error=error,
                    response_text=text,
                ),
                error,
                text,
            )

        return (
            self._record(
                request,
                run_id,
                attempt,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                stop_reason=stop_reason,
                error=None,
                response_text=text,
            ),
            None,
            text,
        )

    def _record(
        self,
        request: CompletionRequest,
        run_id: str,
        attempt: int,
        *,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        stop_reason: str | None,
        error: Exception | None,
        response_text: str | None,
    ) -> CallRecord:
        try:
            cost_usd = compute_cost(self.model_id, input_tokens, output_tokens)
        except UnknownModelError:
            cost_usd = 0.0

        return CallRecord(
            record_id=str(uuid.uuid4()),
            run_id=run_id,
            timestamp=datetime.now(UTC),
            provider="ollama",
            model_id=self.model_id,
            task=request.task,
            case_id=request.case_id,
            prompt_id=request.prompt_id,
            prompt_version=request.prompt_version,
            attempt=attempt,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=None,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            stop_reason=stop_reason,
            error_type=type(error).__name__ if error is not None else None,
            response_text=response_text,
        )
