from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from research_assistant.config import get_paths
from research_assistant.schemas.artifact import BASE_ARTIFACT_FIELDS, SCHEMA_VERSION, base_artifact, stable_id
from research_assistant.schemas.domain_templates import get_domain_template
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.storage.file_store import FileStore

DERIVATION_LIST_FIELDS = {"paper_claims", "assumptions", "derivation_steps", "unresolved_gaps", "required_experiments"}

BENCHMARK_EXPECTED_FIELDS = [
    "title",
    "authors",
    "year",
    "abstract",
    "section_headings",
    "equations",
    "theorem_like_blocks",
    "citations",
]
BENCHMARK_PASS_THRESHOLD = 0.60

READINESS_SOP_SECTIONS = [
    "paper_approval",
    "derivation_review",
    "experiment_evidence",
    "benchmark_gates",
    "escalation",
    "onboarding",
]

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


def _industrial_family_dirs(root: Path | None = None) -> dict[str, Path]:
    paths = get_paths(root)
    return {
        "review_metadata": paths.review_metadata,
        "derivations": paths.derivations,
        "experiments": paths.experiments,
        "graph_reports": paths.graph_reports,
        "benchmark_manifests": paths.benchmarks,
        "benchmark_runs": paths.benchmark_runs,
        "synthesis": paths.synthesis,
        "governance": paths.governance,
        "jobs": paths.jobs,
        "traceability": paths.traceability,
        "model_policies": paths.model_policies,
        "collaboration": paths.collaboration,
        "artifact_indices": paths.artifact_indices,
        "service_contracts": paths.service_contracts,
        "operations": paths.operations,
        "sops": paths.sops,
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
        "traceability": str(paths.traceability),
        "model_policies": str(paths.model_policies),
        "collaboration": str(paths.collaboration),
        "artifact_indices": str(paths.artifact_indices),
        "service_contracts": str(paths.service_contracts),
        "operations": str(paths.operations),
        "sops": str(paths.sops),
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
        "traceability": paths.traceability,
        "model_policy": paths.model_policies,
        "collaboration": paths.collaboration,
        "artifact_index": paths.artifact_indices,
        "service_contract": paths.service_contracts,
        "operations": paths.operations,
        "sop": paths.sops,
    }[family]
    return base / f"{artifact_id}.json"


