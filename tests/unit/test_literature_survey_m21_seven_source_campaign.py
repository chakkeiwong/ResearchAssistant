from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest

from research_assistant.survey import m21_seven_source_campaign as runner
from research_assistant.survey.m20_arxiv_only_live_runner import M20ArxivOnlyLiveError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RAW_CANARY = b"M21-SEVEN-SOURCE-RAW-CANARY"


def _source(arxiv_id: str) -> bytes:
    main = rf"""
\documentclass{{article}}
\newtheorem{{theorem}}{{Theorem}}
\begin{{document}}
\section{{Method}}\label{{sec:method}}
Candidate {arxiv_id} {RAW_CANARY.decode()}.
\begin{{equation}}\label{{eq:method}}x=1\end{{equation}}
\begin{{theorem}}\label{{thm:method}}A result.\end{{theorem}}
\citep{{ref}}
\end{{document}}
""".encode()
    bibliography = f"""
@article{{ref,
  title={{A source for {arxiv_id}}},
  eprint={{{arxiv_id}}}
}}
""".encode()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in {"main.tex": main, "references.bib": bibliography}.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return stream.getvalue()


def _pdf_wrapper_source() -> bytes:
    main = b"\\documentclass{article}\n\\usepackage{pdfpages}\n\\begin{document}\n\\includepdf[pages=1-last]{0_adam_main.pdf}\n\\end{document}\n"
    pdf = b"%PDF-1.4 synthetic retained body\n"
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in {"arxiv.tex": main, "0_adam_main.pdf": pdf}.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return stream.getvalue()


def _citation_only_source() -> bytes:
    main = b"\\documentclass{article}\n\\begin{document}\n\\cite{ref}\n\\bibliography{references}\n\\end{document}\n"
    bibliography = b"@article{ref,title={Metadata without technical structure}}\n"
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in {"main.tex": main, "references.bib": bibliography}.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return stream.getvalue()


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _downloader(
    calls: list[str],
    *,
    fail_id: str | None = None,
    crash_id: str | None = None,
    pdf_wrapper_id: str | None = None,
    citation_only_id: str | None = None,
):
    def download(request: Any, *, destination: Path, max_bytes: int) -> dict[str, Any]:
        arxiv_id = request.full_url.rsplit("/", 1)[-1]
        calls.append(arxiv_id)
        assert request.full_url == f"https://arxiv.org/e-print/{arxiv_id}"
        assert 0 < max_bytes <= runner.MAX_SOURCE_BYTES
        if arxiv_id == fail_id:
            raise M20ArxivOnlyLiveError("synthetic_source_unavailable")
        if arxiv_id == crash_id:
            raise RuntimeError("synthetic harness crash")
        if arxiv_id == pdf_wrapper_id:
            raw = _pdf_wrapper_source()
        elif arxiv_id == citation_only_id:
            raw = _citation_only_source()
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
    crash_id: str | None = None,
    pdf_wrapper_id: str | None = None,
    citation_only_id: str | None = None,
) -> tuple[Path, dict[str, Any], list[str]]:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    calls: list[str] = []
    root = tmp_path / "fresh-seven-source-root"
    result = runner.run_seven_source_campaign(
        repository_root=REPOSITORY_ROOT,
        output_root=root,
        downloader=_downloader(
            calls,
            fail_id=fail_id,
            crash_id=crash_id,
            pdf_wrapper_id=pdf_wrapper_id,
            citation_only_id=citation_only_id,
        ),
        now=lambda: "2026-07-18T08:00:00+00:00",
    )
    return root, result, calls


def test_all_success_is_exactly_seven_requests_and_replayable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, result, calls = _run(tmp_path, monkeypatch)

    assert calls == list(runner.CANDIDATE_IDS)
    assert result["classification"] == "M21_SEVEN_SOURCE_CAMPAIGN_PASSED"
    assert result["primary_criterion_passed"] is True
    assert result["requests_dispatched"] == 7
    assert result["retry_count"] == 0
    assert result["accepted_and_parsed_count"] == 7
    assert result["source_gap_count"] == 0
    assert result["offline_replay_status"] == "passed"
    assert runner.replay_seven_source_campaign(root)["status"] == "passed"

    ledger = json.loads((root / "route_ledger.json").read_text())
    assert [row["arxiv_id"] for row in ledger["rows"]] == list(runner.CANDIDATE_IDS)
    assert all(row["requests_dispatched"] == 1 for row in ledger["rows"])
    assert all(row["retry_count"] == 0 for row in ledger["rows"])
    assert all(row["status"] == "accepted_and_parsed" for row in ledger["rows"])


