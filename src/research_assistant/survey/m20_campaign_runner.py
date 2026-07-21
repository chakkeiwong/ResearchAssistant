from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from research_assistant.survey.m20_live_worker import (
    M20WorkerError,
    _environment_getter,
    _real_arxiv_dispatch,
    _real_openalex_dispatch,
    route_manifest_sha256,
    run_matrix,
    validate_published_run,
)
from research_assistant.survey.mission_state import pretty_json_bytes, sha256_file
from research_assistant.survey.openalex_credential_cost import (
    CAMPAIGN_COST_CAP_USD,
    ROUTE_COST_USD,
)


CAMPAIGN_SCHEMA = "ra-literature-survey-m20-academic-campaign-v1"
ATTEMPT_MANIFEST_SCHEMA = "ra-literature-survey-m20-academic-attempt-manifest-v1"
ATTEMPT_RESULT_SCHEMA = "ra-literature-survey-m20-academic-attempt-result-v1"
MAX_ATTEMPTS = 2
MAX_ATTEMPT_COST_USD = sum(ROUTE_COST_USD.values(), Decimal("0"))
STATE_NAME = "campaign_state.json"
ATTEMPT_MANIFEST_NAME = "attempt_manifest.json"
ATTEMPT_RESULT_NAME = "attempt_result.json"
INVALIDATION_NAME = "campaign_invalidation.json"


class M20CampaignError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usd(value: Decimal) -> str:
    return format(value, "f")


