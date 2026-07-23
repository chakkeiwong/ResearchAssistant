"""Bounded, replayable topic-to-central-paper campaign authority."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

from research_assistant.core_utils import atomic_write_bytes
from research_assistant.survey.artifact_lineage import assert_public_write_path_allowed
from research_assistant.survey.central_papers_capability import (
    CentralPapersCapability,
    FileObservationCapability,
    OpenAlexArxivCentralPapersCapability,
    capability_manifest,
    validate_capability_manifest,
    validate_observations,
)
from research_assistant.survey.central_papers_evidence import (
    CLASSIFIER_VERSION,
    LEDGER_NAMES,
    NONCLAIMS,
    derive_campaign_evidence,
)
from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from research_assistant.survey.snowball_round import build_snowball_round
from research_assistant.survey.topic_contract import (
    build_topic_contract,
    topic_contract_sha256,
    validate_topic_contract,
)


CAMPAIGN_CONTRACT_SCHEMA = "ra-survey-central-papers-campaign-v1"
CHECKPOINT_SCHEMA = "ra-survey-central-papers-checkpoint-v1"
EVIDENCE_MANIFEST_SCHEMA = "ra-survey-central-papers-evidence-manifest-v1"
REPORT_SCHEMA = "ra-survey-central-papers-report-v1"
MANIFEST_SCHEMA = "ra-survey-central-papers-manifest-v1"

DEFAULT_BUDGET = {
    "max_candidates": 25,
    "max_metadata_records": 300,
    "max_metadata_requests": 24,
    "max_rounds": 3,
    "max_source_attempts": 12,
    "max_total_source_bytes": 96_000_000,
}
TERMINAL_FILES = (
    "centrality_assessment.json",
    "centrality_evidence.json",
    "evidence_construction_manifest.json",
    "campaign_report.json",
    "snowball_decision.json",
)


def _fail(code: str, message: str) -> None:
    raise MissionStateError(code, message)


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_central_papers_campaign", f"{label} is not readable JSON") from exc
    if not isinstance(value, dict):
        _fail("invalid_central_papers_campaign", f"{label} must be an object")
    return value


def _write_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        _fail("central_papers_output_exists", f"refusing to replace campaign artifact: {path}")
    atomic_write_bytes(path, pretty_json_bytes(value))


def _regular(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise MissionStateError("invalid_central_papers_campaign", f"{label} is missing") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        _fail("invalid_central_papers_campaign", f"{label} must be a regular non-symlink file")


def _normalized_budget(value: dict[str, Any] | None) -> dict[str, int]:
    budget = dict(DEFAULT_BUDGET if value is None else value)
    if set(budget) != set(DEFAULT_BUDGET):
        _fail("invalid_central_papers_budget", "campaign budget fields are not exact")
    for field, number in budget.items():
        if type(number) is not int or number <= 0:
            _fail("invalid_central_papers_budget", f"{field} must be a positive integer")
    if budget["max_candidates"] > 300 or budget["max_rounds"] > 20:
        _fail("invalid_central_papers_budget", "campaign cardinality cap is exceeded")
    return {field: budget[field] for field in sorted(budget)}


def build_campaign_contract(
    topic_contract: dict[str, Any],
    *,
    capability_fingerprint: str,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = validate_topic_contract(topic_contract)
    value = {
        "schema_version": CAMPAIGN_CONTRACT_SCHEMA,
        "topic_contract": contract,
        "topic_contract_sha256": topic_contract_sha256(contract),
        "capability_fingerprint": capability_fingerprint,
        "budget": _normalized_budget(budget),
        "classifier_version": CLASSIFIER_VERSION,
        "metadata_priority_can_promote": False,
        "benchmark_labels_consumed": False,
        "what_is_not_concluded": NONCLAIMS,
    }
    return validate_campaign_contract(value)


def validate_campaign_contract(value: Any) -> dict[str, Any]:
    expected = {
        "schema_version", "topic_contract", "topic_contract_sha256",
        "capability_fingerprint", "budget", "classifier_version",
        "metadata_priority_can_promote", "benchmark_labels_consumed",
        "what_is_not_concluded",
    }
    if not isinstance(value, dict) or set(value) != expected:
        _fail("invalid_central_papers_campaign", "campaign contract fields are not exact")
    if value["schema_version"] != CAMPAIGN_CONTRACT_SCHEMA:
        _fail("invalid_central_papers_campaign", "campaign contract schema is unsupported")
    topic = validate_topic_contract(value["topic_contract"])
    if value["topic_contract_sha256"] != topic_contract_sha256(topic):
        _fail("invalid_central_papers_campaign", "campaign topic binding differs")
    fingerprint = value["capability_fingerprint"]
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
        character not in "0123456789abcdef" for character in fingerprint
    ):
        _fail("invalid_central_papers_campaign", "capability fingerprint is invalid")
    if value["classifier_version"] != CLASSIFIER_VERSION:
        _fail("invalid_central_papers_campaign", "classifier version is unsupported")
    if value["metadata_priority_can_promote"] is not False:
        _fail("invalid_central_papers_campaign", "metadata promotion must remain disabled")
    if value["benchmark_labels_consumed"] is not False:
        _fail("invalid_central_papers_campaign", "campaign reports benchmark-label consumption")
    if value["what_is_not_concluded"] != NONCLAIMS:
        _fail("invalid_central_papers_campaign", "campaign nonclaims differ")
    return {
        **value,
        "topic_contract": topic,
        "budget": _normalized_budget(value["budget"]),
    }


def campaign_contract_sha256(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(validate_campaign_contract(value)))


def _validate_budget(observations: dict[str, Any], budget: dict[str, int]) -> None:
    consumption = observations["budget_consumption"]
    if len(observations["candidates"]) > budget["max_candidates"]:
        _fail("central_papers_budget_exceeded", "candidate budget is exceeded")
    if any(
        candidate["discovery_round"] >= budget["max_rounds"]
        for candidate in observations["candidates"]
    ):
        _fail("central_papers_budget_exceeded", "discovery round budget is exceeded")
    limits = {
        "metadata_records": "max_metadata_records",
        "metadata_requests": "max_metadata_requests",
        "source_attempts": "max_source_attempts",
        "source_bytes": "max_total_source_bytes",
    }
    for observed, maximum in limits.items():
        if consumption[observed] > budget[maximum]:
            _fail("central_papers_budget_exceeded", f"{observed} budget is exceeded")


def _checkpoint(
    contract: dict[str, Any],
    capability: dict[str, Any],
    observations: dict[str, Any],
    *,
    round_index: int,
    prior_checkpoint_sha256: str | None,
) -> dict[str, Any]:
    projected = {
        **observations,
        "candidates": [
            candidate for candidate in observations["candidates"]
            if candidate["discovery_round"] <= round_index
        ],
    }
    return {
        "schema_version": CHECKPOINT_SCHEMA,
        "round_index": round_index,
        "campaign_contract_sha256": campaign_contract_sha256(contract),
        "capability_manifest_sha256": sha256_bytes(canonical_json_bytes(capability)),
        "prior_checkpoint_sha256": prior_checkpoint_sha256,
        "observations_sha256": sha256_bytes(canonical_json_bytes(projected)),
        "observations": projected,
        "stop_candidate": "observation_round_recorded",
    }


def _load_checkpoint(root: Path, contract: dict[str, Any], capability: dict[str, Any]) -> dict[str, Any]:
    rounds_root = root / "rounds"
    try:
        paths = sorted(rounds_root.glob("round-*.json"))
    except OSError as exc:
        raise MissionStateError("invalid_central_papers_checkpoint", "round checkpoint directory is unreadable") from exc
    if not paths:
        _fail("invalid_central_papers_checkpoint", "no round checkpoint exists")
    expected = {
        "schema_version", "round_index", "campaign_contract_sha256",
        "capability_manifest_sha256", "prior_checkpoint_sha256",
        "observations_sha256", "observations", "stop_candidate",
    }
    prior_digest = None
    prior_ids: set[str] = set()
    observations = None
    for index, path in enumerate(paths):
        _regular(path, f"round {index} checkpoint")
        if path.name != f"round-{index:03d}.json":
            _fail("invalid_central_papers_checkpoint", "round checkpoint sequence is not contiguous")
        value = _load(path, f"round {index} checkpoint")
        if set(value) != expected or value["schema_version"] != CHECKPOINT_SCHEMA or value["round_index"] != index:
            _fail("invalid_central_papers_checkpoint", "round checkpoint fields or schema are invalid")
        if value["campaign_contract_sha256"] != campaign_contract_sha256(contract):
            _fail("invalid_central_papers_checkpoint", "round checkpoint campaign binding differs")
        if value["capability_manifest_sha256"] != sha256_bytes(canonical_json_bytes(capability)):
            _fail("invalid_central_papers_checkpoint", "round checkpoint capability binding differs")
        if value["prior_checkpoint_sha256"] != prior_digest:
            _fail("invalid_central_papers_checkpoint", "round checkpoint chain differs")
        observations = validate_observations(
            value["observations"],
            expected_topic_contract_sha256=contract["topic_contract_sha256"],
            expected_capability_fingerprint=contract["capability_fingerprint"],
        )
        current_ids = {candidate["paper_id"] for candidate in observations["candidates"]}
        if not prior_ids <= current_ids:
            _fail("invalid_central_papers_checkpoint", "round checkpoint removed prior candidates")
        if value["observations_sha256"] != sha256_bytes(canonical_json_bytes(observations)):
            _fail("invalid_central_papers_checkpoint", "round checkpoint observation binding differs")
        _validate_budget(observations, contract["budget"])
        prior_ids = current_ids
        prior_digest = sha256_bytes(path.read_bytes())
    assert observations is not None
    return observations


def _snowball_decision(
    contract: dict[str, Any], observations: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    candidates = observations["candidates"]
    observed_round = max((candidate["discovery_round"] for candidate in candidates), default=0)
    observed_ids = [candidate["paper_id"] for candidate in candidates]
    backward_rows = [
        entry for candidate in candidates for entry in candidate["source"]["bibliography"]
    ]
    backward_status = "available" if backward_rows else (
        "empty" if any(candidate["source"]["status"] == "available" for candidate in candidates)
        else "not_available"
    )
    forward_statuses = {candidate["forward_citation_status"] for candidate in candidates}
    if "available" in forward_statuses:
        forward_status = "available"
    elif forward_statuses and forward_statuses <= {"empty"}:
        forward_status = "empty"
    else:
        forward_status = "not_available"
    return build_snowball_round(
        topic_contract_sha256=contract["topic_contract_sha256"],
        round_index=observed_round + 1,
        prior_paper_ids=observed_ids,
        observed_paper_ids=observed_ids,
        high_or_critical_open_risk_ids=result["diagnostics"]["open_risk_ids"],
        required_roles_covered=not result["diagnostics"]["uncovered_roles"],
        backward_status=backward_status,
        forward_status=forward_status,
        requests_used=observations["budget_consumption"]["metadata_requests"],
        max_requests=contract["budget"]["max_metadata_requests"],
        max_rounds=contract["budget"]["max_rounds"],
    )


def _evidence_manifest(
    root: Path,
    campaign: dict[str, Any],
    ledgers: dict[str, dict[str, Any]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    checkpoint_paths = sorted((root / "rounds").glob("round-*.json"))
    if not checkpoint_paths:
        _fail("invalid_central_papers_checkpoint", "no round checkpoint exists")
    return {
        "schema_version": EVIDENCE_MANIFEST_SCHEMA,
        "campaign_contract_sha256": campaign_contract_sha256(campaign),
        "checkpoint_sha256": sha256_bytes(checkpoint_paths[-1].read_bytes()),
        "ledger_sha256": {
            name: sha256_bytes(canonical_json_bytes(ledgers[name])) for name in LEDGER_NAMES
        },
        "centrality_evidence_sha256": sha256_bytes(canonical_json_bytes(evidence)),
        "classifier_version": CLASSIFIER_VERSION,
        "benchmark_labels_consumed": False,
    }


def _report(
    contract: dict[str, Any], observations: dict[str, Any], result: dict[str, Any],
    snowball: dict[str, Any],
) -> dict[str, Any]:
    assessment = result["assessment"]
    dispositions = {
        verdict: sorted(
            row["paper_id"] for row in assessment["assessments"] if row["verdict"] == verdict
        )
        for verdict in sorted({row["verdict"] for row in assessment["assessments"]})
    }
    open_risks = result["diagnostics"]["open_risk_ids"]
    if observations["discovery_status"] in {"not_available", "empty"}:
        stop_reason = f"discovery_{observations['discovery_status']}"
    else:
        stop_reason = snowball["reason"]
    return {
        "schema_version": REPORT_SCHEMA,
        "status": "completed_with_open_risks" if open_risks else "completed",
        "topic": contract["topic_contract"]["topic"],
        "topic_contract_sha256": contract["topic_contract_sha256"],
        "campaign_contract_sha256": campaign_contract_sha256(contract),
        "dispositions": dispositions,
        "uncovered_roles": result["diagnostics"]["uncovered_roles"],
        "open_risks": open_risks,
        "provider_statuses": observations["provider_statuses"],
        "budget": contract["budget"],
        "budget_consumption": observations["budget_consumption"],
        "rounds_completed": max(
            (candidate["discovery_round"] for candidate in observations["candidates"]),
            default=0,
        ) + 1,
        "stop_reason": stop_reason,
        "snowball_status": snowball["status"],
        "artifact_paths": {
            "assessment": "centrality_assessment.json",
            "evidence": "centrality_evidence.json",
            "ledgers": "ledgers",
            "manifest": "campaign_manifest.json",
        },
        "metadata_priority_used_for_promotion": False,
        "benchmark_labels_consumed": False,
        "next_required_actions": [
            "inspect open source and omission risks before treating the candidate set as review-ready"
        ],
        "what_is_not_concluded": NONCLAIMS,
    }


def run_central_papers_campaign(
    *,
    topic: str,
    output_dir: Path,
    confirm_public_discovery: bool = False,
    resume: bool = False,
    observation_bundle: Path | None = None,
    capability: CentralPapersCapability | None = None,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run or resume a bounded campaign; capability observations are collected once."""
    assert_public_write_path_allowed(output_dir)
    root = output_dir.absolute()
    if capability is not None and observation_bundle is not None:
        _fail("invalid_central_papers_capability", "provide a capability or observation bundle, not both")
    if capability is None:
        if observation_bundle is not None:
            capability = FileObservationCapability(observation_bundle)
        else:
            if not confirm_public_discovery:
                _fail("public_discovery_not_confirmed", "live central-paper discovery requires explicit confirmation")
            capability = OpenAlexArxivCentralPapersCapability(root / "provider_cache")
    topic_contract = build_topic_contract(topic)
    campaign = build_campaign_contract(
        topic_contract,
        capability_fingerprint=capability.fingerprint,
        budget=budget,
    )
    capability_row = capability_manifest(capability)

    if resume:
        _regular(root / "campaign_contract.json", "campaign contract")
        _regular(root / "capability_manifest.json", "capability manifest")
        stored_campaign = validate_campaign_contract(_load(root / "campaign_contract.json", "campaign contract"))
        stored_capability = validate_capability_manifest(
            _load(root / "capability_manifest.json", "capability manifest"),
            expected_fingerprint=stored_campaign["capability_fingerprint"],
        )
        if stored_campaign != campaign or stored_capability != capability_row:
            _fail("central_papers_resume_mismatch", "resume topic, budget, or capability differs")
        if (root / "campaign_manifest.json").exists():
            return validate_central_papers_campaign(root, expected_topic=topic)["report"]
        residue = [name for name in TERMINAL_FILES if (root / name).exists() or (root / name).is_symlink()]
        residue.extend(
            f"ledgers/{name}.json" for name in LEDGER_NAMES
            if (root / "ledgers" / f"{name}.json").exists()
            or (root / "ledgers" / f"{name}.json").is_symlink()
        )
        if residue:
            _fail("central_papers_partial_terminal_residue", f"partial terminal artifacts exist: {residue}")
        observations = _load_checkpoint(root, campaign, capability_row)
    else:
        if root.exists():
            if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
                _fail("central_papers_output_exists", "fresh campaign output must be absent or empty")
        root.mkdir(parents=True, exist_ok=True)
        _write_new(root / "topic_contract.json", topic_contract)
        _write_new(root / "campaign_contract.json", campaign)
        _write_new(root / "capability_manifest.json", capability_row)
        observations = validate_observations(
            capability.collect(topic_contract, campaign["budget"]),
            expected_topic_contract_sha256=campaign["topic_contract_sha256"],
            expected_capability_fingerprint=campaign["capability_fingerprint"],
        )
        _validate_budget(observations, campaign["budget"])
        max_round = max((candidate["discovery_round"] for candidate in observations["candidates"]), default=0)
        prior_digest = None
        for round_index in range(max_round + 1):
            checkpoint_path = root / "rounds" / f"round-{round_index:03d}.json"
            _write_new(checkpoint_path, _checkpoint(
                campaign,
                capability_row,
                observations,
                round_index=round_index,
                prior_checkpoint_sha256=prior_digest,
            ))
            prior_digest = sha256_bytes(checkpoint_path.read_bytes())

    ledgers, evidence, derived = derive_campaign_evidence(campaign, observations)
    assessment = derived["assessment"]
    snowball = _snowball_decision(campaign, observations, derived)
    for name in LEDGER_NAMES:
        _write_new(root / "ledgers" / f"{name}.json", ledgers[name])
    _write_new(root / "centrality_evidence.json", evidence)
    _write_new(root / "centrality_assessment.json", assessment)
    _write_new(root / "snowball_decision.json", snowball)
    evidence_manifest = _evidence_manifest(root, campaign, ledgers, evidence)
    _write_new(root / "evidence_construction_manifest.json", evidence_manifest)
    report = _report(campaign, observations, derived, snowball)
    _write_new(root / "campaign_report.json", report)
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "campaign_contract_sha256": campaign_contract_sha256(campaign),
        "capability_manifest_sha256": sha256_bytes(canonical_json_bytes(capability_row)),
        "artifact_sha256": {
            name: sha256_bytes((root / name).read_bytes()) for name in TERMINAL_FILES
        },
        "ledger_sha256": {
            name: sha256_bytes((root / "ledgers" / f"{name}.json").read_bytes())
            for name in LEDGER_NAMES
        },
        "benchmark_labels_consumed": False,
    }
    _write_new(root / "campaign_manifest.json", manifest)
    return report


