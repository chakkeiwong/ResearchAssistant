from __future__ import annotations

import json
from pathlib import Path
import time

from research_assistant.cli import main
from research_assistant.adapters.mcp_permissions import create_arxiv_batch_grant
from research_assistant.ingest.arxiv_batch import load_arxiv_candidate_file, plan_arxiv_batch_intake, run_arxiv_batch_intake


FIXTURE_CANDIDATE_FILE = Path("tests/fixtures/mcp/arxiv_candidates/query_transport_maps_hmc.json")


def test_arxiv_batch_plan_explicit_ids_is_stable_and_read_only(tmp_path: Path) -> None:
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    plan = plan_arxiv_batch_intake(
        arxiv_ids=["arxiv:2401.00002", "2401.00001", "2401.00001"],
        max_papers=5,
        destination="source",
        root=tmp_path,
    )
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    repeat = plan_arxiv_batch_intake(
        arxiv_ids=["2401.00001", "2401.00002"],
        max_papers=5,
        destination="source",
        root=tmp_path,
    )
    assert plan["status"] == "ready_for_grant"
    assert plan["arxiv_ids"] == ["2401.00001", "2401.00002"]
    assert plan["candidate_count"] == 2
    assert plan["writes_during_planning"] is False
    assert plan["plan_hash"] == repeat["plan_hash"]
    assert before == after


def test_arxiv_batch_plan_detects_existing_source_duplicate(tmp_path: Path) -> None:
    source_record = tmp_path / "local_research" / "papers" / "source" / "records" / "paper_arxiv_2401_fixture.json"
    source_record.parent.mkdir(parents=True)
    source_record.write_text(json.dumps({
        "paper_id": "paper_arxiv_2401_fixture",
        "status": "available",
        "source_type": "arxiv_latex",
        "provenance": {"arxiv_id": "2401.00001"},
    }))

    plan = plan_arxiv_batch_intake(arxiv_ids=["2401.00001"], max_papers=1, root=tmp_path)
    assert plan["status"] == "ready_for_grant"
    assert plan["candidates"][0]["duplicate_status"] == "possible_duplicate"
    assert plan["candidates"][0]["duplicate"]["source"] == "source_record"


def test_arxiv_batch_plan_blocks_query_only_until_discovery_exists(tmp_path: Path) -> None:
    plan = plan_arxiv_batch_intake(query="transport maps", arxiv_ids=[], max_papers=10, root=tmp_path)
    assert plan["status"] == "blocked"
    assert any(issue["code"] == "query_search_not_implemented" for issue in plan["issues"])


def test_arxiv_batch_candidate_file_inspect_and_plan_is_read_only(tmp_path: Path) -> None:
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    inspected = load_arxiv_candidate_file(FIXTURE_CANDIDATE_FILE)
    plan = plan_arxiv_batch_intake(candidate_file=FIXTURE_CANDIDATE_FILE, max_papers=2, root=tmp_path)
    repeat = plan_arxiv_batch_intake(candidate_file=FIXTURE_CANDIDATE_FILE, max_papers=2, root=tmp_path)
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))

    assert inspected["status"] == "ok"
    assert inspected["metadata"]["ordered_arxiv_ids"] == ["1903.03704", "2401.00001"]
    assert plan["status"] == "ready_for_grant"
    assert plan["arxiv_ids"] == ["1903.03704", "2401.00001"]
    assert plan["candidate_file"]["candidate_batch_id"] == "candidate_batch_transport_maps_hmc_fixture"
    assert plan["candidate_file"]["candidate_file_sha256"]
    assert plan["plan_hash"] == repeat["plan_hash"]
    assert before == after