def _atomic_json(path: Path, value: Any) -> None:
    if not path.parent.is_dir():
        raise M20CampaignError("artifact_parent_missing")
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(pretty_json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_json(path: Path, error_code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M20CampaignError(error_code) from exc
    if not isinstance(value, dict):
        raise M20CampaignError(error_code)
    return value


def _git_provenance(repository_root: Path) -> dict[str, Any]:
    if not repository_root.is_dir():
        raise M20CampaignError("repository_root_invalid")

    def git(*args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=repository_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise M20CampaignError("git_provenance_unavailable") from exc
        return completed.stdout.strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "worktree_dirty": bool(git("status", "--porcelain")),
    }


def _validate_state(state: dict[str, Any]) -> tuple[Decimal, Decimal | None]:
    required = {
        "schema_version",
        "campaign_id",
        "status",
        "repository_root",
        "plan_path",
        "route_manifest_sha256",
        "attempt_limit",
        "attempts_used",
        "cost_cap_usd",
        "reconciled_cost_usd",
        "remaining_cost_usd",
        "cost_accounting_status",
        "continuation_veto",
        "continuation_veto_reason",
        "selected_attempt",
        "attempts",
        "created_at_utc",
        "updated_at_utc",
    }
    try:
        reconciled = Decimal(state["reconciled_cost_usd"])
        remaining = (
            Decimal(state["remaining_cost_usd"])
            if state["remaining_cost_usd"] is not None
            else None
        )
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise M20CampaignError("campaign_state_invalid") from exc
    attempts = state.get("attempts")
    attempts_valid = isinstance(attempts, list)
    allowed_attempt_statuses = {
        "running",
        "M20_PROMOTED",
        "VALID_NEGATIVE_NO_SELECTED_CANDIDATE",
        "RETRYABLE_BOUNDARY_FAILURE",
        "ATTEMPT_BUDGET_EXHAUSTED",
        "CONTINUATION_VETO",
    }
    if attempts_valid:
        for index, row in enumerate(attempts, start=1):
            if not isinstance(row, dict) or set(row) != {
                "attempt_id", "status", "manifest_path", "result_path", "reconciled_cost_usd",
            }:
                attempts_valid = False
                break
            cost = row["reconciled_cost_usd"]
            try:
                parsed_cost = Decimal(cost) if cost is not None else None
            except (InvalidOperation, TypeError):
                attempts_valid = False
                break
            if (
                row["attempt_id"] != f"attempt-{index:02d}"
                or row["status"] not in allowed_attempt_statuses
                or not isinstance(row["manifest_path"], str)
                or not row["manifest_path"]
                or not isinstance(row["result_path"], str)
                or not row["result_path"]
                or (
                    parsed_cost is not None
                    and (not parsed_cost.is_finite() or parsed_cost < 0 or parsed_cost > CAMPAIGN_COST_CAP_USD)
                )
            ):
                attempts_valid = False
                break
    expected_last_status = {
        "running": "running",
        "ready_for_retry": "RETRYABLE_BOUNDARY_FAILURE",
        "promoted": "M20_PROMOTED",
        "stopped_no_selected_candidate": "VALID_NEGATIVE_NO_SELECTED_CANDIDATE",
        "stopped_attempt_budget_exhausted": "ATTEMPT_BUDGET_EXHAUSTED",
        "continuation_veto": "CONTINUATION_VETO",
        "invalidated_planning_assumption": "RETRYABLE_BOUNDARY_FAILURE",
    }.get(state.get("status"))
    selected_attempt_valid = (
        state.get("selected_attempt") == attempts[-1]["attempt_id"]
        if state.get("status") == "promoted" and attempts_valid and attempts
        else state.get("selected_attempt") is None
    )
    if (
        set(state) != required
        or state["schema_version"] != CAMPAIGN_SCHEMA
        or not isinstance(state["campaign_id"], str)
        or state["status"] not in {
            "ready",
            "running",
            "ready_for_retry",
            "promoted",
            "stopped_no_selected_candidate",
            "stopped_attempt_budget_exhausted",
            "continuation_veto",
            "invalidated_planning_assumption",
        }
        or type(state["attempt_limit"]) is not int
        or state["attempt_limit"] != MAX_ATTEMPTS
        or type(state["attempts_used"]) is not int
        or not 0 <= state["attempts_used"] <= MAX_ATTEMPTS
        or not attempts_valid
        or len(attempts) != state["attempts_used"]
        or (state["status"] == "ready" and attempts != [])
        or (
            expected_last_status is not None
            and (not attempts or attempts[-1]["status"] != expected_last_status)
        )
        or not selected_attempt_valid
        or state["cost_cap_usd"] != _usd(CAMPAIGN_COST_CAP_USD)
        or not reconciled.is_finite()
        or state["cost_accounting_status"] not in {"known", "unknown_or_unreconciled"}
        or (
            state["cost_accounting_status"] == "known"
            and (
                not isinstance(remaining, Decimal)
                or not remaining.is_finite()
                or min(reconciled, remaining) < 0
                or reconciled + remaining != CAMPAIGN_COST_CAP_USD
            )
        )
        or (
            state["cost_accounting_status"] == "unknown_or_unreconciled"
            and (remaining is not None or state["status"] != "continuation_veto")
        )
        or type(state["continuation_veto"]) is not bool
        or state["continuation_veto"] != (
            state["status"] in {"continuation_veto", "invalidated_planning_assumption"}
        )
        or (state["continuation_veto"] and not isinstance(state["continuation_veto_reason"], str))
        or (not state["continuation_veto"] and state["continuation_veto_reason"] is not None)
        or not isinstance(state["repository_root"], str)
        or not Path(state["repository_root"]).is_absolute()
        or not isinstance(state["plan_path"], str)
        or not Path(state["plan_path"]).is_absolute()
        or not isinstance(state["created_at_utc"], str)
        or not state["created_at_utc"]
        or not isinstance(state["updated_at_utc"], str)
        or not state["updated_at_utc"]
        or state["route_manifest_sha256"] != route_manifest_sha256()
    ):
        raise M20CampaignError("campaign_state_invalid")
    return reconciled, remaining


def invalidate_campaign(
    *,
    campaign_root: Path,
    reason: str,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    campaign_root = campaign_root.resolve(strict=True)
    state_path = campaign_root / STATE_NAME
    state = _read_json(state_path, "campaign_state_missing")
    _validate_state(state)
    if state["status"] != "ready_for_retry":
        raise M20CampaignError("campaign_not_invalidatable")
    if reason != "unmet_credential_prerequisite":
        raise M20CampaignError("invalidation_reason_invalid")
    record = {
        "schema_version": "ra-literature-survey-m20-campaign-invalidation-v1",
        "campaign_id": state["campaign_id"],
        "status": "invalidated_planning_assumption",
        "reason": reason,
        "attempts_used": state["attempts_used"],
        "reconciled_cost_usd": state["reconciled_cost_usd"],
        "remaining_attempts_disabled": MAX_ATTEMPTS - state["attempts_used"],
        "invalidated_at_utc": now(),
        "nonclaims": [
            "provider_failure",
            "credential_invalidity",
            "m20_scientific_failure",
            "north_star_mission_completion",
        ],
    }
    invalidation_path = campaign_root / INVALIDATION_NAME
    if invalidation_path.exists():
        raise M20CampaignError("campaign_invalidation_exists")
    _atomic_json(invalidation_path, record)
    state["status"] = "invalidated_planning_assumption"
    state["continuation_veto"] = True
    state["continuation_veto_reason"] = reason
    state["updated_at_utc"] = record["invalidated_at_utc"]
    _validate_state(state)
    _atomic_json(state_path, state)
    return record


def initialize_campaign(
    *,
    campaign_root: Path,
    repository_root: Path,
    plan_path: Path,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    campaign_root = campaign_root.resolve(strict=False)
    repository_root = repository_root.resolve(strict=True)
    plan_path = plan_path.resolve(strict=True)
    if campaign_root.exists() or not campaign_root.parent.is_dir():
        raise M20CampaignError("campaign_root_not_fresh")
    if not plan_path.is_file():
        raise M20CampaignError("plan_path_invalid")
    campaign_root.mkdir(mode=0o700)
    created = now()
    state = {
        "schema_version": CAMPAIGN_SCHEMA,
        "campaign_id": campaign_root.name,
        "status": "ready",
        "repository_root": str(repository_root),
        "plan_path": str(plan_path),
        "route_manifest_sha256": route_manifest_sha256(),
        "attempt_limit": MAX_ATTEMPTS,
        "attempts_used": 0,
        "cost_cap_usd": _usd(CAMPAIGN_COST_CAP_USD),
        "reconciled_cost_usd": "0",
        "remaining_cost_usd": _usd(CAMPAIGN_COST_CAP_USD),
        "cost_accounting_status": "known",
        "continuation_veto": False,
        "continuation_veto_reason": None,
        "selected_attempt": None,
        "attempts": [],
        "created_at_utc": created,
        "updated_at_utc": created,
    }
    _validate_state(state)
    _atomic_json(campaign_root / STATE_NAME, state)
    return state


def _cost_assessment(summary: Any) -> tuple[Decimal | None, bool, str | None]:
    if not isinstance(summary, dict):
        return None, False, "cost_evidence_missing"
    evidence = summary.get("cost_evidence")
    if not isinstance(evidence, dict):
        return None, False, "cost_evidence_missing"
    try:
        reserved = Decimal(evidence["reserved_cost_usd"])
        reconciled = Decimal(evidence["reconciled_cost_usd"])
    except (KeyError, InvalidOperation, TypeError):
        return None, False, "cost_evidence_invalid"
    if not reserved.is_finite() or not reconciled.is_finite() or min(reserved, reconciled) < 0:
        return None, False, "cost_evidence_invalid"
    if evidence.get("cost_state") != "open" or evidence.get("cost_block_code") is not None:
        return reconciled, False, "cost_state_blocked"
    if reserved != reconciled:
        return reconciled, False, "cost_unreconciled"
    return reconciled, True, None


def _privacy_assessment(worker_root: Path) -> tuple[str, str | None]:
    ledger = _read_json(worker_root / "request_ledger.json", "privacy_evidence_missing")
    rows = ledger.get("rows")
    if not isinstance(rows, list):
        return "not_established", "privacy_evidence_invalid"
    for row in rows:
        if not isinstance(row, dict) or row.get("provider") != "openalex":
            continue
        evidence = row.get("cost_evidence")
        if evidence is None and row.get("status") == "not_dispatched_due_to_veto":
            continue
        if not isinstance(evidence, dict):
            return "not_established", "privacy_evidence_invalid"
        if (
            evidence.get("credential_persisted") is not False
            or evidence.get("authenticated_url_persisted") is not False
            or evidence.get("error_code") == "credential_echoed_in_response"
            or evidence.get("cost_block_code") == "credential_echoed_in_response"
        ):
            return "blocked", "credential_persistence_or_echo"
    return "passed", None


def _validated_replay(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("status") != "passed"
        or value.get("campaign_validity") not in {"closed", "boundary_invalid"}
        or type(value.get("selected_candidate_authority")) is not bool
    ):
        raise M20CampaignError("offline_replay_invalid")
    return value


def _result_classification(
    *,
    replay: dict[str, Any] | None,
    replay_error: str | None,
    cost_ok: bool,
    cost_error: str | None,
    privacy_state: str,
    privacy_error: str | None,
    attempts_used: int,
) -> tuple[str, bool, bool, str | None]:
    if replay_error is not None:
        return "CONTINUATION_VETO", False, True, replay_error
    if not cost_ok:
        return "CONTINUATION_VETO", False, True, cost_error or "cost_not_reconciled"
    if privacy_state != "passed":
        return "CONTINUATION_VETO", False, True, privacy_error or "privacy_not_established"
    if not isinstance(replay, dict):
        return "CONTINUATION_VETO", False, True, "offline_replay_missing"
    if replay.get("campaign_validity") == "closed":
        if replay.get("selected_candidate_authority") is True:
            return "M20_PROMOTED", False, False, None
        return "VALID_NEGATIVE_NO_SELECTED_CANDIDATE", False, False, None
    if attempts_used < MAX_ATTEMPTS:
        return "RETRYABLE_BOUNDARY_FAILURE", True, False, None
    return "ATTEMPT_BUDGET_EXHAUSTED", False, False, None


def run_campaign_attempt(
    *,
    campaign_root: Path,
    command: list[str] | None = None,
    credential_getter: Callable[[str], Any] | None = None,
    arxiv_dispatch: Callable[[dict[str, Any]], bytes] | None = None,
    openalex_dispatch: Callable[[Any], bytes] | None = None,
    matrix_runner: Callable[..., dict[str, Any]] = run_matrix,
    replay_validator: Callable[..., dict[str, Any]] = validate_published_run,
    git_provenance: Callable[[Path], dict[str, Any]] = _git_provenance,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    campaign_root = campaign_root.resolve(strict=True)
    state_path = campaign_root / STATE_NAME
    state = _read_json(state_path, "campaign_state_missing")
    reconciled_before, remaining_before = _validate_state(state)
    if state["status"] not in {"ready", "ready_for_retry"}:
        raise M20CampaignError("campaign_not_runnable")
    if state["attempts_used"] >= MAX_ATTEMPTS:
        raise M20CampaignError("attempt_budget_exhausted")
    if remaining_before is None or remaining_before < MAX_ATTEMPT_COST_USD:
        raise M20CampaignError("insufficient_remaining_campaign_cost")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
        raise M20CampaignError("cpu_only_environment_required")

    repository_root = Path(state["repository_root"]).resolve(strict=True)
    plan_path = Path(state["plan_path"]).resolve(strict=True)
    if not plan_path.is_file():
        raise M20CampaignError("plan_path_invalid")
    provenance = git_provenance(repository_root)
    if (
        not isinstance(provenance, dict)
        or set(provenance) != {"commit", "tree", "worktree_dirty"}
        or not isinstance(provenance["commit"], str)
        or len(provenance["commit"]) != 40
        or not isinstance(provenance["tree"], str)
        or len(provenance["tree"]) != 40
        or type(provenance["worktree_dirty"]) is not bool
    ):
        raise M20CampaignError("git_provenance_invalid")
    attempt_number = state["attempts_used"] + 1
    attempt_id = f"attempt-{attempt_number:02d}"
    attempt_root = campaign_root / attempt_id
    if attempt_root.exists():
        raise M20CampaignError("attempt_output_not_fresh")
    attempt_root.mkdir(mode=0o700)
    worker_root = attempt_root / "worker"
    started = now()
    manifest = {
        "schema_version": ATTEMPT_MANIFEST_SCHEMA,
        "campaign_id": state["campaign_id"],
        "attempt_id": attempt_id,
        "status": "started",
        "question": "Can the frozen five-route metadata matrix produce replay-valid selected-candidate authority?",
        "plan_path": str(plan_path),
        "plan_sha256": sha256_file(plan_path),
        "route_manifest_sha256": state["route_manifest_sha256"],
        "git": provenance,
        "command": command or [sys.executable, "-m", "research_assistant.survey.m20_campaign_runner", "run"],
        "environment": {
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "gpu_used": False,
        },
        "attempt_limit": MAX_ATTEMPTS,
        "cost_cap_usd": _usd(CAMPAIGN_COST_CAP_USD),
        "cumulative_reconciled_cost_before_usd": _usd(reconciled_before),
        "remaining_cost_before_usd": _usd(remaining_before),
        "worker_output_root": str(worker_root),
        "started_at_utc": started,
    }
    _atomic_json(attempt_root / ATTEMPT_MANIFEST_NAME, manifest)

    running_row = {
        "attempt_id": attempt_id,
        "status": "running",
        "manifest_path": str(attempt_root / ATTEMPT_MANIFEST_NAME),
        "result_path": str(attempt_root / ATTEMPT_RESULT_NAME),
        "reconciled_cost_usd": None,
    }
    state["status"] = "running"
    state["attempts_used"] = attempt_number
    state["attempts"].append(running_row)
    state["updated_at_utc"] = started
    _validate_state(state)
    _atomic_json(state_path, state)

    summary: dict[str, Any] | None = None
    replay: dict[str, Any] | None = None
    replay_error: str | None = None
    privacy_state = "not_established"
    privacy_error: str | None = None
    execution_error: str | None = None
    try:
        candidate_summary = matrix_runner(
            output_root=worker_root,
            credential_getter=credential_getter or _environment_getter,
            arxiv_dispatch=arxiv_dispatch or _real_arxiv_dispatch,
            openalex_dispatch=openalex_dispatch or _real_openalex_dispatch,
            execution_mode="live",
        )
        if not isinstance(candidate_summary, dict):
            raise M20CampaignError("worker_summary_invalid")
        summary = candidate_summary
    except Exception as exc:  # The exception message may contain provider or credential data.
        execution_error = exc.code if isinstance(exc, (M20CampaignError, M20WorkerError)) else "execution_failed"
        replay_error = "execution_failed_before_replay"
    if summary is not None:
        try:
            replay = _validated_replay(replay_validator(worker_root, execution_mode="live"))
        except Exception:
            replay_error = "offline_replay_failed"
        try:
            privacy_state, privacy_error = _privacy_assessment(worker_root)
        except M20CampaignError:
            privacy_state, privacy_error = "not_established", "privacy_evidence_invalid"

    attempt_cost: Decimal | None = None
    cost_ok = False
    cost_error = "cost_not_established"
    if summary is not None:
        attempt_cost, cost_ok, cost_error = _cost_assessment(summary)
    classification, retry_allowed, continuation_veto, veto_reason = _result_classification(
        replay=replay,
        replay_error=replay_error,
        cost_ok=cost_ok,
        cost_error=cost_error,
        privacy_state=privacy_state,
        privacy_error=privacy_error,
        attempts_used=attempt_number,
    )
    reconciled_after = reconciled_before + (attempt_cost or Decimal("0"))
    if reconciled_after > CAMPAIGN_COST_CAP_USD:
        classification = "CONTINUATION_VETO"
        retry_allowed = False
        continuation_veto = True
        veto_reason = "campaign_cost_cap_exceeded"
    cost_accounting_status = "known" if cost_ok else "unknown_or_unreconciled"
    remaining_after = (
        CAMPAIGN_COST_CAP_USD - min(reconciled_after, CAMPAIGN_COST_CAP_USD)
        if cost_accounting_status == "known"
        else None
    )
    completed = now()
    result = {
        "schema_version": ATTEMPT_RESULT_SCHEMA,
        "campaign_id": state["campaign_id"],
        "attempt_id": attempt_id,
        "classification": classification,
        "m20_primary_criterion_passed": classification == "M20_PROMOTED",
        "campaign_validity": replay.get("campaign_validity") if replay else "not_established",
        "selected_candidate_authority": replay.get("selected_candidate_authority") if replay else False,
        "offline_replay_status": "passed" if replay is not None else "failed",
        "cost_state": (
            summary.get("cost_evidence", {}).get("cost_state", "not_established")
            if isinstance(summary.get("cost_evidence"), dict)
            else "not_established"
        ) if summary is not None else "not_established",
        "attempt_reconciled_cost_usd": _usd(attempt_cost) if attempt_cost is not None else None,
        "cumulative_reconciled_cost_usd": _usd(reconciled_after),
        "remaining_cost_usd": _usd(remaining_after) if remaining_after is not None else None,
        "cost_accounting_status": cost_accounting_status,
        "privacy_state": privacy_state,
        "retry_allowed_under_unchanged_campaign": retry_allowed,
        "continuation_veto": continuation_veto,
        "continuation_veto_reason": veto_reason,
        "execution_error": execution_error,
        "worker_output_root": str(worker_root),
        "completed_at_utc": completed,
        "nonclaims": [
            "literature_completeness",
            "scientific_superiority",
            "source_or_full_text_access",
            "north_star_mission_completion",
        ],
    }
    _atomic_json(attempt_root / ATTEMPT_RESULT_NAME, result)

    if classification == "M20_PROMOTED":
        state_status = "promoted"
        state["selected_attempt"] = attempt_id
    elif classification == "VALID_NEGATIVE_NO_SELECTED_CANDIDATE":
        state_status = "stopped_no_selected_candidate"
    elif classification == "RETRYABLE_BOUNDARY_FAILURE":
        state_status = "ready_for_retry"
    elif classification == "ATTEMPT_BUDGET_EXHAUSTED":
        state_status = "stopped_attempt_budget_exhausted"
    else:
        state_status = "continuation_veto"
    state["status"] = state_status
    state["reconciled_cost_usd"] = _usd(reconciled_after)
    state["remaining_cost_usd"] = _usd(remaining_after) if remaining_after is not None else None
    state["cost_accounting_status"] = cost_accounting_status
    state["continuation_veto"] = continuation_veto
    state["continuation_veto_reason"] = veto_reason if continuation_veto else None
    state["attempts"][-1] = {
        **running_row,
        "status": classification,
        "reconciled_cost_usd": _usd(attempt_cost) if attempt_cost is not None else None,
    }
    state["updated_at_utc"] = completed
    _validate_state(state)
    _atomic_json(state_path, state)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    initialize = subparsers.add_parser("init")
    initialize.add_argument("--campaign-root", type=Path, required=True)
    initialize.add_argument("--repository-root", type=Path, required=True)
    initialize.add_argument("--plan", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--campaign-root", type=Path, required=True)
    invalidate = subparsers.add_parser("invalidate")
    invalidate.add_argument("--campaign-root", type=Path, required=True)
    invalidate.add_argument(
        "--reason",
        choices=["unmet_credential_prerequisite"],
        required=True,
    )
    args = parser.parse_args(argv)
    if args.action == "init":
        initialize_campaign(
            campaign_root=args.campaign_root,
            repository_root=args.repository_root,
            plan_path=args.plan,
        )
        return 0
    if args.action == "invalidate":
        invalidate_campaign(campaign_root=args.campaign_root, reason=args.reason)
        return 0
    result = run_campaign_attempt(campaign_root=args.campaign_root, command=[sys.executable, *sys.argv])
    return 0 if result["classification"] in {"M20_PROMOTED", "VALID_NEGATIVE_NO_SELECTED_CANDIDATE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "M20CampaignError",
    "initialize_campaign",
    "invalidate_campaign",
    "run_campaign_attempt",
]
