from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from research_assistant.config import get_paths
from research_assistant.schemas.artifact import base_artifact, stable_id
from research_assistant.schemas.domain_templates import get_domain_template
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.storage.file_store import FileStore

DERIVATION_LIST_FIELDS = {"paper_claims", "assumptions", "derivation_steps", "unresolved_gaps", "required_experiments"}

EXPERIMENT_CHECKLIST_TEMPLATES: dict[str, dict[str, Any]] = {
    "gradient_checks": {
        "template_id": "gradient_checks",
        "name": "Gradient checks",
        "checklist": ["finite-difference spot check", "autodiff consistency", "scale and sign convention review"],
    },
    "conservation_checks": {
        "template_id": "conservation_checks",
        "name": "Conservation checks",
        "checklist": ["energy drift diagnostic", "symplectic integrator setting", "step-size sensitivity"],
    },
    "simulation_recovery": {
        "template_id": "simulation_recovery",
        "name": "Simulation recovery",
        "checklist": ["simulate known parameters", "recover posterior/estimator", "record failure modes"],
    },
    "posterior_calibration": {
        "template_id": "posterior_calibration",
        "name": "Posterior calibration",
        "checklist": ["coverage check", "rank histogram or SBC plan", "calibration limitations"],
    },
    "likelihood_sanity": {
        "template_id": "likelihood_sanity",
        "name": "Likelihood sanity checks",
        "checklist": ["normalization review", "edge-case likelihood values", "missing-data behavior"],
    },
}

SYNTHESIS_KINDS = {
    "monograph_exposition",
    "method_comparison_table",
    "assumptions_matrix",
    "implementation_implications",
}

IMPLEMENTATION_LINK_RELATIONSHIPS = {
    "equation-to-code",
    "theorem-assumption-to-test",
    "algorithm-to-implementation-checklist",
    "claim-to-experiment",
}


def _store(root: Path | None = None) -> FileStore:
    return FileStore(get_paths(root).local_research)


def artifact_paths(root: Path | None = None) -> dict[str, str]:
    paths = get_paths(root)
    return {
        "derivations": str(paths.derivations),
        "experiments": str(paths.experiments),
        "graph_reports": str(paths.graph_reports),
        "benchmarks": str(paths.benchmarks),
        "benchmark_runs": str(paths.benchmark_runs),
        "synthesis": str(paths.synthesis),
        "governance": str(paths.governance),
        "jobs": str(paths.jobs),
        "exports": str(paths.exports),
    }


def _path_for(root: Path | None, family: str, artifact_id: str) -> Path:
    paths = get_paths(root)
    base = {
        "derivation": paths.derivations,
        "experiment": paths.experiments,
        "graph_report": paths.graph_reports,
        "benchmark": paths.benchmarks,
        "benchmark_run": paths.benchmark_runs,
        "synthesis": paths.synthesis,
        "governance": paths.governance,
        "job": paths.jobs,
        "review_metadata": paths.review_metadata,
    }[family]
    return base / f"{artifact_id}.json"