def test_arxiv_batch_candidate_file_order_changes_plan_hash(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE_CANDIDATE_FILE.read_text())
    reversed_path = tmp_path / "reversed_candidates.json"
    payload["candidate_batch_id"] = "candidate_batch_transport_maps_hmc_reversed"
    payload["candidates"] = list(reversed(payload["candidates"]))
    reversed_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    original = plan_arxiv_batch_intake(candidate_file=FIXTURE_CANDIDATE_FILE, max_papers=2, root=tmp_path)
    reversed_plan = plan_arxiv_batch_intake(candidate_file=reversed_path, max_papers=2, root=tmp_path)

    assert original["status"] == "ready_for_grant"
    assert reversed_plan["status"] == "ready_for_grant"
    assert original["arxiv_ids"] == ["1903.03704", "2401.00001"]
    assert reversed_plan["arxiv_ids"] == ["2401.00001", "1903.03704"]
    assert original["plan_hash"] != reversed_plan["plan_hash"]


def test_arxiv_batch_candidate_file_rejects_malformed(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({
        "schema_version": "arxiv-query-candidates-v1",
        "candidate_batch_id": "bad",
        "candidates": [{"title": "missing id"}],
    }))
    inspected = load_arxiv_candidate_file(malformed)
    plan = plan_arxiv_batch_intake(candidate_file=malformed, max_papers=1, root=tmp_path)

    assert inspected["status"] == "blocked"
    assert any(issue["code"] == "candidate_missing_arxiv_id" for issue in inspected["issues"])
    assert plan["status"] == "blocked"


