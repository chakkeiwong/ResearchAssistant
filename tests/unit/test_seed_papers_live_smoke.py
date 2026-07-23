from __future__ import annotations

import json
from pathlib import Path

from scripts.run_seed_papers_live_smoke import HOSTS, SCHEMA_VERSION, run


class _Response:
    status = 200

    def __init__(self, url: str):
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.url

    def read(self, _limit: int):
        if "openalex.org" in self.url:
            value = {"meta": {"count": 0}, "results": []}
        elif "crossref.org" in self.url:
            value = {"message": {"total-results": 0, "items": []}}
        else:
            value = {"total": 0, "data": []}
        return json.dumps(value).encode()


def test_live_smoke_schema_and_budgets_without_network(tmp_path: Path) -> None:
    opened: list[str] = []

    def opener(url: str, *, timeout: int):
        assert timeout == 30
        opened.append(url)
        return _Response(url)

    result = run(
        topic="Neural optimal transport",
        output_root=tmp_path / "smoke",
        max_records_per_response=3,
        opener=opener,
    )
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["status"] == "transport_smoke_passed"
    assert result["hosts"] == HOSTS
    assert len(opened) == result["budgets"]["max_requests"] == 18
    assert result["response_schema_valid"] is True
    assert result["selected_count"] == 0
    assert "retrieval recall" in result["what_is_not_concluded"]
    assert (tmp_path / "smoke" / "live_smoke_result.json").is_file()


def test_live_smoke_preserves_malformed_response_failure(tmp_path: Path) -> None:
    class Malformed(_Response):
        def read(self, _limit: int):
            return b"not-json"

    result = run(
        topic="Neural optimal transport",
        output_root=tmp_path / "failed-smoke",
        opener=lambda url, timeout: Malformed(url),
    )
    assert result["status"] == "transport_smoke_failed"
    assert result["response_schema_valid"] is False
    assert result["failure_class"] == "invalid_seed_provider_response"
    recorded = json.loads((tmp_path / "failed-smoke" / "live_smoke_result.json").read_text())
    assert recorded == result
