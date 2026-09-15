from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from promptlab.adapters.base import CompletionRequest, ModelAdapter


def _parse_json_text(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def complete_structured[T: BaseModel](
    adapter: ModelAdapter,
    request: CompletionRequest,
    schema: type[T],
    run_id: str,
    max_repairs: int = 1,
) -> T:
    """Return a schema-validated completion with a bounded semantic repair loop.

    Transport retry remains inside the adapter.
    Schema/content repair belongs here.

    On validation failure, send the validation error text back to the model and
    instruct it to correct only what the error concerns. Do not perform more
    than max_repairs semantic repair attempts.
    """

    current = request
    last_error: Exception | None = None
    for attempt in range(max_repairs + 1):
        result = adapter.complete(current, run_id)
        text = result.text or ""
        try:
            parsed = _parse_json_text(text)
            return schema.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            if attempt >= max_repairs:
                raise
            current = request.model_copy(
                update={
                    "user_content": (
                        "Your previous response failed validation with the following "
                        "error. Return a corrected JSON object. Do not change any "
                        f"field the error does not concern.\n<error>\n{exc}\n</error>"
                    )
                }
            )
    raise last_error if last_error is not None else RuntimeError("structured completion failed")
