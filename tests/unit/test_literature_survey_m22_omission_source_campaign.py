from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest

from research_assistant.survey import m22_omission_source_campaign as runner
from research_assistant.survey.m20_arxiv_only_live_runner import M20ArxivOnlyLiveError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RAW_CANARY = b"M22-OMISSION-SOURCE-RAW-CANARY"


def _tar(rows: dict[str, bytes], *, special: tarfile.TarInfo | None = None) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in rows.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        if special is not None:
            archive.addfile(special)
    return stream.getvalue()


def _source(arxiv_id: str) -> bytes:
    main = rf"""
\documentclass{{article}}
\newtheorem{{theorem}}{{Theorem}}
\begin{{document}}
\section{{Method}}\label{{sec:method}}
Candidate {arxiv_id} {RAW_CANARY.decode()}.
\begin{{equation}}\label{{eq:method}}x=1\end{{equation}}
\begin{{theorem}}\label{{thm:method}}A result.\end{{theorem}}
\section{{Experiments}}
An evaluation.
\section{{Limitations}}
A limitation.
\end{{document}}
""".encode()
    return _tar({"main.tex": main, "references.bib": b"@article{ref,title={Reference}}"})


def _pdf_wrapper_source() -> bytes:
    return _tar({
        "arxiv.tex": (
            b"\\documentclass{article}\n\\usepackage{pdfpages}\n"
            b"\\begin{document}\n\\includepdf[pages=1-last]{paper.pdf}\n"
            b"\\end{document}\n"
        ),
        "paper.pdf": b"%PDF-1.4 synthetic body\n",
    })


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _downloader(
    calls: list[str],
    *,
    fail_id: str | None = None,
    pdf_wrapper_id: str | None = None,
    unsafe_id: str | None = None,
):
    def download(request: Any, *, destination: Path, max_bytes: int) -> dict[str, Any]:
        arxiv_id = request.full_url.rsplit("/", 1)[-1]
        calls.append(arxiv_id)
        assert request.full_url == f"https://arxiv.org/e-print/{arxiv_id}"
        assert 0 < max_bytes <= 50_000_000
        if arxiv_id == fail_id:
            raise M20ArxivOnlyLiveError("synthetic_source_unavailable")
        if arxiv_id == unsafe_id:
            raw = _tar({"../escape.tex": b"unsafe"})
        elif arxiv_id == pdf_wrapper_id:
            raw = _pdf_wrapper_source()
        else:
            raw = _source(arxiv_id)
        destination.write_bytes(raw)
        return {
            "size_bytes": len(raw),
            "sha256": _digest(raw),
            "http_status": 200,
            "content_type": "application/x-eprint-tar",
            "declared_content_length": len(raw),
            "final_url_observation": {
                "url_shape": "parsed",
                "scheme": "https",
                "hostname": "export.arxiv.org",
                "path": f"/src/{arxiv_id}",
                "userinfo_present": False,
                "port_present": False,
                "query_present": False,
                "fragment_present": False,
            },
            "final_url_matches_request": False,
        }

    return download


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fail_id: str | None = None,
    pdf_wrapper_id: str | None = None,
    unsafe_id: str | None = None,
) -> tuple[Path, dict[str, Any], list[str]]:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    calls: list[str] = []
    root = tmp_path / "fresh-m22-omission-source-root"
    result = runner.run_omission_source_campaign(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
        downloader=_downloader(
            calls,
            fail_id=fail_id,
            pdf_wrapper_id=pdf_wrapper_id,
            unsafe_id=unsafe_id,
        ),
        now=lambda: "2026-07-19T06:00:00+00:00",
    )
    return root, result, calls