def test_accepted_sources_have_full_type_anchors_and_no_claim_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)
    claim_support = json.loads((root / "claim_support.json").read_text())
    assert claim_support["claims"] == []

    for arxiv_id in runner.CANDIDATE_IDS:
        candidate = root / "candidates" / arxiv_id.replace(".", "_")
        anchors = json.loads((candidate / "anchor_candidates.json").read_text())
        structured = json.loads((candidate / "structured_source.json").read_text())
        assert anchors["supported_claims"] == []
        assert anchors["ready_for_prose"] is False
        assert {row["anchor_type"] for row in anchors["anchors"]} == {
            "section",
            "equation",
            "theorem_like_block",
        }
        assert structured["arxiv_id"] == arxiv_id
        assert structured["raw_source_included"] is False


def test_individual_source_failure_continues_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed_id = runner.CANDIDATE_IDS[2]
    root, result, calls = _run(tmp_path, monkeypatch, fail_id=failed_id)

    assert calls == list(runner.CANDIDATE_IDS)
    assert result["primary_criterion_passed"] is True
    assert result["accepted_and_parsed_count"] == 6
    assert result["source_gap_count"] == 1
    ledger = json.loads((root / "route_ledger.json").read_text())
    failed = next(row for row in ledger["rows"] if row["arxiv_id"] == failed_id)
    assert failed["status"] == "closed_source_failure"
    assert failed["error_code"] == "synthetic_source_unavailable"
    assert failed["retry_count"] == 0
    candidate = root / "candidates" / failed_id.replace(".", "_")
    assert not any(path.is_file() for path in candidate.rglob("*"))
    assert runner.replay_seven_source_campaign(root)["status"] == "passed"


def test_pdf_wrapper_is_closed_as_text_parse_gap_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gap_id = runner.CANDIDATE_IDS[0]
    root, result, calls = _run(tmp_path, monkeypatch, pdf_wrapper_id=gap_id)

    assert calls == list(runner.CANDIDATE_IDS)
    assert result["primary_criterion_passed"] is True
    assert result["accepted_and_parsed_count"] == 6
    assert result["source_gap_count"] == 1
    route = json.loads((root / "route_ledger.json").read_text())
    row = route["rows"][0]
    assert row["status"] == "closed_source_parse_gap"
    assert row["error_code"] == "SOURCE_AVAILABLE_TEXT_PARSE_GAP_PDF_FALLBACK_OUT_OF_SCOPE"
    candidate = root / "candidates" / gap_id.replace(".", "_")
    structured = json.loads((candidate / "structured_source.json").read_text())
    anchors = json.loads((candidate / "anchor_candidates.json").read_text())
    assert structured["status"] == "source_available_text_parse_gap"
    assert anchors["status"] == "source_available_text_parse_gap"
    assert anchors["anchors"] == []
    replay = runner.replay_seven_source_campaign(root)
    assert replay["accepted_and_parsed_count"] == 6
    assert replay["source_parse_gap_count"] == 1
    assert replay["legacy_outcome_reconciliations"] == []


def test_replay_reconciles_only_exact_legacy_pdf_wrapper_misclassification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gap_id = runner.CANDIDATE_IDS[0]
    root, _, _ = _run(tmp_path, monkeypatch, pdf_wrapper_id=gap_id)
    candidate = root / "candidates" / gap_id.replace(".", "_")

    route_path = root / "route_ledger.json"
    route = json.loads(route_path.read_text())
    route["rows"][0]["status"] = "accepted_and_parsed"
    route["rows"][0]["error_code"] = None
    route_path.write_text(json.dumps(route, indent=2, sort_keys=True) + "\n")

    source_status_path = root / "source_status.json"
    source_status = json.loads(source_status_path.read_text())
    source_status["rows"][0].update(
        source_status="AVAILABLE_MACHINE_PARSED",
        outcome="accepted_and_parsed",
        error_code=None,
    )
    source_status_path.write_text(
        json.dumps(source_status, indent=2, sort_keys=True) + "\n"
    )

    structured_path = candidate / "structured_source.json"
    structured = json.loads(structured_path.read_text())
    structured["status"] = "available_machine_parsed"
    structured.pop("parse_gap_code")
    structured_path.write_text(json.dumps(structured, indent=2, sort_keys=True) + "\n")

    anchors_path = candidate / "anchor_candidates.json"
    anchors = json.loads(anchors_path.read_text())
    anchors["status"] = "machine_extracted_review_candidates"
    anchors.pop("parse_gap_code")
    anchors.pop("next_required_action")
    anchors_path.write_text(json.dumps(anchors, indent=2, sort_keys=True) + "\n")
    (root / "artifact_inventory.json").write_bytes(
        runner._pretty(runner._inventory(root))
    )

    replay = runner.replay_seven_source_campaign(root)
    assert replay["accepted_source_package_count"] == 7
    assert replay["accepted_and_parsed_count"] == 6
    assert replay["source_parse_gap_count"] == 1
    assert replay["legacy_outcome_reconciliations"] == [{
        "arxiv_id": gap_id,
        "recorded_outcome": "accepted_and_parsed",
        "reconciled_outcome": "closed_source_parse_gap",
        "parse_gap_code": "SOURCE_AVAILABLE_TEXT_PARSE_GAP_PDF_FALLBACK_OUT_OF_SCOPE",
    }]