def validate_central_papers_campaign(
    output_dir: Path, *, expected_topic: str | None = None
) -> dict[str, Any]:
    root = output_dir.absolute()
    for name in (
        "topic_contract.json", "campaign_contract.json", "capability_manifest.json", "campaign_manifest.json",
        *TERMINAL_FILES,
    ):
        _regular(root / name, name)
    for name in LEDGER_NAMES:
        _regular(root / "ledgers" / f"{name}.json", f"{name} ledger")
    campaign = validate_campaign_contract(_load(root / "campaign_contract.json", "campaign contract"))
    topic_contract = validate_topic_contract(_load(root / "topic_contract.json", "topic contract"))
    if topic_contract != campaign["topic_contract"]:
        _fail("invalid_central_papers_campaign", "standalone topic contract differs from campaign")
    if expected_topic is not None and campaign["topic_contract"]["topic"] != expected_topic:
        _fail("invalid_central_papers_campaign", "campaign belongs to a different topic")
    capability = validate_capability_manifest(
        _load(root / "capability_manifest.json", "capability manifest"),
        expected_fingerprint=campaign["capability_fingerprint"],
    )
    observations = _load_checkpoint(root, campaign, capability)
    manifest = _load(root / "campaign_manifest.json", "campaign manifest")
    expected_fields = {
        "schema_version", "campaign_contract_sha256", "capability_manifest_sha256",
        "artifact_sha256", "ledger_sha256", "benchmark_labels_consumed",
    }
    if set(manifest) != expected_fields or manifest["schema_version"] != MANIFEST_SCHEMA:
        _fail("invalid_central_papers_campaign", "terminal manifest fields or schema are invalid")
    if manifest["benchmark_labels_consumed"] is not False:
        _fail("invalid_central_papers_campaign", "terminal manifest reports benchmark-label consumption")
    if manifest["campaign_contract_sha256"] != campaign_contract_sha256(campaign):
        _fail("invalid_central_papers_campaign", "terminal campaign binding differs")
    if manifest["capability_manifest_sha256"] != sha256_bytes(canonical_json_bytes(capability)):
        _fail("invalid_central_papers_campaign", "terminal capability binding differs")
    expected_artifacts = {name: sha256_bytes((root / name).read_bytes()) for name in TERMINAL_FILES}
    expected_ledgers = {
        name: sha256_bytes((root / "ledgers" / f"{name}.json").read_bytes()) for name in LEDGER_NAMES
    }
    if manifest["artifact_sha256"] != expected_artifacts or manifest["ledger_sha256"] != expected_ledgers:
        _fail("invalid_central_papers_campaign", "terminal artifact binding differs")
    ledgers, evidence, derived = derive_campaign_evidence(campaign, observations)
    snowball = _snowball_decision(campaign, observations, derived)
    if _load(root / "evidence_construction_manifest.json", "evidence construction manifest") != _evidence_manifest(root, campaign, ledgers, evidence):
        _fail("invalid_central_papers_campaign", "evidence construction manifest differs from replay")
    if _load(root / "centrality_evidence.json", "centrality evidence") != evidence:
        _fail("invalid_central_papers_campaign", "centrality evidence differs from replay")
    if _load(root / "centrality_assessment.json", "centrality assessment") != derived["assessment"]:
        _fail("invalid_central_papers_campaign", "centrality assessment differs from replay")
    for name in LEDGER_NAMES:
        if _load(root / "ledgers" / f"{name}.json", f"{name} ledger") != ledgers[name]:
            _fail("invalid_central_papers_campaign", f"{name} ledger differs from replay")
    if _load(root / "snowball_decision.json", "snowball decision") != snowball:
        _fail("invalid_central_papers_campaign", "snowball decision differs from replay")
    report = _load(root / "campaign_report.json", "campaign report")
    if report != _report(campaign, observations, derived, snowball):
        _fail("invalid_central_papers_campaign", "campaign report differs from replay")
    return {"campaign": campaign, "report": report, "manifest": manifest}


__all__ = [
    "CAMPAIGN_CONTRACT_SCHEMA", "CHECKPOINT_SCHEMA", "DEFAULT_BUDGET",
    "MANIFEST_SCHEMA", "REPORT_SCHEMA", "build_campaign_contract",
    "campaign_contract_sha256", "run_central_papers_campaign",
    "validate_campaign_contract", "validate_central_papers_campaign",
]
