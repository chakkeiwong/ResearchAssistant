from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest

from research_assistant.survey import m20_arxiv_only_live_runner as runner
from research_assistant.survey.m20_arxiv_backward_worker import (
    M20ArxivBackwardError,
    build_arxiv_backward_evidence,
    extract_backward_reference_candidates,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RAW_CANARY = b"ARXIV-ONLY-RAW-SOURCE-CANARY"


def _tar(
    rows: dict[str, bytes],
    *,
    special: tarfile.TarInfo | None = None,
) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in rows.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        if special is not None:
            archive.addfile(special)
    return stream.getvalue()


def _source(*, with_candidate: bool = True, large_irrelevant_bytes: int = 0) -> bytes:
    bibliography = RAW_CANARY
    if with_candidate:
        bibliography += b"""
@article{candidate,
  title={A backward candidate},
  doi={10.1234/backward.2026}
}
@misc{identifier_free,
  title={No admitted persistent identifier}
}
"""
    rows = {
        "main.tex": b"\\documentclass{article}\\begin{document}seed\\end{document}",
        "references.bib": bibliography,
    }
    if large_irrelevant_bytes:
        rows["figures/large.bin"] = b"x" * large_irrelevant_bytes
    return _tar(rows)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _downloader(
    body: bytes,
    *,
    final_host: str = "export.arxiv.org",
    content_type: str = "application/x-eprint-tar",
    calls: list[str] | None = None,
):
    def download(request: Any, *, destination: Path, max_bytes: int) -> dict[str, Any]:
        if calls is not None:
            calls.append(request.full_url)
        assert request.full_url == runner.SOURCE_URL
        assert max_bytes == 500_000_000
        destination.write_bytes(body)
        return {
            "size_bytes": len(body),
            "sha256": _digest(body),
            "http_status": 200,
            "content_type": content_type,
            "declared_content_length": len(body),
            "final_url_observation": {
                "url_shape": "parsed",
                "scheme": "https",
                "hostname": final_host,
                "path": "/src/2201.12220v3",
                "userinfo_present": False,
                "port_present": False,
                "query_present": True,
                "fragment_present": False,
            },
            "final_url_matches_request": False,
        }

    return download


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    downloader: Any | None = None,
) -> tuple[Path, dict[str, Any]]:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    tmp_path.mkdir(parents=True, exist_ok=True)
    root = tmp_path / "fresh-arxiv-only-root"
    result = runner.run_arxiv_only_attempt(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
        downloader=downloader or _downloader(_source()),
        now=lambda: "2026-07-18T04:30:00+00:00",
    )
    return root, result


def test_worker_ignores_large_irrelevant_regular_member_content() -> None:
    result = extract_backward_reference_candidates(
        _source(large_irrelevant_bytes=3_000_000),
        max_package_bytes=10_000_000,
        max_expanded_bytes=10_000_000,
        max_relevant_member_bytes=1_000_000,
        max_total_relevant_bytes=2_000_000,
    )

    assert result["candidate_count"] == 1
    assert result["archive_diagnostics"]["declared_expanded_bytes"] > 3_000_000
    assert {row["path"] for row in result["source_member_inventory"]} == {
        "main.tex",
        "references.bib",
    }


@pytest.mark.parametrize("name", ["../escape.tex", "/absolute.bib", "dir\\bad.tex"])
def test_worker_rejects_unsafe_paths(name: str) -> None:
    with pytest.raises(M20ArxivBackwardError, match="source_member_path_invalid"):
        extract_backward_reference_candidates(_tar({name: b"text"}))


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE])
def test_worker_rejects_links_and_devices(kind: bytes) -> None:
    special = tarfile.TarInfo("unsafe.tex")
    special.type = kind
    special.linkname = "target"
    with pytest.raises(M20ArxivBackwardError, match="source_member_type_forbidden"):
        extract_backward_reference_candidates(_tar({"main.tex": b"text"}, special=special))


def test_worker_enforces_expansion_and_relevant_member_caps() -> None:
    source = _source(large_irrelevant_bytes=2_000_000)
    with pytest.raises(M20ArxivBackwardError, match="source_package_expansion_cap_exceeded"):
        extract_backward_reference_candidates(source, max_expanded_bytes=1_000_000)

    large_bib = _tar({"large.bib": b"x" * 2_000_001})
    with pytest.raises(M20ArxivBackwardError, match="source_relevant_member_cap_exceeded"):
        extract_backward_reference_candidates(
            large_bib, max_relevant_member_bytes=2_000_000
        )


