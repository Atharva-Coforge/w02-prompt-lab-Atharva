from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch

from promptlab.day1 import as_int, load_case_sources, main


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


def test_load_case_sources_selects_short_middle_and_long_cases() -> None:
    sources = load_case_sources()

    assert set(sources) == {"E12", "E07", "E11"}
    assert len(sources["E12"]) < len(sources["E07"]) < len(sources["E11"])


def test_as_int_keeps_ints_and_defaults_missing_values() -> None:
    assert as_int(19) == 19
    assert as_int(None) == 0
    assert as_int("x") == 0


def test_truncation_demo_sets_error_type_when_done_reason_is_length(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    num_predict_values: list[object] = []

    def fake_post(*args: object, **kwargs: object) -> FakeResponse:
        body = kwargs["json"]
        assert isinstance(body, dict)
        options = body["options"]
        assert isinstance(options, dict)
        num_predict_values.append(options["num_predict"])
        if options["num_predict"] == 8:
            return FakeResponse(
                {
                    "response": "cut off",
                    "prompt_eval_count": 50,
                    "eval_count": 8,
                    "done_reason": "length",
                }
            )
        return FakeResponse(
            {
                "response": "ok",
                "prompt_eval_count": 20,
                "eval_count": 15,
                "done_reason": "stop",
            }
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("promptlab.day1.httpx.post", fake_post)
    main()

    run_files = list((tmp_path / "runs").glob("*.jsonl"))
    assert len(run_files) == 1
    records = [
        json.loads(line)
        for line in run_files[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert num_predict_values == [256, 256, 256, 8]
    assert len(records) == 4
    assert [row["case_id"] for row in records] == ["E12", "E07", "E11", "E11"]
    assert records[0]["error_type"] is None
    assert records[1]["error_type"] is None
    assert records[2]["error_type"] is None
    assert records[3]["stop_reason"] == "length"
    assert records[3]["error_type"] == "TruncatedResponseError"
    assert records[3]["attempt"] == 2
    assert records[3]["max_output_tokens"] == 8