def _read(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    return _store(root).read_json(path)


def _write(path: Path, payload: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    _store(root).write_json(path, payload)
    return payload


def list_experiment_checklists() -> list[dict[str, Any]]:
    return [
        {"template_id": row["template_id"], "name": row["name"], "checklist_count": len(row["checklist"])}
        for row in sorted(EXPERIMENT_CHECKLIST_TEMPLATES.values(), key=lambda item: item["template_id"])
    ]


def show_experiment_checklist(template_id: str) -> dict[str, Any]:
    if template_id not in EXPERIMENT_CHECKLIST_TEMPLATES:
        raise KeyError(f"unknown experiment checklist template {template_id}")
    return dict(EXPERIMENT_CHECKLIST_TEMPLATES[template_id])


def create_derivation(
    paper_id: str,
    *,
    title: str,
    template_id: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    template = get_domain_template(template_id) if template_id else None
    artifact_id = stable_id("derivation", paper_id, title, template_id or "")
    payload = {
        **base_artifact(
            artifact_type="derivation_worksheet",
            artifact_id=artifact_id,
            paper_id=paper_id,
            provenance={"created_by": "ra derivation-create", "domain_template_id": template_id},
            limitations=["Worksheet content is review material and is not accepted technical_audit."],
        ),
        "title": title,
        "domain_template": template,
        "paper_claims": [],
        "assumptions": [],
        "derivation_steps": [],
        "unresolved_gaps": [],
        "required_experiments": [],
        "accepted_into_technical_audit": False,
    }
    return _write(_path_for(root, "derivation", artifact_id), payload, root=root)


def show_derivation(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "derivation", artifact_id), root=root)


def update_derivation(artifact_id: str, field: str, value: str, *, root: Path | None = None) -> dict[str, Any]:
    if field not in DERIVATION_LIST_FIELDS:
        raise ValueError(f"derivation update field must be one of {sorted(DERIVATION_LIST_FIELDS)}")
    path = _path_for(root, "derivation", artifact_id)
    payload = _read(path, root=root)
    values = list(payload.get(field) or [])
    item_id = stable_id(field.removesuffix("s") or field, payload["artifact_id"], value)
    values.append({"id": item_id, "text": value, "review_status": "requires_human_review"})
    payload[field] = values
    return _write(path, payload, root=root)


def create_experiment(
    paper_id: str,
    *,
    claim_id: str,
    checklist_id: str,
    root: Path | None = None,
) -> dict[str, Any]:
    checklist = show_experiment_checklist(checklist_id)
    artifact_id = stable_id("experiment", paper_id, claim_id, checklist_id)
    payload = {
        **base_artifact(
            artifact_type="experiment_plan",
            artifact_id=artifact_id,
            paper_id=paper_id,
            provenance={"created_by": "ra experiment-create"},
            limitations=["Experiment results require separate review before supporting a paper claim."],
        ),
        "claim_id": claim_id,
        "checklist_template_id": checklist_id,
        "checklist": checklist["checklist"],
        "planned_diagnostics": [],
        "result_records": [],
        "acceptance_criteria": [],
        "status": "planned",
    }
    return _write(_path_for(root, "experiment", artifact_id), payload, root=root)


def show_experiment(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "experiment", artifact_id), root=root)


def link_claim_to_experiment(
    paper_id: str,
    *,
    claim_id: str,
    experiment_id: str,
    root: Path | None = None,
) -> dict[str, Any]:
    link = LinkRecord(
        id=stable_id("link", paper_id, claim_id, experiment_id, "claim-to-experiment"),
        paper_id=paper_id,
        target_type="experiment",
        target=experiment_id,
        relationship="claim-to-experiment",
        source_type="claim",
        source_ref=claim_id,
        target_ref=experiment_id,
        evidence_refs=[],
        review_status="requires_human_review",
    )
    _store(root).write_json(get_paths(root).links / f"{link.id}.json", link.to_dict())
    return link.to_dict()


def _normalized_title(title: str | None) -> str:
    return " ".join((title or "").lower().split())


def _identifier_buckets(nodes: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    buckets: dict[str, list[str]] = {}
    missing = []
    for node_id, node in nodes.items():
        identifiers = []
        if node.get("doi"):
            identifiers.append(f"doi:{str(node['doi']).lower()}")
        external_ids = node.get("external_ids") or {}
        if node.get("arxiv_id"):
            identifiers.append(f"arxiv:{node['arxiv_id']}")
        if external_ids.get("arxiv"):
            identifiers.append(f"arxiv:{external_ids['arxiv']}")
        if node.get("source") and node.get("source_id"):
            identifiers.append(f"{node['source']}:{node['source_id']}")
        title = _normalized_title(node.get("title"))
        if title:
            identifiers.append(f"title:{title}")
        if not identifiers:
            missing.append(node_id)
        for identifier in identifiers:
            buckets.setdefault(identifier, []).append(node_id)
    duplicates = [
        {"identifier": identifier, "node_ids": sorted(set(node_ids))}
        for identifier, node_ids in sorted(buckets.items())
        if len(set(node_ids)) > 1
    ]
    return duplicates, missing


def build_graph_report(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    graph_path = paths.local_research / "graphs" / "citations" / f"{paper_id}.json"
    graph = _store(root).read_json(graph_path) if graph_path.exists() else {"nodes": {}, "edges": [], "diagnostics": {"graph_missing": True}}
    nodes = graph.get("nodes") or {}
    duplicates, missing = _identifier_buckets(nodes)
    artifact_id = stable_id("graph_report", paper_id)
    payload = {
        **base_artifact(
            artifact_type="citation_graph_intelligence_report",
            artifact_id=artifact_id,
            paper_id=paper_id,
            provenance={"created_by": "ra graph-report-build", "graph_path": str(graph_path) if graph_path.exists() else None},
            limitations=["Citation intents, clusters, and trends are placeholders until reviewed."],
        ),
        "node_dedup_diagnostics": {
            "duplicate_identifiers": duplicates,
            "missing_identifier_node_ids": missing,
            "node_count": len(nodes),
        },
        "citation_intents": [
            {"edge": edge, "intent": "unknown", "review_status": "requires_human_review"}
            for edge in graph.get("edges") or []
        ],
        "cluster_trend_report": {
            "clusters": [],
            "trends": [],
            "status": "scaffold",
        },
        "source_graph_diagnostics": graph.get("diagnostics") or {},
    }
    return _write(_path_for(root, "graph_report", artifact_id), payload, root=root)


def show_graph_report(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "graph_report", artifact_id), root=root)


def _review_metadata_default(paper_id: str) -> dict[str, Any]:
    return {
        **base_artifact(
            artifact_type="department_review_metadata",
            artifact_id=paper_id,
            paper_id=paper_id,
            provenance={"created_by": "ra review-meta"},
            limitations=["Review metadata is local advisory state, not mathematical approval."],
        ),
        "owner": "",
        "steward": "",
        "reviewers": [],
        "workstream_tags": [],
        "review_history": [],
    }


def show_review_metadata(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    path = _path_for(root, "review_metadata", paper_id)
    if not path.exists():
        return _review_metadata_default(paper_id)
    return _read(path, root=root)


def set_review_metadata(
    paper_id: str,
    *,
    field: str,
    value: str,
    root: Path | None = None,
) -> dict[str, Any]:
    if field not in {"owner", "steward", "reviewers", "workstream_tags"}:
        raise ValueError("review metadata field must be owner, steward, reviewers, or workstream_tags")
    path = _path_for(root, "review_metadata", paper_id)
    payload = show_review_metadata(paper_id, root=root)
    if field in {"owner", "steward"}:
        payload[field] = value
    else:
        values = list(payload.get(field) or [])
        if value not in values:
            values.append(value)
        payload[field] = values
    payload.setdefault("review_history", []).append({"field": field, "value": value, "action": "set"})
    return _write(path, payload, root=root)


def list_review_metadata(*, root: Path | None = None) -> list[dict[str, Any]]:
    paths = get_paths(root)
    rows = []
    for path in sorted(paths.review_metadata.glob("*.json")):
        payload = _store(root).read_json(path)
        rows.append({
            "paper_id": payload.get("paper_id"),
            "owner": payload.get("owner"),
            "steward": payload.get("steward"),
            "reviewers": payload.get("reviewers") or [],
            "workstream_tags": payload.get("workstream_tags") or [],
        })
    return rows


def create_benchmark_manifest(
    manifest_id: str,
    *,
    family: str,
    fixture_paths: list[str],
    root: Path | None = None,
) -> dict[str, Any]:
    payload = {
        **base_artifact(
            artifact_type="benchmark_manifest",
            artifact_id=manifest_id,
            provenance={"created_by": "ra benchmark-manifest-create"},
            limitations=["Benchmark fixtures are local deterministic checks, not production parser certification."],
        ),
        "family": family,
        "fixture_paths": fixture_paths,
        "quality_checks": ["source_record_available", "extraction_count_scaffold"],
    }
    return _write(_path_for(root, "benchmark", manifest_id), payload, root=root)


def show_benchmark_manifest(manifest_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "benchmark", manifest_id), root=root)


def run_benchmark_manifest(manifest_id: str, *, root: Path | None = None) -> dict[str, Any]:
    manifest = show_benchmark_manifest(manifest_id, root=root)
    results = []
    for fixture in manifest.get("fixture_paths") or []:
        fixture_path = Path(fixture)
        if not fixture_path.is_absolute():
            fixture_path = get_paths(root).root / fixture_path
        exists = fixture_path.exists()
        results.append({
            "fixture_path": str(fixture_path),
            "status": "passed" if exists else "failed",
            "counts": {"files": 1 if exists else 0},
            "limitations": [] if exists else ["fixture path is unavailable"],
        })
    artifact_id = stable_id("benchmark_run", manifest_id)
    payload = {
        **base_artifact(
            artifact_type="benchmark_run",
            artifact_id=artifact_id,
            provenance={"created_by": "ra benchmark-run", "manifest_id": manifest_id},
            limitations=["Counts are fixture-level scaffolds until parser ground-truth scoring is added."],
        ),
        "manifest_id": manifest_id,
        "results": results,
        "status": "passed" if all(row["status"] == "passed" for row in results) else "failed",
    }
    return _write(_path_for(root, "benchmark_run", artifact_id), payload, root=root)


def propose_synthesis(
    paper_id: str,
    *,
    kind: str,
    root: Path | None = None,
) -> dict[str, Any]:
    if kind not in SYNTHESIS_KINDS:
        raise ValueError(f"synthesis kind must be one of {sorted(SYNTHESIS_KINDS)}")
    artifact_id = stable_id("synthesis", paper_id, kind)
    evidence_refs = []
    source_path = get_paths(root).papers_source / "records" / f"{paper_id}.json"
    if source_path.exists():
        source = _store(root).read_json(source_path)
        evidence_refs.extend([{"kind": "section", "labels": section.get("labels") or [], "title": section.get("title")} for section in source.get("sections") or []])
        evidence_refs.extend([{"kind": "equation", "labels": equation.get("labels") or []} for equation in source.get("equations") or []])
    payload = {
        **base_artifact(
            artifact_type="synthesis_proposal",
            artifact_id=artifact_id,
            paper_id=paper_id,
            provenance={"created_by": "ra synthesis-propose", "deterministic": True},
            limitations=["Proposal uses deterministic local evidence only and requires review."],
        ),
        "kind": kind,
        "evidence_refs": evidence_refs,
        "proposal_sections": [],
        "accepted_into_technical_audit": False,
    }
    return _write(_path_for(root, "synthesis", artifact_id), payload, root=root)


def show_synthesis(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "synthesis", artifact_id), root=root)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_governance_record(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    hashes = {}
    for label, path in {
        "summary": paths.summaries / f"{paper_id}.json",
        "metadata": paths.metadata / f"{paper_id}.json",
        "source_record": paths.papers_source / "records" / f"{paper_id}.json",
    }.items():
        if path.exists():
            hashes[label] = {"path": str(path), "sha256": _sha256_file(path)}
    artifact_id = stable_id("governance", paper_id)
    payload = {
        **base_artifact(
            artifact_type="governance_record",
            artifact_id=artifact_id,
            paper_id=paper_id,
            provenance={"created_by": "ra governance-build"},
            limitations=["Policy metadata is a local placeholder and does not authorize live provider calls."],
        ),
        "extraction_quality_metrics": {
            "summary_available": (paths.summaries / f"{paper_id}.json").exists(),
            "source_record_available": (paths.papers_source / "records" / f"{paper_id}.json").exists(),
        },
        "artifact_hashes": hashes,
        "provider_model_policy": {
            "live_model_calls_allowed": False,
            "allowed_providers": [],
            "policy_status": "placeholder",
        },
        "offline_safe": True,
    }
    return _write(_path_for(root, "governance", artifact_id), payload, root=root)


def show_governance_record(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "governance", artifact_id), root=root)


def create_job(
    *,
    job_type: str,
    paper_id: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    artifact_id = stable_id("job", job_type, paper_id or "")
    payload = {
        **base_artifact(
            artifact_type="job_status",
            artifact_id=artifact_id,
            paper_id=paper_id,
            provenance={"created_by": "ra job-create"},
            limitations=["Job records are status scaffolds; no background worker is implied."],
        ),
        "job_type": job_type,
        "status": "queued",
        "progress": {"completed": 0, "total": 0},
        "messages": [],
    }
    return _write(_path_for(root, "job", artifact_id), payload, root=root)


def show_job(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "job", artifact_id), root=root)


def dashboard_export(output: Path | None = None, *, root: Path | None = None) -> Path:
    paths = get_paths(root)
    out = output or (paths.exports / "dashboard_index.json")
    payload = {
        "artifact_paths": artifact_paths(root),
        "counts": {
            "summaries": len(list(paths.summaries.glob("*.json"))),
            "derivations": len(list(paths.derivations.glob("*.json"))),
            "experiments": len(list(paths.experiments.glob("*.json"))),
            "synthesis": len(list(paths.synthesis.glob("*.json"))),
            "governance": len(list(paths.governance.glob("*.json"))),
            "jobs": len(list(paths.jobs.glob("*.json"))),
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return out
