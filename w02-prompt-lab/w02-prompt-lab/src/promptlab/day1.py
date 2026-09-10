"""Day 1 runner: three extraction calls to local Mistral, with usage records."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime

import httpx

from promptlab.config import PROJECT_ROOT, Settings
from promptlab.usage import CallRecord, append_record, compute_cost

CASE_IDS = ("E12", "E07", "E11")
PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "baseline.v0.md"
CASES_PATH = PROJECT_ROOT / "cases" / "extraction.jsonl"
MAX_OUTPUT_TOKENS = 256
TEMPERATURE = 0.0
TRUNCATION_OUTPUT_TOKENS = 8


def load_case_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: dict[str, object] = json.loads(line)
        case_id = str(row["id"])
        if case_id in CASE_IDS:
            sources[case_id] = str(row["source"])
    return sources


def call_ollama(base_url: str, model_id: str, prompt: str, num_predict: int) -> tuple[dict[str, object], int]:
    started = time.perf_counter()
    response = httpx.post(
        f"{base_url}/api/generate",
        json={
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": num_predict,
            },
        },
        timeout=180.0,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    response.raise_for_status()
    payload: dict[str, object] = response.json()
    return payload, latency_ms


def main() -> None:
    settings = Settings.from_env()
    model = settings.models["mistral"]
    template = PROMPT_PATH.read_text(encoding="utf-8")
    sources = load_case_sources()
    run_id = str(uuid.uuid4())

    for case_id in CASE_IDS:
        prompt = template.replace("{document_text}", sources[case_id])
        payload, latency_ms = call_ollama(settings.ollama_base_url, model.model_id, prompt, MAX_OUTPUT_TOKENS)

        input_tokens = int(payload.get("prompt_eval_count") or 0)
        output_tokens = int(payload.get("eval_count") or 0)
        stop_reason = payload.get("done_reason")
        response_text = payload.get("response")

        record = CallRecord(
            record_id=str(uuid.uuid4()),
            run_id=run_id,
            timestamp=datetime.now(UTC),
            provider="ollama",
            model_id=model.model_id,
            task="extraction",
            case_id=case_id,
            prompt_id="baseline",
            prompt_version="v0",
            attempt=1,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=None,
            latency_ms=latency_ms,
            cost_usd=compute_cost(model.model_id, input_tokens, output_tokens),
            stop_reason=str(stop_reason) if stop_reason is not None else None,
            error_type=None,
            response_text=str(response_text) if response_text is not None else None,
        )
        append_record(record, run_id)
        print(f"{case_id}: {input_tokens} in / {output_tokens} out / {latency_ms} ms / {stop_reason}")

    truncation_prompt = template.replace("{document_text}", sources["E11"])
    truncation_payload, truncation_latency_ms = call_ollama(
        settings.ollama_base_url,
        model.model_id,
        truncation_prompt,
        TRUNCATION_OUTPUT_TOKENS,
    )
    truncation_stop = truncation_payload.get("done_reason")
    truncation_input = int(truncation_payload.get("prompt_eval_count") or 0)
    truncation_output = int(truncation_payload.get("eval_count") or 0)
    truncation_text = truncation_payload.get("response")
    truncation_record = CallRecord(
        record_id=str(uuid.uuid4()),
        run_id=run_id,
        timestamp=datetime.now(UTC),
        provider="ollama",
        model_id=model.model_id,
        task="extraction",
        case_id="E11",
        prompt_id="baseline",
        prompt_version="v0",
        attempt=2,
        temperature=TEMPERATURE,
        max_output_tokens=TRUNCATION_OUTPUT_TOKENS,
        input_tokens=truncation_input,
        output_tokens=truncation_output,
        cached_input_tokens=None,
        latency_ms=truncation_latency_ms,
        cost_usd=compute_cost(model.model_id, truncation_input, truncation_output),
        stop_reason=str(truncation_stop) if truncation_stop is not None else None,
        error_type="TruncatedResponseError" if truncation_stop == "length" else None,
        response_text=str(truncation_text) if truncation_text is not None else None,
    )
    append_record(truncation_record, run_id)
    print(
        f"E11 truncation demo: stop={truncation_record.stop_reason} "
        f"error={truncation_record.error_type}"
    )

    print(f"wrote runs/{run_id}.jsonl")


if __name__ == "__main__":
    main()