def test_citations_without_technical_structure_are_a_zero_yield_parse_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gap_id = runner.CANDIDATE_IDS[1]
    root, result, _ = _run(tmp_path, monkeypatch, citation_only_id=gap_id)

    assert result["accepted_and_parsed_count"] == 6
    route = json.loads((root / "route_ledger.json").read_text())
    row = route["rows"][1]
    assert row["status"] == "closed_source_parse_gap"
    assert row["error_code"] == "SOURCE_AVAILABLE_TEXT_PARSE_GAP_ZERO_STRUCTURAL_YIELD"
    structured = json.loads(
        (root / "candidates" / gap_id.replace(".", "_") / "structured_source.json").read_text()
    )
    assert structured["citation_count"] == 1
    assert structured["status"] == "source_available_text_parse_gap"


def test_replay_rejects_final_artifact_inventory_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)
    terminal = root / "terminal_result.json"
    terminal.write_bytes(terminal.read_bytes() + b"\n")

    with pytest.raises(
        runner.M21SevenSourceError, match="artifact_inventory_replay_mismatch"
    ):
        runner.replay_seven_source_campaign(root)


def test_harness_failure_stops_later_dispatches_and_is_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    crashed_id = runner.CANDIDATE_IDS[3]
    root, result, calls = _run(tmp_path, monkeypatch, crash_id=crashed_id)

    assert calls == list(runner.CANDIDATE_IDS[:4])
    assert result["classification"] == "TERMINAL_CAMPAIGN_VETO"
    assert result["primary_criterion_passed"] is False
    assert result["campaign_veto"] == "unexpected_harness_error"
    ledger = json.loads((root / "route_ledger.json").read_text())
    assert ledger["rows"][3]["status"] == "closed_harness_failure"
    assert all(
        row["status"] == "not_dispatched_campaign_veto"
        for row in ledger["rows"][4:]
    )


def test_replay_rejects_accepted_body_and_aggregate_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)
    body = root / "candidates" / "1412_6980" / "accepted_source.body"
    original = body.read_bytes()
    body.write_bytes(b"tampered")
    with pytest.raises((runner.M21SevenSourceError, M20ArxivOnlyLiveError)):
        runner.replay_seven_source_campaign(root)

    body.write_bytes(original)
    source_status = root / "source_status.json"
    payload = json.loads(source_status.read_text())
    payload["rows"][0]["support_status"] = "PRIMARY_TECHNICAL_SUPPORT"
    source_status.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(runner.M21SevenSourceError, match="source_status_replay_mismatch"):
        runner.replay_seven_source_campaign(root)


def test_raw_canary_is_confined_to_accepted_bodies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)

    assert RAW_CANARY not in b"".join(
        path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name != "accepted_source.body"
    )


def test_manifest_preserves_exact_execution_sources_and_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)
    manifest = json.loads((root / "run_manifest.json").read_text())

    assert manifest["candidate_ids"] == list(runner.CANDIDATE_IDS)
    assert manifest["campaign_inputs"]["selection_sha256"] == hashlib.sha256(
        (REPOSITORY_ROOT / runner.SELECTION_PATH).read_bytes()
    ).hexdigest()
    assert len(manifest["preserved_execution_sources"]) == len(runner.EXECUTION_PATHS)
    for row in manifest["preserved_execution_sources"]:
        path = root / row["relative_path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_replay_rejects_preserved_execution_or_input_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _run(tmp_path, monkeypatch)
    manifest = json.loads((root / "run_manifest.json").read_text())
    runner_copy = next(
        root / row["relative_path"]
        for row in manifest["preserved_execution_sources"]
        if Path(row["relative_path"]).name == runner.RUNNER_PATH.name
    )
    original = runner_copy.read_bytes()
    runner_copy.write_bytes(b"tampered")
    with pytest.raises(runner.M21SevenSourceError, match="execution_source_tampered"):
        runner.replay_seven_source_campaign(root)

    runner_copy.write_bytes(original)
    selection_copy = next(
        root / row["relative_path"]
        for row in manifest["preserved_execution_sources"]
        if Path(row["relative_path"]).name == runner.SELECTION_PATH.name
    )
    selection_copy.write_bytes(b"tampered")
    with pytest.raises(runner.M21SevenSourceError, match="execution_source_tampered"):
        runner.replay_seven_source_campaign(root)


def test_active_runner_has_no_provider_credential_or_pdf_interface() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8").casefold()
    assert "openalex" not in source
    assert "api_key" not in source
    assert "authorization" not in source
    assert "cookie" not in source
    assert '"pdf_fallback": false' in source
    assert source.count("downloader(") == 1
