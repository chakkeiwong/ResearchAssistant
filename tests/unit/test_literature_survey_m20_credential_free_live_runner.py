from __future__ import annotations

import io
import json
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from research_assistant.survey import m20_credential_free_live_runner as runner


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RAW_MARKER = b"RAW-SOURCE-CONTENT-MUST-STAY-IN-ACCEPTED-BODY"


def _source(*, include_reference: bool = True) -> bytes:
    bibliography = RAW_MARKER
    if include_reference:
        bibliography += b"""
@article{reference,
  title={A bounded backward candidate},
  doi={10.1234/backward.2024}
}
"""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in {
            "main.tex": b"\\documentclass{article}\\begin{document}seed\\end{document}",
            "references.bib": bibliography,
        }.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return stream.getvalue()


def _forward(*, works: list[dict[str, Any]] | None = None, cost: float = 0.0001) -> bytes:
    rows = [{
        "id": "https://openalex.org/W999",
        "display_name": "A bounded forward candidate",
        "doi": "https://doi.org/10.1234/forward.2024",
        "publication_year": 2024,
        "cited_by_count": 2,
        "referenced_works": ["https://openalex.org/W4226072009"],
    }] if works is None else works
    return json.dumps({
        "meta": {"count": len(rows), "page": 1, "per_page": 10, "cost_usd": cost},
        "results": rows,
        "group_by": [],
    }, sort_keys=True).encode()


def _transport(
    *,
    source: bytes | None = None,
    forward: bytes | None = None,
    source_final_url: str = runner.SOURCE_URL,
    calls: list[str] | None = None,
):
    source_body = _source() if source is None else source
    forward_body = _forward() if forward is None else forward

    def dispatch(request: Any, *, route: str, max_bytes: int):
        if calls is not None:
            calls.append(route)
        headers = {key.casefold() for key, _ in request.header_items()}
        assert headers == {"accept", "user-agent"}
        assert "authorization" not in headers
        assert "cookie" not in headers
        if route == "arxiv_source":
            assert request.full_url == runner.SOURCE_URL
            assert max_bytes == 20_000_000
            return source_body, source_final_url, 200, "application/x-eprint-tar"
        assert request.full_url == runner.OPENALEX_URL
        assert max_bytes == 2_000_000
        return forward_body, runner.OPENALEX_URL, 200, "application/json"

    return dispatch


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> tuple[Path, dict[str, Any]]:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    tmp_path.mkdir(parents=True, exist_ok=True)
    root = tmp_path / "fresh-live-root"
    result = runner.run_live_successor(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
        now=lambda: "2026-07-18T01:02:03+00:00",
        **kwargs,
    )
    return root, result


def test_success_retains_two_bodies_replays_and_writes_scholarly_ledgers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    root, result = _run(tmp_path, monkeypatch, transport=_transport(calls=calls))

    assert calls == ["arxiv_source", "openalex_forward"]
    assert result["classification"] == "CAPABILITY_PASSED"
    assert result["reported_cost_usd"] == "0.0001"
    assert result["offline_replay_status"] == "passed"
    assert result["backward_candidate_count"] == 1
    assert result["forward_candidate_count"] == 1
    assert sorted(path.name for path in (root / "accepted_bodies").iterdir()) == [
        "arxiv-source.body",
        "openalex-forward.json",
    ]
    for name in (
        "source_support.json",
        "citation_venue_metadata.json",
        "backward_snowball.json",
        "forward_snowball.json",
        "claim_support.json",
        "omitted_paper_risks.json",
    ):
        assert json.loads((root / name).read_text())

    assert RAW_MARKER not in b"".join(
        path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "accepted_bodies" not in path.parts
    )


def test_existing_output_root_is_rejected_before_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    root = tmp_path / "existing"
    root.mkdir()
    calls: list[str] = []

    with pytest.raises(runner.M20CredentialFreeLiveError, match="output_root_not_fresh"):
        runner.run_live_successor(
            repository_root=REPOSITORY_ROOT,
            output_root=root,
            transport=_transport(calls=calls),
        )
    assert calls == []