def test_worker_path_and_bytes_inputs_are_replay_equivalent(tmp_path: Path) -> None:
    source = _source()
    path = tmp_path / "source-package"
    path.write_bytes(source)

    assert build_arxiv_backward_evidence(source) == build_arxiv_backward_evidence(path)


def test_empty_backward_layer_is_a_veto() -> None:
    with pytest.raises(M20ArxivBackwardError, match="backward_candidates_empty"):
        build_arxiv_backward_evidence(_source(with_candidate=False))


def test_success_is_single_route_replayable_and_scholarly_nonpromoting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    root, result = _run(
        tmp_path,
        monkeypatch,
        downloader=_downloader(_source(), calls=calls),
    )

    assert calls == [runner.SOURCE_URL]
    assert result["classification"] == "M20_ARXIV_ONLY_PASSED"
    assert result["m20_revised_contract_passed"] is True
    assert result["backward_candidate_count"] == 1
    assert result["forward_coverage_status"] == "unavailable_out_of_scope"
    assert result["forward_coverage_blocking"] is False
    assert result["offline_replay_status"] == "passed"
    assert result["root_bytes_before_close_artifacts"] <= 500_000_000
    assert result["root_cap_enforced_after_close"] is True

    manifest = json.loads((root / "run_manifest.json").read_text())
    preserved = manifest["preserved_execution_sources"]
    assert {row["relative_path"] for row in preserved} == {
        "execution_sources/literature_survey_north_star_m20_arxiv_only_500mb_attempt_plan_2026-07-18.md",
        "execution_sources/literature_survey_north_star_m20_arxiv_only_governance_migration_2026-07-18.md",
        "execution_sources/m20_arxiv_backward_worker.py",
        "execution_sources/m20_arxiv_only_live_runner.py",
    }
    for row in preserved:
        copied = root / row["relative_path"]
        assert copied.stat().st_size == row["size_bytes"]
        assert _digest(copied.read_bytes()) == row["sha256"]

    ledger = json.loads((root / "route_ledger.json").read_text())
    assert ledger["request_limit"] == 1
    assert ledger["requests_dispatched"] == 1
    assert ledger["retry_count"] == 0
    assert [row["route"] for row in ledger["routes"]] == ["arxiv_source"]

    classifications = json.loads((root / "candidate_classifications.json").read_text())
    assert classifications["candidate_count"] == 1
    assert classifications["rows"][0]["scholarly_classification"] == "NOT_CHECKED"
    assert classifications["rows"][0]["support_status"] == "SOURCE_GAP_BLOCKER"

    forward = json.loads((root / "forward_snowball.json").read_text())
    assert forward == {
        "blocking": False,
        "limitation": "forward-citation coverage is unavailable and no completeness claim is permitted",
        "rows": [],
        "schema_version": "ra-literature-survey-m20-arxiv-only-live-v1-forward-snowball",
        "status": "unavailable_out_of_scope",
    }
    assert RAW_CANARY not in b"".join(
        path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "accepted_bodies" not in path.parts
    )


def test_replay_rejects_source_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, result = _run(tmp_path, monkeypatch)
    assert result["primary_criterion_passed"] is True
    (root / runner.BODY_RELATIVE_PATH).write_bytes(b"tampered")
    with pytest.raises(runner.M20ArxivOnlyLiveError, match="accepted_body_tampered"):
        runner.replay_arxiv_only_evidence(root)


def test_download_contract_rejects_bad_host_and_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for index, downloader in enumerate((
        _downloader(_source(), final_host="example.org"),
        _downloader(_source(), content_type="text/html"),
    )):
        root, result = _run(tmp_path / str(index), monkeypatch, downloader=downloader)
        assert result["classification"] == "TERMINAL_FAILURE_NO_RETRY"
        assert result["requests_dispatched"] == 1
        assert result["retry_count"] == 0
        assert json.loads((root / "route_ledger.json").read_text())["routes"][0]["status"] == "failed"
        assert not (root / runner.BODY_RELATIVE_PATH).exists()


def test_root_reserve_failure_removes_unaccepted_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "MAX_EVIDENCE_ROOT_BYTES", 100_000)
    monkeypatch.setattr(runner, "MIN_DERIVED_EVIDENCE_RESERVE_BYTES", 50_000)
    root, result = _run(tmp_path, monkeypatch)

    assert result["classification"] == "TERMINAL_FAILURE_NO_RETRY"
    assert result["continuation_veto_reason"] == "evidence_root_cap_exceeded"
    assert not (root / runner.BODY_RELATIVE_PATH).exists()


def test_active_runner_has_no_provider_or_credential_interface() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8").casefold()
    assert "openalex" not in source
    assert "api_key" not in source
    assert "authorization" not in source
    assert "cookie" not in source
    assert source.count("opener.open(") == 1