def test_exact_five_requests_are_replayable_bounded_and_nonpromoting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, result, calls = _run(tmp_path, monkeypatch)

    assert calls == list(runner.CANDIDATE_IDS)
    assert len(calls) == len(set(calls)) == 5
    assert result["classification"] == "M22_OMISSION_SOURCE_INTAKE_PASSED"
    assert result["primary_criterion_passed"] is True
    assert result["requests_dispatched"] == 5
    assert result["retry_count"] == 0
    assert result["accepted_and_parsed_count"] == 5
    assert result["offline_replay_status"] == "passed"
    assert sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) <= 300_000_000
    replay = runner.replay_omission_source_campaign(root)
    assert replay["status"] == "passed"
    assert replay["legacy_execution_source_gaps"] == []

    claims = json.loads((root / "claim_support.json").read_text())
    statuses = json.loads((root / "source_status.json").read_text())
    assert claims["claims"] == []
    assert all(row["scholarly_classification"] == "NOT_CHECKED" for row in statuses["rows"])
    assert all(row["support_status"] == "SOURCE_GAP_BLOCKER" for row in statuses["rows"])
    assert RAW_CANARY not in b"".join(
        path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "source_members" not in path.parts and path.name != "accepted_source.body"
    )


def test_individual_source_failure_continues_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed_id = runner.CANDIDATE_IDS[1]
    root, result, calls = _run(tmp_path, monkeypatch, fail_id=failed_id)

    assert calls == list(runner.CANDIDATE_IDS)
    assert result["primary_criterion_passed"] is True
    assert result["source_failure_count"] == 1
    row = json.loads((root / "route_ledger.json").read_text())["rows"][1]
    assert row["status"] == "closed_source_failure"
    assert row["error_code"] == "synthetic_source_unavailable"
    assert row["retry_count"] == 0
    assert runner.replay_omission_source_campaign(root)["status"] == "passed"


def test_pdf_wrapper_is_a_closed_parse_gap_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gap_id = runner.CANDIDATE_IDS[2]
    root, result, calls = _run(tmp_path, monkeypatch, pdf_wrapper_id=gap_id)

    assert calls == list(runner.CANDIDATE_IDS)
    assert result["primary_criterion_passed"] is True
    assert result["source_parse_gap_count"] == 1
    row = json.loads((root / "route_ledger.json").read_text())["rows"][2]
    assert row["status"] == "closed_source_parse_gap"
    assert row["error_code"] == "SOURCE_AVAILABLE_TEXT_PARSE_GAP_PDF_FALLBACK_OUT_OF_SCOPE"


def test_unsafe_archive_is_a_campaign_veto_and_stops_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unsafe_id = runner.CANDIDATE_IDS[2]
    root, result, calls = _run(tmp_path, monkeypatch, unsafe_id=unsafe_id)

    assert calls == list(runner.CANDIDATE_IDS[:3])
    assert result["primary_criterion_passed"] is False
    assert result["campaign_veto"] == "source_member_path_invalid"
    rows = json.loads((root / "route_ledger.json").read_text())["rows"]
    assert rows[2]["status"] == "closed_source_failure"
    assert all(row["status"] == "not_dispatched_campaign_veto" for row in rows[3:])


def test_replay_rejects_source_and_claim_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)
    source = root / "candidates" / runner.CANDIDATE_IDS[0].replace(".", "_") / "accepted_source.body"
    original = source.read_bytes()
    source.write_bytes(b"tampered")
    with pytest.raises((runner.M22OmissionSourceError, M20ArxivOnlyLiveError)):
        runner.replay_omission_source_campaign(root)

    source.write_bytes(original)
    claims_path = root / "claim_support.json"
    claims = json.loads(claims_path.read_text())
    claims["claims"] = [{"unsupported": True}]
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n")
    with pytest.raises(runner.M22OmissionSourceError, match="claim_support_replay_mismatch"):
        runner.replay_omission_source_campaign(root)


def test_runner_has_no_provider_credential_or_pdf_interface() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8").casefold()
    assert "openalex" not in source
    assert "api_key" not in source
    assert "authorization" not in source
    assert "cookie" not in source
    assert '"pdf_fallback": false' in source
    assert source.count("downloader(") == 1


def test_replay_reconciles_exact_legacy_missing_balanced_field_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)
    manifest_path = root / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    helper = next(
        row for row in manifest["preserved_execution_sources"]
        if Path(row["relative_path"]).name == "bibtex_fields.py"
    )
    manifest["preserved_execution_sources"].remove(helper)
    (root / helper["relative_path"]).unlink()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (root / "artifact_inventory.json").write_bytes(runner._pretty(runner._inventory(root)))

    replay = runner.replay_omission_source_campaign(root)

    assert replay["status"] == "passed"
    assert replay["legacy_execution_source_gaps"] == ["bibtex_fields.py"]