def _read(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    return _store(root).read_json(path)


def _write(path: Path, payload: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    _store(root).write_json(path, payload)
    return payload


def _issue(severity: str, code: str, message: str, *, path: Path | None = None, family: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if path is not None:
        payload["path"] = str(path)
    if family is not None:
        payload["family"] = family
    return payload


def _count_issues(issues: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "blockers": len([issue for issue in issues if issue.get("severity") == "blocker"]),
        "warnings": len([issue for issue in issues if issue.get("severity") == "warning"]),
        "info": len([issue for issue in issues if issue.get("severity") == "info"]),
    }


def validate_artifact_record(
    payload: dict[str, Any],
    *,
    family: str,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    missing = sorted(BASE_ARTIFACT_FIELDS - set(payload))
    if missing:
        issues.append(_issue("blocker", "missing_base_fields", f"missing base artifact fields: {missing}", path=path, family=family))
    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue(
            "blocker",
            "schema_version_mismatch",
            f"expected schema_version {SCHEMA_VERSION}, found {payload.get('schema_version')!r}",
            path=path,
            family=family,
        ))
    if not payload.get("artifact_id"):
        issues.append(_issue("blocker", "missing_artifact_id", "artifact_id must be present", path=path, family=family))
    if not payload.get("artifact_type"):
        issues.append(_issue("blocker", "missing_artifact_type", "artifact_type must be present", path=path, family=family))
    if not isinstance(payload.get("provenance"), dict) or not payload.get("provenance"):
        issues.append(_issue("warning", "missing_provenance", "provenance should be a non-empty object", path=path, family=family))
    if not isinstance(payload.get("limitations"), list) or not payload.get("limitations"):
        issues.append(_issue("warning", "missing_limitations", "limitations should be a non-empty list", path=path, family=family))
    if payload.get("requires_human_review") is not True:
        issues.append(_issue("blocker", "human_review_not_required", "industrial artifacts must default to requires_human_review=true", path=path, family=family))
    if payload.get("review_status") not in {"requires_human_review", "draft", "needs_review"}:
        issues.append(_issue("warning", "unexpected_review_status", f"unexpected review_status {payload.get('review_status')!r}", path=path, family=family))
    if payload.get("accepted_into_technical_audit") is True:
        issues.append(_issue(
            "blocker",
            "generated_artifact_accepted",
            "generated industrial artifacts must not auto-populate accepted technical_audit",
            path=path,
            family=family,
        ))
    return issues


def validate_industrial_artifacts(*, root: Path | None = None) -> dict[str, Any]:
    families = _industrial_family_dirs(root)
    records: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    family_summary: dict[str, dict[str, Any]] = {}
    for family, base in families.items():
        family_records = []
        family_issues: list[dict[str, Any]] = []
        for path in sorted(base.glob("*.json")):
            record_issues: list[dict[str, Any]] = []
            payload: dict[str, Any] | None = None
            try:
                payload = _store(root).read_json(path)
            except json.JSONDecodeError as exc:
                record_issues.append(_issue("blocker", "invalid_json", f"invalid JSON: {exc}", path=path, family=family))
            except OSError as exc:
                record_issues.append(_issue("blocker", "unreadable_json", f"could not read JSON: {exc}", path=path, family=family))
            if payload is not None:
                record_issues.extend(validate_artifact_record(payload, family=family, path=path))
            counts = _count_issues(record_issues)
            family_record = {
                "family": family,
                "path": str(path),
                "artifact_id": payload.get("artifact_id") if payload else None,
                "artifact_type": payload.get("artifact_type") if payload else None,
                "paper_id": payload.get("paper_id") if payload else None,
                "schema_version": payload.get("schema_version") if payload else None,
                "requires_human_review": payload.get("requires_human_review") if payload else None,
                "issue_counts": counts,
                "issues": record_issues,
            }
            family_records.append(family_record)
            records.append(family_record)
            family_issues.extend(record_issues)
        family_summary[family] = {
            "count": len(family_records),
            "issue_counts": _count_issues(family_issues),
        }
        all_issues.extend(family_issues)
    counts = _count_issues(all_issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "industrial_validation_report",
        "status": "blocked" if counts["blockers"] else "passed",
        "issue_counts": counts,
        "family_summary": family_summary,
        "records": records,
        "trust_boundary": "Validation reports are operational diagnostics and do not approve mathematical conclusions.",
        "requires_human_review": True,
    }


def _artifact_record_matches(record: dict[str, Any], *, family: str | None, paper_id: str | None) -> bool:
    if family and record.get("family") != family:
        return False
    if paper_id and record.get("paper_id") != paper_id:
        return False
    return True


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
    _refresh_derivation_validation(payload)
    return _write(path, payload, root=root)


def add_derivation_notation(artifact_id: str, symbol: str, meaning: str, *, root: Path | None = None) -> dict[str, Any]:
    path = _path_for(root, "derivation", artifact_id)
    payload = _read(path, root=root)
    registry = dict(payload.get("notation_registry") or {})
    registry[symbol] = {"meaning": meaning, "review_status": "requires_human_review"}
    payload["notation_registry"] = registry
    payload.setdefault("version_history", []).append({"action": "add_notation", "symbol": symbol})
    _refresh_derivation_validation(payload)
    return _write(path, payload, root=root)


def link_derivation_steps(artifact_id: str, step_id: str, depends_on: str, *, root: Path | None = None) -> dict[str, Any]:
    path = _path_for(root, "derivation", artifact_id)
    payload = _read(path, root=root)
    dependencies = list(payload.get("step_dependencies") or [])
    edge = {"step_id": step_id, "depends_on": depends_on, "review_status": "requires_human_review"}
    if edge not in dependencies:
        dependencies.append(edge)
    payload["step_dependencies"] = dependencies
    payload.setdefault("version_history", []).append({"action": "link_steps", "step_id": step_id, "depends_on": depends_on})
    _refresh_derivation_validation(payload)
    return _write(path, payload, root=root)


def add_derivation_comment(artifact_id: str, target_id: str, comment: str, *, reviewer: str = "", root: Path | None = None) -> dict[str, Any]:
    path = _path_for(root, "derivation", artifact_id)
    payload = _read(path, root=root)
    comments = list(payload.get("reviewer_comments") or [])
    comments.append({
        "comment_id": stable_id("comment", artifact_id, target_id, comment),
        "target_id": target_id,
        "reviewer": reviewer,
        "comment": comment,
        "review_status": "requires_human_review",
    })
    payload["reviewer_comments"] = comments
    payload.setdefault("version_history", []).append({"action": "add_comment", "target_id": target_id})
    _refresh_derivation_validation(payload)
    return _write(path, payload, root=root)


def _derivation_known_ids(payload: dict[str, Any]) -> set[str]:
    ids: set[str] = {payload.get("artifact_id", "")}
    for field in DERIVATION_LIST_FIELDS:
        for item in payload.get(field) or []:
            if isinstance(item, dict) and item.get("id"):
                ids.add(item["id"])
    ids.discard("")
    return ids


def _refresh_derivation_validation(payload: dict[str, Any]) -> None:
    known_ids = _derivation_known_ids(payload)
    unresolved_dependencies = [
        edge for edge in payload.get("step_dependencies") or []
        if edge.get("step_id") not in known_ids or edge.get("depends_on") not in known_ids
    ]
    unresolved_comments = [
        comment for comment in payload.get("reviewer_comments") or []
        if comment.get("target_id") not in known_ids
    ]
    blocker_count = len(unresolved_dependencies) + len(unresolved_comments)
    payload["dependency_validation"] = {
        "known_ids": sorted(known_ids),
        "unresolved_dependencies": unresolved_dependencies,
        "unresolved_comment_targets": unresolved_comments,
        "blocker_count": blocker_count,
        "status": "blocked" if blocker_count else "ready_for_review",
        "requires_human_review": True,
        "limitations": ["Dependency validation checks worksheet references, not mathematical correctness."],
    }


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


def record_experiment_run(
    artifact_id: str,
    *,
    run_label: str,
    seed: str,
    environment: str,
    diagnostics: list[str] | None = None,
    result_summary: str = "",
    acceptance_status: str = "requires_review",
    dataset_hash: str = "",
    model_hash: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    path = _path_for(root, "experiment", artifact_id)
    payload = _read(path, root=root)
    runs = list(payload.get("result_records") or [])
    runs.append({
        "run_id": stable_id("run", artifact_id, run_label, seed),
        "run_label": run_label,
        "environment": environment,
        "seed": seed,
        "dataset_hash": dataset_hash,
        "model_hash": model_hash,
        "diagnostics": diagnostics or [],
        "result_summary": result_summary,
        "acceptance_status": acceptance_status,
        "review_status": "requires_human_review",
    })
    payload["result_records"] = runs
    payload["status"] = "run_recorded"
    _refresh_experiment_reproducibility(payload)
    return _write(path, payload, root=root)


def _score_experiment_run(run: dict[str, Any]) -> dict[str, Any]:
    required = ["environment", "seed", "dataset_hash", "model_hash", "diagnostics", "result_summary", "acceptance_status"]
    missing = [field for field in required if not run.get(field)]
    score = (len(required) - len(missing)) / len(required)
    blockers = [{"code": "missing_reproducibility_evidence", "field": field} for field in missing]
    return {
        "run_id": run.get("run_id"),
        "score": round(score, 3),
        "missing_fields": missing,
        "blockers": blockers,
        "status": "blocked" if blockers else "complete",
        "requires_human_review": True,
    }


def _refresh_experiment_reproducibility(payload: dict[str, Any]) -> None:
    run_scores = [_score_experiment_run(run) for run in payload.get("result_records") or []]
    blocker_count = sum(len(row["blockers"]) for row in run_scores)
    payload["reproducibility_evidence"] = {
        "run_count": len(run_scores),
        "run_scores": run_scores,
        "blocker_count": blocker_count,
        "status": "blocked" if blocker_count else ("ready_for_review" if run_scores else "no_runs_recorded"),
        "limitations": ["Completeness checks do not verify scientific correctness."],
        "requires_human_review": True,
    }


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


def _score_benchmark_expected(expected: dict[str, Any], *, fixture_exists: bool, is_json: bool) -> dict[str, Any]:
    if not fixture_exists:
        return {
            "score": 0.0,
            "passed": False,
            "field_scores": {},
            "missing_expected_fields": BENCHMARK_EXPECTED_FIELDS,
            "limitation_taxonomy": ["missing_fixture"],
        }
    if not is_json:
        return {
            "score": 0.0,
            "passed": False,
            "field_scores": {},
            "missing_expected_fields": BENCHMARK_EXPECTED_FIELDS,
            "limitation_taxonomy": ["unscored_fixture"],
        }
    field_scores = {
        field: {
            "available": bool(expected.get(field)),
            "status": "passed" if expected.get(field) else "missing",
        }
        for field in BENCHMARK_EXPECTED_FIELDS
    }
    missing = [field for field, row in field_scores.items() if not row["available"]]
    score = (len(BENCHMARK_EXPECTED_FIELDS) - len(missing)) / len(BENCHMARK_EXPECTED_FIELDS)
    taxonomy = []
    if missing:
        taxonomy.append("missing_expected_fields")
    if score < BENCHMARK_PASS_THRESHOLD:
        taxonomy.append("insufficient_score")
    return {
        "score": round(score, 3),
        "passed": score >= BENCHMARK_PASS_THRESHOLD,
        "threshold": BENCHMARK_PASS_THRESHOLD,
        "field_scores": field_scores,
        "missing_expected_fields": missing,
        "limitation_taxonomy": taxonomy,
    }


def run_benchmark_manifest(manifest_id: str, *, root: Path | None = None) -> dict[str, Any]:
    manifest = show_benchmark_manifest(manifest_id, root=root)
    results = []
    for fixture in manifest.get("fixture_paths") or []:
        fixture_path = Path(fixture)
        if not fixture_path.is_absolute():
            fixture_path = get_paths(root).root / fixture_path
        exists = fixture_path.exists()
        is_json = exists and fixture_path.suffix == ".json"
        expected = _store(root).read_json(fixture_path) if is_json else {}
        quality = _score_benchmark_expected(expected, fixture_exists=exists, is_json=is_json)
        results.append({
            "fixture_path": str(fixture_path),
            "status": "passed" if exists and quality["passed"] else "failed",
            "counts": {
                "files": 1 if exists else 0,
                "expected_sections": len(expected.get("section_headings") or []),
                "expected_equations": len(expected.get("equations") or []),
                "expected_theorems": len(expected.get("theorem_like_blocks") or []),
                "expected_citations": len(expected.get("citations") or []),
            },
            "quality_score": quality["score"],
            "quality_threshold": quality["threshold"],
            "quality_scores": quality["field_scores"],
            "missing_expected_fields": quality["missing_expected_fields"],
            "limitation_taxonomy": quality["limitation_taxonomy"],
            "limitations": quality["limitation_taxonomy"],
        })
    artifact_id = stable_id("benchmark_run", manifest_id)
    payload = {
        **base_artifact(
            artifact_type="benchmark_run",
            artifact_id=artifact_id,
            provenance={"created_by": "ra benchmark-run", "manifest_id": manifest_id},
            limitations=["Scores inspect expected fixture metadata completeness, not full parser correctness."],
        ),
        "manifest_id": manifest_id,
        "results": results,
        "status": "passed" if all(row["status"] == "passed" for row in results) else "failed",
        "pass_threshold": BENCHMARK_PASS_THRESHOLD,
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


def build_traceability_report(paper_id: str, *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    links = []
    for path in sorted(paths.links.glob("*.json")):
        link = _store(root).read_json(path)
        if link.get("paper_id") == paper_id:
            link["record_path"] = str(path)
            links.append(link)
    coverage: dict[str, dict[str, Any]] = {}
    for relationship in sorted(IMPLEMENTATION_LINK_RELATIONSHIPS):
        rows = [link for link in links if link.get("relationship") == relationship]
        target_checks = [_traceability_target_check(row, root=root) for row in rows]
        coverage[relationship] = {
            "count": len(rows),
            "reviewed_count": len([row for row in rows if row.get("review_status") == "approved"]),
            "requires_review_count": len([row for row in rows if row.get("review_status") != "approved"]),
            "existing_target_count": len([row for row in target_checks if row["exists"]]),
            "missing_target_count": len([row for row in target_checks if not row["exists"]]),
        }
        for row, check in zip(rows, target_checks):
            row["target_check"] = check
    missing_target_count = sum(row.get("target_check", {}).get("exists") is False for row in links)
    artifact_id = stable_id("traceability", paper_id)
    payload = {
        **base_artifact(
            artifact_type="paper_to_code_traceability_report",
            artifact_id=artifact_id,
            paper_id=paper_id,
            provenance={"created_by": "ra traceability-build"},
            limitations=["Coverage checks local target paths but does not prove code implements the paper correctly."],
        ),
        "coverage": coverage,
        "links": links,
        "target_health": {
            "missing_target_count": missing_target_count,
            "status": "blocked" if missing_target_count else "ready_for_review",
            "requires_human_review": True,
        },
    }
    return _write(_path_for(root, "traceability", artifact_id), payload, root=root)


def show_traceability_report(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "traceability", artifact_id), root=root)


def _traceability_target_check(link: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    target = str(link.get("target") or "")
    target_path_text = target.split(":", 1)[0] if target else ""
    target_path = Path(target_path_text) if target_path_text else None
    if target_path and not target_path.is_absolute():
        target_path = get_paths(root).root / target_path
    exists = bool(target_path and target_path.exists())
    suffix = target_path.suffix if target_path else ""
    target_kind = "test" if target_path and ("test" in target_path.parts or target_path.name.startswith("test_")) else "code"
    if suffix not in {".py", ".ipynb", ".jl", ".R", ".stan", ".m", ".cpp", ".h", ".hpp", ".md"}:
        target_kind = "other"
    return {
        "target_path": str(target_path) if target_path else "",
        "exists": exists,
        "target_kind": target_kind,
        "blocker": None if exists else "target_path_missing",
    }


def _latest_records(base: Path, *, root: Path | None = None) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(base.glob("*.json")):
        try:
            payload = _store(root).read_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        payload = dict(payload)
        payload["record_path"] = str(path)
        rows.append(payload)
    return rows


def _latest_by_created_at(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    return sorted(records, key=lambda row: row.get("created_at") or "")[-1]


def _sop_gate_report(*, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    sops = _latest_records(paths.sops, root=root)
    latest_sop = _latest_by_created_at(sops)
    warnings = []
    blockers = []
    if latest_sop is None:
        warnings.append("no_department_sop")
        sections = {}
    else:
        sections = latest_sop.get("sections") or {}
        for section in READINESS_SOP_SECTIONS:
            if section not in sections:
                warnings.append(f"missing_sop_section:{section}")
    artifact_presence = {
        "derivations": any(paths.derivations.glob("*.json")),
        "experiments": any(paths.experiments.glob("*.json")),
        "benchmark_runs": any(paths.benchmark_runs.glob("*.json")),
        "traceability": any(paths.traceability.glob("*.json")),
        "governance": any(paths.governance.glob("*.json")),
    }
    for family, present in artifact_presence.items():
        if not present:
            warnings.append(f"missing_artifact_family:{family}")
    return {
        "status": "blocked" if blockers else ("warnings" if warnings else "ready_for_review"),
        "sop_id": latest_sop.get("artifact_id") if latest_sop else None,
        "sections_present": sorted(sections),
        "artifact_presence": artifact_presence,
        "blockers": blockers,
        "warnings": warnings,
        "requires_human_review": True,
    }


def build_readiness_report(report_id: str = "industrial_readiness", *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    validation = validate_industrial_artifacts(root=root)
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if validation["issue_counts"]["blockers"]:
        blockers.append({"code": "artifact_validation_blockers", "count": validation["issue_counts"]["blockers"]})
    if validation["issue_counts"]["warnings"]:
        warnings.append({"code": "artifact_validation_warnings", "count": validation["issue_counts"]["warnings"]})

    model_policies = _latest_records(paths.model_policies, root=root)
    live_model_policies = [policy for policy in model_policies if policy.get("live_model_calls_allowed") is True]
    if live_model_policies:
        blockers.append({"code": "live_model_calls_allowed", "count": len(live_model_policies)})

    synthesis_records = _latest_records(paths.synthesis, root=root)
    if synthesis_records and not model_policies:
        warnings.append({"code": "synthesis_without_model_policy", "count": len(synthesis_records)})

    derivations = _latest_records(paths.derivations, root=root)
    derivation_blockers = sum((row.get("dependency_validation") or {}).get("blocker_count", 0) for row in derivations)
    if derivation_blockers:
        blockers.append({"code": "derivation_dependency_blockers", "count": derivation_blockers})

    experiments = _latest_records(paths.experiments, root=root)
    experiment_blockers = sum((row.get("reproducibility_evidence") or {}).get("blocker_count", 0) for row in experiments)
    if experiment_blockers:
        blockers.append({"code": "experiment_reproducibility_blockers", "count": experiment_blockers})
    no_run_count = len([row for row in experiments if not row.get("result_records")])
    if no_run_count:
        warnings.append({"code": "experiments_without_runs", "count": no_run_count})

    benchmark_runs = _latest_records(paths.benchmark_runs, root=root)
    failed_benchmark_runs = len([row for row in benchmark_runs if row.get("status") != "passed"])
    if failed_benchmark_runs:
        blockers.append({"code": "failed_benchmark_runs", "count": failed_benchmark_runs})

    traceability_reports = _latest_records(paths.traceability, root=root)
    missing_targets = sum((row.get("target_health") or {}).get("missing_target_count", 0) for row in traceability_reports)
    if missing_targets:
        blockers.append({"code": "traceability_missing_targets", "count": missing_targets})

    governance_records = [
        record for record in _latest_records(paths.governance, root=root)
        if record.get("artifact_type") == "governance_record"
    ]
    if not governance_records:
        warnings.append({"code": "missing_governance_records", "count": 1})
    if any(record.get("offline_safe") is not True for record in governance_records):
        blockers.append({"code": "governance_not_offline_safe", "count": 1})

    sop_gates = _sop_gate_report(root=root)
    warnings.extend({"code": warning, "count": 1} for warning in sop_gates["warnings"])
    blockers.extend({"code": blocker, "count": 1} for blocker in sop_gates["blockers"])

    status = "blocked" if blockers else ("warnings" if warnings else "ready_for_review")
    payload = {
        **base_artifact(
            artifact_type="industrial_readiness_report",
            artifact_id=report_id,
            provenance={"created_by": "ra industrial-readiness"},
            limitations=["Readiness is an operational gate report, not scientific or production approval."],
        ),
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "validation_summary": {
            "status": validation["status"],
            "issue_counts": validation["issue_counts"],
        },
        "policy_gates": {
            "live_model_calls_allowed": bool(live_model_policies),
            "model_policy_count": len(model_policies),
            "offline_safe": not live_model_policies,
        },
        "artifact_counts": {
            "derivations": len(derivations),
            "experiments": len(experiments),
            "benchmark_runs": len(benchmark_runs),
            "traceability": len(traceability_reports),
            "synthesis": len(synthesis_records),
            "governance": len(governance_records),
            "model_policies": len(model_policies),
        },
        "sop_gate_report": sop_gates,
        "next_actions": _readiness_next_actions(blockers, warnings),
    }
    return _write(_path_for(root, "governance", report_id), payload, root=root)


def show_readiness_report(report_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "governance", report_id), root=root)


def _readiness_next_actions(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[str]:
    actions = []
    blocker_codes = {row["code"] for row in blockers}
    warning_codes = {row["code"] for row in warnings}
    if "artifact_validation_blockers" in blocker_codes:
        actions.append("fix invalid or unsafe industrial artifact records")
    if "live_model_calls_allowed" in blocker_codes:
        actions.append("disable live model calls or obtain an explicit approved provider policy")
    if "derivation_dependency_blockers" in blocker_codes:
        actions.append("resolve derivation dependency and comment target references")
    if "experiment_reproducibility_blockers" in blocker_codes:
        actions.append("complete experiment run reproducibility evidence")
    if "failed_benchmark_runs" in blocker_codes:
        actions.append("review failed benchmark fixture quality scores")
    if "traceability_missing_targets" in blocker_codes:
        actions.append("fix missing code/test targets in traceability links")
    if "missing_governance_records" in warning_codes:
        actions.append("build governance records for active papers")
    if any(code.startswith("missing_sop_section") for code in warning_codes):
        actions.append("complete department SOP sections")
    if not actions:
        actions.append("continue human review of generated artifacts")
    return actions


def enrich_graph_report(artifact_id: str, *, root: Path | None = None) -> dict[str, Any]:
    path = _path_for(root, "graph_report", artifact_id)
    payload = _read(path, root=root)
    payload["graph_analytics"] = {
        "method_lineage": [],
        "influence_map": [],
        "competing_families": [],
        "trend_signals": [],
        "open_question_clusters": [],
        "review_status": "requires_human_review",
        "limitations": ["Analytics are deterministic placeholders until classified and reviewed."],
    }
    for intent in payload.get("citation_intents") or []:
        intent.setdefault("intent_candidates", ["background", "method_use", "comparison", "extension"])
        intent.setdefault("classification_status", "unclassified")
    return _write(path, payload, root=root)


def create_model_policy(policy_id: str, *, root: Path | None = None) -> dict[str, Any]:
    payload = {
        **base_artifact(
            artifact_type="model_provider_policy",
            artifact_id=policy_id,
            provenance={"created_by": "ra model-policy create"},
            limitations=["Default policy blocks live model calls until department approval."],
        ),
        "live_model_calls_allowed": False,
        "allowed_providers": [],
        "allowed_models": [],
        "prompt_registry_required": True,
        "privacy_review_required": True,
        "evaluation_required": True,
    }
    return _write(_path_for(root, "model_policy", policy_id), payload, root=root)


def show_model_policy(policy_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "model_policy", policy_id), root=root)


def check_synthesis_policy(policy_id: str, *, root: Path | None = None) -> dict[str, Any]:
    policy = show_model_policy(policy_id, root=root)
    return {
        "policy_id": policy_id,
        "live_model_calls_allowed": policy.get("live_model_calls_allowed") is True,
        "status": "blocked" if not policy.get("live_model_calls_allowed") else "allowed",
        "requires_human_review": True,
        "limitations": policy.get("limitations") or [],
    }


def create_collaboration_workspace(workspace_id: str, *, root: Path | None = None) -> dict[str, Any]:
    payload = {
        **base_artifact(
            artifact_type="department_collaboration_workspace",
            artifact_id=workspace_id,
            provenance={"created_by": "ra collaboration create"},
            limitations=["Local JSON collaboration records are not concurrency-safe multi-user infrastructure."],
        ),
        "users": [],
        "roles": [],
        "assignments": [],
        "comments": [],
        "event_history": [],
    }
    return _write(_path_for(root, "collaboration", workspace_id), payload, root=root)


def show_collaboration_workspace(workspace_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "collaboration", workspace_id), root=root)


def update_collaboration_workspace(
    workspace_id: str,
    *,
    action: str,
    value: str,
    target: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    path = _path_for(root, "collaboration", workspace_id)
    payload = _read(path, root=root)
    if action == "add-user":
        payload.setdefault("users", []).append({"user_id": value, "review_status": "requires_human_review"})
    elif action == "add-role":
        payload.setdefault("roles", []).append({"role": value, "review_status": "requires_human_review"})
    elif action == "assign":
        payload.setdefault("assignments", []).append({"target": target, "assignee": value, "review_status": "requires_human_review"})
    elif action == "comment":
        payload.setdefault("comments", []).append({"target": target, "comment": value, "review_status": "requires_human_review"})
    else:
        raise ValueError("collaboration action must be add-user, add-role, assign, or comment")
    payload.setdefault("event_history", []).append({"action": action, "target": target, "value": value})
    return _write(path, payload, root=root)


def build_artifact_index(index_id: str = "local_artifact_index", *, root: Path | None = None) -> dict[str, Any]:
    paths = get_paths(root)
    families = {
        "summaries": paths.summaries,
        "links": paths.links,
        **_industrial_family_dirs(root),
    }
    validation = validate_industrial_artifacts(root=root)
    validation_by_path = {record["path"]: record for record in validation["records"]}
    inventory = {}
    schema_versions = {}
    for family, base in families.items():
        records = []
        for path in sorted(base.glob("*.json")):
            try:
                record = _store(root).read_json(path)
            except (json.JSONDecodeError, OSError) as exc:
                records.append({
                    "family": family,
                    "path": str(path),
                    "artifact_id": None,
                    "paper_id": None,
                    "schema_version": None,
                    "artifact_type": None,
                    "review_status": None,
                    "requires_human_review": None,
                    "issue_counts": {"blockers": 1, "warnings": 0, "info": 0},
                    "read_error": str(exc),
                })
                schema_versions.setdefault("unreadable", 0)
                schema_versions["unreadable"] += 1
                continue
            validation_record = validation_by_path.get(str(path), {})
            records.append({
                "family": family,
                "path": str(path),
                "artifact_id": record.get("artifact_id") or record.get("id"),
                "paper_id": record.get("paper_id") or (record.get("id") if family == "summaries" else None),
                "schema_version": record.get("schema_version"),
                "artifact_type": record.get("artifact_type"),
                "review_status": record.get("review_status"),
                "requires_human_review": record.get("requires_human_review"),
                "issue_counts": validation_record.get("issue_counts", {"blockers": 0, "warnings": 0, "info": 0}),
            })
            schema_versions.setdefault(record.get("schema_version", "unknown"), 0)
            schema_versions[record.get("schema_version", "unknown")] += 1
        inventory[family] = {"count": len(records), "records": records}
    payload = {
        **base_artifact(
            artifact_type="artifact_index",
            artifact_id=index_id,
            provenance={"created_by": "ra artifact-index build"},
            limitations=["Index is a point-in-time local JSON inventory, not a transactional database."],
        ),
        "inventory": inventory,
        "schema_versions": schema_versions,
        "validation_summary": {
            "status": validation["status"],
            "issue_counts": validation["issue_counts"],
            "family_summary": validation["family_summary"],
        },
        "migration_needed": bool({"unknown", "unreadable"} & set(schema_versions)) or validation["issue_counts"]["blockers"] > 0,
    }
    return _write(_path_for(root, "artifact_index", index_id), payload, root=root)


def show_artifact_index(index_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "artifact_index", index_id), root=root)


def query_artifact_index(
    index_id: str = "local_artifact_index",
    *,
    family: str | None = None,
    paper_id: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    index = show_artifact_index(index_id, root=root)
    records = []
    for inventory_family, payload in (index.get("inventory") or {}).items():
        for record in payload.get("records") or []:
            row = dict(record)
            row.setdefault("family", inventory_family)
            if _artifact_record_matches(row, family=family, paper_id=paper_id):
                records.append(row)
    return {
        "index_id": index_id,
        "filters": {"family": family, "paper_id": paper_id},
        "count": len(records),
        "records": records,
        "validation_status": (index.get("validation_summary") or {}).get("status"),
        "requires_human_review": True,
    }


def export_tool_contract(contract_id: str = "local_tool_contract", *, root: Path | None = None) -> dict[str, Any]:
    commands = [
        {"command": "industrial-validate", "inputs": [], "output": "artifact validation JSON"},
        {"command": "industrial-readiness", "inputs": ["build", "show"], "output": "industrial readiness JSON"},
        {"command": "full-scale-plan", "inputs": ["phases", "phase-show", "registry-build", "registry-show", "usefulness-build", "readiness-build"], "output": "full-scale implementation planning JSON"},
        {"command": "domain-templates", "inputs": ["list", "show"], "output": "domain template JSON"},
        {"command": "derivation", "inputs": ["create", "show", "append", "notation", "link-steps", "comment"], "output": "derivation worksheet JSON"},
        {"command": "experiment", "inputs": ["create", "show", "record-run", "link-claim"], "output": "experiment JSON"},
        {"command": "graph-report", "inputs": ["build", "show", "enrich"], "output": "citation intelligence JSON"},
        {"command": "traceability", "inputs": ["build", "show"], "output": "paper-to-code coverage JSON"},
        {"command": "model-policy", "inputs": ["create", "show", "check-synthesis"], "output": "policy JSON"},
        {"command": "collaboration", "inputs": ["create", "show", "update"], "output": "collaboration JSON"},
        {"command": "artifact-index", "inputs": ["build", "show", "query"], "output": "index JSON"},
        {"command": "operations-policy", "inputs": ["create", "show"], "output": "ops policy JSON"},
        {"command": "sop", "inputs": ["create", "show"], "output": "SOP JSON"},
        {"command": "dashboard-export", "inputs": ["--output"], "output": "dashboard readiness JSON"},
    ]
    payload = {
        **base_artifact(
            artifact_type="service_tool_contract",
            artifact_id=contract_id,
            provenance={"created_by": "ra tool-contract export"},
            limitations=["Contract describes local CLI/backend surfaces; it is not a running server."],
        ),
        "commands": commands,
        "trust_boundary": "All generated outputs require human review unless explicitly approved by a separate workflow.",
        "dashboard_summary_keys": ["artifact_paths", "counts", "schema_version"],
    }
    return _write(_path_for(root, "service_contract", contract_id), payload, root=root)


def show_tool_contract(contract_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "service_contract", contract_id), root=root)


def create_operations_policy(policy_id: str = "department_operations_policy", *, root: Path | None = None) -> dict[str, Any]:
    payload = {
        **base_artifact(
            artifact_type="security_compliance_operations_policy",
            artifact_id=policy_id,
            provenance={"created_by": "ra operations-policy create"},
            limitations=["Operational controls are placeholders until department policy owners approve them."],
        ),
        "auth": {"status": "placeholder", "required_before_server": True},
        "secrets": {"status": "placeholder", "no_secrets_in_repo": True},
        "provider_allowlist": [],
        "license_tracking": {"status": "placeholder"},
        "monitoring": {"status": "placeholder"},
        "offline_safe": True,
        "network_authorized": False,
    }
    return _write(_path_for(root, "operations", policy_id), payload, root=root)


def show_operations_policy(policy_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "operations", policy_id), root=root)


def create_department_sop(sop_id: str = "department_research_sop", *, root: Path | None = None) -> dict[str, Any]:
    sections = {
        "paper_approval": ["identity validated", "source evidence reviewed", "technical_audit explicitly approved"],
        "derivation_review": ["notation registered", "dependencies checked", "unresolved gaps recorded"],
        "experiment_evidence": ["environment captured", "seeds recorded", "diagnostics reviewed"],
        "benchmark_gates": ["fixtures scored", "limitations recorded", "regressions reviewed"],
        "escalation": ["security/policy issues escalated", "mathematical gaps assigned"],
        "onboarding": ["artifact contracts reviewed", "trust boundary understood"],
    }
    payload = {
        **base_artifact(
            artifact_type="department_standard_operating_procedure",
            artifact_id=sop_id,
            provenance={"created_by": "ra sop create"},
            limitations=["SOP is a draft scaffold and requires department review before enforcement."],
        ),
        "sections": sections,
        "review_gates": {
            "papers": "human approval required",
            "derivations": "reviewer signoff required",
            "experiments": "diagnostic review required",
            "synthesis": "policy and source review required",
        },
    }
    return _write(_path_for(root, "sop", sop_id), payload, root=root)


def show_department_sop(sop_id: str, *, root: Path | None = None) -> dict[str, Any]:
    return _read(_path_for(root, "sop", sop_id), root=root)


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
    validation = validate_industrial_artifacts(root=root)
    readiness_records = [
        record for record in _latest_records(paths.governance, root=root)
        if record.get("artifact_type") == "industrial_readiness_report"
    ]
    latest_readiness = _latest_by_created_at(readiness_records)
    payload = {
        "artifact_paths": artifact_paths(root),
        "counts": {
            "summaries": len(list(paths.summaries.glob("*.json"))),
            "derivations": len(list(paths.derivations.glob("*.json"))),
            "experiments": len(list(paths.experiments.glob("*.json"))),
            "synthesis": len(list(paths.synthesis.glob("*.json"))),
            "governance": len(list(paths.governance.glob("*.json"))),
            "jobs": len(list(paths.jobs.glob("*.json"))),
            "traceability": len(list(paths.traceability.glob("*.json"))),
            "model_policies": len(list(paths.model_policies.glob("*.json"))),
            "collaboration": len(list(paths.collaboration.glob("*.json"))),
            "artifact_indices": len(list(paths.artifact_indices.glob("*.json"))),
            "service_contracts": len(list(paths.service_contracts.glob("*.json"))),
            "operations": len(list(paths.operations.glob("*.json"))),
            "sops": len(list(paths.sops.glob("*.json"))),
        },
        "schema_version": "industrial-platform-v1",
        "validation_summary": {
            "status": validation["status"],
            "issue_counts": validation["issue_counts"],
        },
        "readiness_summary": {
            "available": latest_readiness is not None,
            "status": latest_readiness.get("status") if latest_readiness else "not_built",
            "blocker_count": len(latest_readiness.get("blockers") or []) if latest_readiness else 0,
            "warning_count": len(latest_readiness.get("warnings") or []) if latest_readiness else 0,
            "record_path": latest_readiness.get("record_path") if latest_readiness else None,
        },
        "next_actions": latest_readiness.get("next_actions") if latest_readiness else ["run industrial-readiness build"],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return out