def test_redirect_handler_allows_one_exact_arxiv_host_hop_and_rejects_other_hosts() -> None:
    handler = runner._BoundedRedirectHandler("arxiv_source")
    request = runner._request("arxiv_source")
    redirected = handler.redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://export.arxiv.org/src/2201.12220v3?download=1",
    )
    assert isinstance(redirected, urllib.request.Request)
    assert redirected.full_url == "https://export.arxiv.org/src/2201.12220v3?download=1"

    forbidden = runner._BoundedRedirectHandler("arxiv_source")
    with pytest.raises(runner.M20CredentialFreeLiveError, match="response_redirect_forbidden"):
        forbidden.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://example.org/e-print/2201.12220v3",
        )

    secret_bearing = runner._BoundedRedirectHandler("arxiv_source")
    try:
        secret_bearing.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://user:secret@example.org/source?api_key=secret",
        )
    except runner.M20CredentialFreeLiveError as exc:
        serialized = json.dumps(exc.details)
        assert "secret" not in serialized
        assert "api_key" not in serialized
        assert exc.details["final_url"]["hostname"] == "example.org"


def test_source_cap_or_redirect_failure_stops_before_openalex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for index, transport in enumerate((
        _transport(source=b"x" * 20_000_001),
        _transport(source_final_url="https://example.org/source"),
    )):
        root, result = _run(tmp_path / str(index), monkeypatch, transport=transport)
        assert result["classification"] == "TERMINAL_FAILURE_NO_RETRY"
        assert result["requests_dispatched"] == 1
        assert json.loads((root / "route_ledger.json").read_text())["retry_count"] == 0


@pytest.mark.parametrize(
    ("source", "forward", "error", "requests_dispatched"),
    [
        (_source(include_reference=False), _forward(), "backward_candidates_empty", 1),
        (_source(), _forward(works=[]), "forward_candidates_empty", 2),
        (_source(), _forward(cost=0.001), "forward_cost_contradiction", 2),
    ],
)
def test_evidence_vetoes_close_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: bytes,
    forward: bytes,
    error: str,
    requests_dispatched: int,
) -> None:
    root, result = _run(
        tmp_path,
        monkeypatch,
        transport=_transport(source=source, forward=forward),
    )

    assert result["classification"] == "TERMINAL_FAILURE_NO_RETRY"
    assert result["continuation_veto_reason"] == error
    assert result["requests_dispatched"] == requests_dispatched
    assert result["retry_count"] == 0
    assert (root / "terminal_result.json").is_file()


def test_offline_replay_rejects_body_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, result = _run(tmp_path, monkeypatch, transport=_transport())
    assert result["primary_criterion_passed"] is True
    (root / "accepted_bodies" / "openalex-forward.json").write_bytes(b"{}")

    with pytest.raises(runner.M20CredentialFreeLiveError, match="accepted_body_tampered"):
        runner.replay_live_evidence(root)


def test_offline_replay_rejects_route_ledger_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, result = _run(tmp_path, monkeypatch, transport=_transport())
    assert result["primary_criterion_passed"] is True
    ledger_path = root / "route_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    ledger["routes"][1]["request_headers"].append("authorization")
    ledger_path.write_text(json.dumps(ledger))

    with pytest.raises(runner.M20CredentialFreeLiveError, match="route_ledger_invalid"):
        runner.replay_live_evidence(root)


def test_allowed_source_redirect_query_is_not_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "SERVER-REDIRECT-QUERY-SECRET"
    root, result = _run(
        tmp_path,
        monkeypatch,
        transport=_transport(
            source_final_url=f"https://export.arxiv.org/src/2201.12220v3?token={secret}"
        ),
    )

    assert result["primary_criterion_passed"] is True
    retained = b"".join(path.read_bytes() for path in root.rglob("*") if path.is_file())
    assert secret.encode() not in retained
    route = json.loads((root / "route_ledger.json").read_text())["routes"][0]
    assert "final_url" not in route
    assert route["final_url_observation"]["hostname"] == "export.arxiv.org"
    assert route["final_url_observation"]["query_present"] is True
    assert route["final_url_matches_request"] is False


def test_module_has_no_credential_or_environment_lookup_interface() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "OPENALEX_API_KEY" not in source
    assert "getenv" not in source
    assert "environ.get" in source  # CPU-only environment assertion only.
    assert "Authorization" not in source
    assert "Cookie" not in source