def test_arxiv_batch_plan_cli(tmp_path: Path, capsys) -> None:
    rc = main([
        "--root", str(tmp_path),
        "arxiv-batch", "plan",
        "--ids", "2401.00001,2401.00002",
        "--max-papers", "2",
        "--destination", "source",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["status"] == "ready_for_grant"
    assert payload["requires_grant"] is True
    assert payload["candidate_count"] == 2


def test_arxiv_batch_plan_cli_accepts_candidate_file(tmp_path: Path, capsys) -> None:
    rc = main([
        "--root", str(tmp_path),
        "arxiv-batch", "plan",
        "--candidate-file", str(FIXTURE_CANDIDATE_FILE),
        "--max-papers", "2",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["status"] == "ready_for_grant"
    assert payload["candidate_file"]["candidate_count"] == 2
    assert payload["candidate_file"]["ordered_arxiv_ids"] == ["1903.03704", "2401.00001"]


def test_granted_arxiv_batch_run_accepts_candidate_file(tmp_path: Path, monkeypatch) -> None:
    plan = plan_arxiv_batch_intake(candidate_file=FIXTURE_CANDIDATE_FILE, max_papers=2, root=tmp_path)
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        max_papers=2,
        root=tmp_path,
        arxiv_ids=plan["arxiv_ids"],
    )["grant"]

    def fake_fetch(arxiv_id: str, *, root: Path | None = None, paper_id: str | None = None):
        from research_assistant.source.structured_source import StructuredSourceRecord, source_record_path
        from research_assistant.storage.file_store import FileStore
        from research_assistant.config import get_paths

        paths = get_paths(root)
        record = StructuredSourceRecord(
            paper_id=paper_id or f"paper_{arxiv_id.replace('.', '_')}",
            source_type="arxiv_latex",
            status="available",
            primary_for_audit=True,
            provenance={"arxiv_id": arxiv_id},
        )
        FileStore(paths.local_research).write_json(source_record_path(paths.papers_source, record.paper_id), record.to_dict())
        return record

    monkeypatch.setattr("research_assistant.ingest.arxiv_batch.fetch_arxiv_structured_source", fake_fetch)
    result = run_arxiv_batch_intake(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        candidate_file=FIXTURE_CANDIDATE_FILE,
        root=tmp_path,
    )

    assert result["status"] == "completed"
    assert result["attempted_count"] == 2
    assert result["fetched_count"] == 2


def test_arxiv_batch_candidate_file_inspect_cli(capsys) -> None:
    rc = main([
        "arxiv-batch", "candidate-file", "inspect",
        "--path", str(FIXTURE_CANDIDATE_FILE),
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["status"] == "ok"
    assert payload["metadata"]["candidate_count"] == 2


def test_arxiv_batch_plan_cli_blocks_count_overflow(tmp_path: Path, capsys) -> None:
    rc = main([
        "--root", str(tmp_path),
        "arxiv-batch", "plan",
        "--ids", "2401.00001,2401.00002",
        "--max-papers", "1",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["status"] == "blocked"
    assert payload["issues"][0]["code"] == "max_papers_exceeded"


def test_granted_arxiv_batch_run_fetches_source_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    plan = plan_arxiv_batch_intake(arxiv_ids=["2401.00001"], max_papers=1, root=tmp_path)
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        max_papers=1,
        root=tmp_path,
        arxiv_ids=["2401.00001"],
    )["grant"]

    def fake_fetch(arxiv_id: str, *, root: Path | None = None, paper_id: str | None = None):
        from research_assistant.source.structured_source import StructuredSourceRecord, source_record_path
        from research_assistant.storage.file_store import FileStore
        from research_assistant.config import get_paths

        paths = get_paths(root)
        record = StructuredSourceRecord(
            paper_id=paper_id or "paper_arxiv_2401_00001",
            source_type="arxiv_latex",
            status="available",
            primary_for_audit=True,
            provenance={"arxiv_id": arxiv_id},
            sections=[{"title": "Method"}],
        )
        FileStore(paths.local_research).write_json(source_record_path(paths.papers_source, record.paper_id), record.to_dict())
        return record

    monkeypatch.setattr("research_assistant.ingest.arxiv_batch.fetch_arxiv_structured_source", fake_fetch)
    result = run_arxiv_batch_intake(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        arxiv_ids=["2401.00001"],
        root=tmp_path,
    )
    assert result["status"] == "completed"
    assert result["fetched_count"] == 1
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["review_policy"] == "review_material_only"
    assert manifest["results"][0]["status"] == "available"
    assert (tmp_path / "local_research" / "governance" / "mcp" / "audit" / f"{grant['grant_id']}.audit.jsonl").exists()


def test_granted_arxiv_batch_run_blocks_plan_hash_mismatch(tmp_path: Path) -> None:
    plan = plan_arxiv_batch_intake(arxiv_ids=["2401.00001"], max_papers=1, root=tmp_path)
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        max_papers=1,
        root=tmp_path,
        arxiv_ids=["2401.00001"],
    )["grant"]
    result = run_arxiv_batch_intake(
        grant_id=grant["grant_id"],
        plan_hash="wrong_hash",
        arxiv_ids=["2401.00001"],
        root=tmp_path,
    )
    assert result["status"] == "blocked"
    assert any(issue["code"] == "plan_hash_mismatch" for issue in result["issues"])


def test_granted_arxiv_batch_run_skips_duplicates_by_default(tmp_path: Path, monkeypatch) -> None:
    source_record = tmp_path / "local_research" / "papers" / "source" / "records" / "paper_existing.json"
    source_record.parent.mkdir(parents=True)
    source_record.write_text(json.dumps({
        "paper_id": "paper_existing",
        "status": "available",
        "source_type": "arxiv_latex",
        "provenance": {"arxiv_id": "2401.00001"},
    }))
    plan = plan_arxiv_batch_intake(arxiv_ids=["2401.00001"], max_papers=1, root=tmp_path)
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        max_papers=1,
        root=tmp_path,
        arxiv_ids=["2401.00001"],
    )["grant"]

    def fail_fetch(*args, **kwargs):
        raise AssertionError("duplicate should skip before fetch")

    monkeypatch.setattr("research_assistant.ingest.arxiv_batch.fetch_arxiv_structured_source", fail_fetch)
    result = run_arxiv_batch_intake(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        arxiv_ids=["2401.00001"],
        root=tmp_path,
    )
    assert result["status"] == "completed"
    assert result["fetched_count"] == 0
    assert result["skipped_duplicates"][0]["status"] == "skipped_duplicate"


def test_granted_arxiv_batch_rerun_skips_records_created_after_grant(tmp_path: Path, monkeypatch) -> None:
    plan = plan_arxiv_batch_intake(arxiv_ids=["2401.00001"], max_papers=1, root=tmp_path)
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        max_papers=1,
        root=tmp_path,
        arxiv_ids=["2401.00001"],
    )["grant"]

    def fake_fetch(arxiv_id: str, *, root: Path | None = None, paper_id: str | None = None):
        from research_assistant.source.structured_source import StructuredSourceRecord, source_record_path
        from research_assistant.storage.file_store import FileStore
        from research_assistant.config import get_paths

        paths = get_paths(root)
        record = StructuredSourceRecord(
            paper_id=paper_id or "paper_arxiv_2401_00001",
            source_type="arxiv_latex",
            status="available",
            primary_for_audit=True,
            provenance={"arxiv_id": arxiv_id},
        )
        FileStore(paths.local_research).write_json(source_record_path(paths.papers_source, record.paper_id), record.to_dict())
        return record

    monkeypatch.setattr("research_assistant.ingest.arxiv_batch.fetch_arxiv_structured_source", fake_fetch)
    first = run_arxiv_batch_intake(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        arxiv_ids=["2401.00001"],
        root=tmp_path,
    )

    def fail_fetch(*args, **kwargs):
        raise AssertionError("rerun duplicate should skip before fetch")

    monkeypatch.setattr("research_assistant.ingest.arxiv_batch.fetch_arxiv_structured_source", fail_fetch)
    rerun = run_arxiv_batch_intake(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        arxiv_ids=["2401.00001"],
        root=tmp_path,
    )

    assert first["status"] == "completed"
    assert first["fetched_count"] == 1
    assert rerun["status"] == "completed"
    assert rerun["fetched_count"] == 0
    assert rerun["skipped_duplicates"][0]["status"] == "skipped_duplicate"


def test_granted_arxiv_batch_run_handles_mocked_25_paper_scale(tmp_path: Path, monkeypatch) -> None:
    ids = [f"2401.{idx:05d}" for idx in range(1, 26)]
    plan = plan_arxiv_batch_intake(arxiv_ids=ids, max_papers=25, root=tmp_path)
    grant = create_arxiv_batch_grant(
        plan_hash=plan["plan_hash"],
        max_papers=25,
        root=tmp_path,
        arxiv_ids=ids,
    )["grant"]

    def fake_fetch(arxiv_id: str, *, root: Path | None = None, paper_id: str | None = None):
        from research_assistant.source.structured_source import StructuredSourceRecord, source_record_path
        from research_assistant.storage.file_store import FileStore
        from research_assistant.config import get_paths

        paths = get_paths(root)
        record = StructuredSourceRecord(
            paper_id=paper_id or f"paper_{arxiv_id.replace('.', '_')}",
            source_type="arxiv_latex",
            status="available",
            primary_for_audit=True,
            provenance={"arxiv_id": arxiv_id},
            sections=[{"title": "Method", "labels": ["sec:method"]}],
        )
        FileStore(paths.local_research).write_json(source_record_path(paths.papers_source, record.paper_id), record.to_dict())
        return record

    monkeypatch.setattr("research_assistant.ingest.arxiv_batch.fetch_arxiv_structured_source", fake_fetch)
    started = time.perf_counter()
    result = run_arxiv_batch_intake(
        grant_id=grant["grant_id"],
        plan_hash=plan["plan_hash"],
        arxiv_ids=ids,
        root=tmp_path,
    )
    elapsed = time.perf_counter() - started
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text())
    audit_events = (tmp_path / "local_research" / "governance" / "mcp" / "audit" / f"{grant['grant_id']}.audit.jsonl").read_text().splitlines()

    assert result["status"] == "completed"
    assert result["attempted_count"] == 25
    assert result["fetched_count"] == 25
    assert result["failures"] == []
    assert manifest["attempted_count"] == 25
    assert manifest["fetched_count"] == 25
    assert manifest["review_policy"] == "review_material_only"
    assert len(audit_events) >= 27
    assert manifest_path.stat().st_size > 0
    assert elapsed < 5
