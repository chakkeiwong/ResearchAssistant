from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

from research_assistant.survey import m20_campaign_runner as runner
from research_assistant.survey.m20_live_worker import (
    ARXIV_SEED,
    OPENALEX_ID,
    TOPIC,
    M20WorkerError,
    run_matrix,
    validate_published_run,
)
from research_assistant.survey.mission_state import canonical_json_bytes


PLAN = "docs/plans/literature_survey_north_star_m20_active_campaign_plan_2026-07-17.md"


def _initialize(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    plan = repository / PLAN
    plan.parent.mkdir(parents=True)
    plan.write_text("test plan\n", encoding="utf-8")
    campaign = tmp_path / "campaign"
    runner.initialize_campaign(
        campaign_root=campaign,
        repository_root=repository,
        plan_path=plan,
        now=lambda: "2026-07-17T00:00:00+00:00",
    )
    return campaign


def _provenance(_root: Path) -> dict[str, Any]:
    return {"commit": "a" * 40, "tree": "b" * 40, "worktree_dirty": False}


def _matrix(
    *,
    cost_state: str = "open",
    reserved: str = "0.0011",
    reconciled: str = "0.0011",
    privacy_blocked: bool = False,
    credential_canary: str | None = None,
    lookup_credential: bool = False,
):
    def execute(**kwargs: Any) -> dict[str, Any]:
        root = kwargs["output_root"]
        root.mkdir()
        if credential_canary is not None or lookup_credential:
            credential = kwargs["credential_getter"]("OPENALEX_API_KEY")
            if credential_canary is not None:
                assert credential == credential_canary
        cost = {
            "cost_state": cost_state,
            "cost_block_code": "dispatch_cost_unreconciled" if cost_state == "blocked" else None,
            "reserved_cost_usd": reserved,
            "reconciled_cost_usd": reconciled,
        }
        (root / "request_ledger.json").write_text(json.dumps({
            "rows": [{
                "provider": "openalex",
                "status": "available",
                "cost_evidence": {
                    "credential_persisted": privacy_blocked,
                    "authenticated_url_persisted": False,
                    "error_code": None,
                    "cost_block_code": cost["cost_block_code"],
                },
            }],
        }), encoding="utf-8")
        return {"cost_evidence": cost}

    return execute


def _replay(*, validity: str = "closed", selected: bool = True):
    def validate(_root: Path, *, execution_mode: str) -> dict[str, Any]:
        assert execution_mode == "live"
        return {
            "status": "passed",
            "campaign_validity": validity,
            "selected_candidate_authority": selected,
        }

    return validate


def _run(
    campaign: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    matrix_runner: Any = None,
    replay_validator: Any = None,
    credential_getter: Any = None,
) -> dict[str, Any]:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    return runner.run_campaign_attempt(
        campaign_root=campaign,
        matrix_runner=matrix_runner or _matrix(),
        replay_validator=replay_validator or _replay(),
        credential_getter=credential_getter or (lambda _name: "synthetic-key"),
        arxiv_dispatch=lambda _descriptor: b"",
        openalex_dispatch=lambda _request: b"",
        git_provenance=_provenance,
        now=lambda: "2026-07-17T00:01:00+00:00",
    )


def _state(campaign: Path) -> dict[str, Any]:
    return json.loads((campaign / runner.STATE_NAME).read_text(encoding="utf-8"))


def test_selected_candidate_promotes_with_replay_cost_and_privacy_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    result = _run(campaign, monkeypatch)

    assert result["classification"] == "M20_PROMOTED"
    assert result["m20_primary_criterion_passed"] is True
    assert _state(campaign)["status"] == "promoted"
    assert _state(campaign)["selected_attempt"] == "attempt-01"


def test_valid_no_selection_result_is_terminal_and_non_promoting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    result = _run(campaign, monkeypatch, replay_validator=_replay(selected=False))

    assert result["classification"] == "VALID_NEGATIVE_NO_SELECTED_CANDIDATE"
    assert result["m20_primary_criterion_passed"] is False
    assert result["retry_allowed_under_unchanged_campaign"] is False
    assert _state(campaign)["status"] == "stopped_no_selected_candidate"


def test_blocked_cost_is_veto_even_when_numeric_amounts_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    result = _run(
        campaign,
        monkeypatch,
        matrix_runner=_matrix(cost_state="blocked", reserved="0", reconciled="0"),
    )

    assert result["classification"] == "CONTINUATION_VETO"
    assert result["continuation_veto_reason"] == "cost_state_blocked"
    assert result["cost_accounting_status"] == "unknown_or_unreconciled"
    assert result["remaining_cost_usd"] is None
    assert _state(campaign)["continuation_veto"] is True
    assert _state(campaign)["remaining_cost_usd"] is None


def test_missing_credential_is_retryable_only_while_cost_state_is_known(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    result = _run(
        campaign,
        monkeypatch,
        matrix_runner=_matrix(reserved="0", reconciled="0", lookup_credential=True),
        replay_validator=_replay(validity="boundary_invalid", selected=False),
        credential_getter=lambda _name: None,
    )

    assert result["classification"] == "RETRYABLE_BOUNDARY_FAILURE"
    assert result["retry_allowed_under_unchanged_campaign"] is True
    assert _state(campaign)["status"] == "ready_for_retry"


def test_planning_assumption_invalidation_disables_remaining_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    _run(
        campaign,
        monkeypatch,
        matrix_runner=_matrix(reserved="0", reconciled="0", lookup_credential=True),
        replay_validator=_replay(validity="boundary_invalid", selected=False),
        credential_getter=lambda _name: None,
    )

    record = runner.invalidate_campaign(
        campaign_root=campaign,
        reason="unmet_credential_prerequisite",
        now=lambda: "2026-07-18T00:00:00+00:00",
    )

    assert record["remaining_attempts_disabled"] == 1
    assert record["reconciled_cost_usd"] == "0"
    assert _state(campaign)["status"] == "invalidated_planning_assumption"
    assert _state(campaign)["continuation_veto"] is True
    with pytest.raises(runner.M20CampaignError, match="campaign_not_runnable"):
        _run(campaign, monkeypatch)


@pytest.mark.parametrize("bad_value", [None, [], "not-a-summary"])
def test_malformed_worker_result_still_writes_a_terminal_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_value: Any
) -> None:
    campaign = _initialize(tmp_path)

    result = _run(campaign, monkeypatch, matrix_runner=lambda **_kwargs: bad_value)

    assert result["classification"] == "CONTINUATION_VETO"
    assert result["continuation_veto_reason"] == "execution_failed_before_replay"
    assert (campaign / "attempt-01" / runner.ATTEMPT_RESULT_NAME).is_file()


def test_provider_failure_with_unreconciled_cost_prevents_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    result = _run(
        campaign,
        monkeypatch,
        matrix_runner=_matrix(cost_state="blocked", reserved="0.001", reconciled="0"),
        replay_validator=_replay(validity="boundary_invalid", selected=False),
    )

    assert result["classification"] == "CONTINUATION_VETO"
    assert result["cost_accounting_status"] == "unknown_or_unreconciled"
    with pytest.raises(runner.M20CampaignError, match="campaign_not_runnable"):
        _run(campaign, monkeypatch)


def test_cumulative_cost_preflight_blocks_attempt_two_before_credential_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    state = _state(campaign)
    state.update({
        "status": "ready_for_retry",
        "attempts_used": 1,
        "reconciled_cost_usd": "0.009",
        "remaining_cost_usd": "0.001",
        "attempts": [{
            "attempt_id": "attempt-01",
            "status": "RETRYABLE_BOUNDARY_FAILURE",
            "manifest_path": "historical",
            "result_path": "historical",
            "reconciled_cost_usd": "0.009",
        }],
    })
    (campaign / runner.STATE_NAME).write_text(json.dumps(state), encoding="utf-8")
    looked_up = []

    with pytest.raises(runner.M20CampaignError, match="insufficient_remaining_campaign_cost"):
        _run(campaign, monkeypatch, credential_getter=lambda name: looked_up.append(name))
    assert looked_up == []


def test_existing_attempt_root_is_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    (campaign / "attempt-01").mkdir()

    with pytest.raises(runner.M20CampaignError, match="attempt_output_not_fresh"):
        _run(campaign, monkeypatch)


def test_inconsistent_selected_attempt_state_is_rejected_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    state = _state(campaign)
    state.update({
        "status": "promoted",
        "attempts_used": 1,
        "selected_attempt": "attempt-02",
        "attempts": [{
            "attempt_id": "attempt-01",
            "status": "M20_PROMOTED",
            "manifest_path": "historical",
            "result_path": "historical",
            "reconciled_cost_usd": "0.0011",
        }],
    })
    (campaign / runner.STATE_NAME).write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(runner.M20CampaignError, match="campaign_state_invalid"):
        _run(campaign, monkeypatch)


def test_offline_replay_failure_is_a_continuation_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)

    def failed_replay(_root: Path, *, execution_mode: str) -> dict[str, Any]:
        raise M20WorkerError("published_run_replay_invalid")

    result = _run(campaign, monkeypatch, replay_validator=failed_replay)
    assert result["classification"] == "CONTINUATION_VETO"
    assert result["offline_replay_status"] == "failed"


@pytest.mark.parametrize(
    "bad_replay",
    [
        {},
        {"status": "failed", "campaign_validity": "closed", "selected_candidate_authority": True},
        {"status": "passed", "campaign_validity": "unknown", "selected_candidate_authority": True},
        {"status": "passed", "campaign_validity": "closed", "selected_candidate_authority": "yes"},
    ],
)
def test_malformed_replay_result_is_a_continuation_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_replay: dict[str, Any]
) -> None:
    campaign = _initialize(tmp_path)
    result = _run(
        campaign,
        monkeypatch,
        replay_validator=lambda _root, execution_mode: bad_replay,
    )

    assert result["classification"] == "CONTINUATION_VETO"
    assert result["continuation_veto_reason"] == "offline_replay_failed"


def test_privacy_block_is_a_continuation_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    result = _run(campaign, monkeypatch, matrix_runner=_matrix(privacy_blocked=True))

    assert result["classification"] == "CONTINUATION_VETO"
    assert result["privacy_state"] == "blocked"


def test_credential_canary_is_not_persisted_in_campaign_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    canary = "M20-SYNTHETIC-CREDENTIAL-CANARY"
    _run(
        campaign,
        monkeypatch,
        matrix_runner=_matrix(credential_canary=canary),
        credential_getter=lambda name: canary if name == "OPENALEX_API_KEY" else None,
    )

    assert canary.encode() not in b"".join(
        path.read_bytes() for path in campaign.rglob("*") if path.is_file()
    )


def test_cpu_only_environment_is_required_before_attempt_consumption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)

    with pytest.raises(runner.M20CampaignError, match="cpu_only_environment_required"):
        runner.run_campaign_attempt(campaign_root=campaign, git_provenance=_provenance)
    assert _state(campaign)["attempts_used"] == 0


def test_real_worker_synthetic_dispatches_close_runner_evidence_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _initialize(tmp_path)
    canary = "M20-RUNNER-END-TO-END-CANARY"

    def atom(arxiv_id: str, title: str) -> bytes:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry><id>https://arxiv.org/abs/{arxiv_id}</id><title>{title}</title>
  <published>2022-01-01T00:00:00Z</published><author><name>Alice Example</name></author>
  <arxiv:primary_category term="cs.LG" /></entry>
</feed>'''.encode()

    def work(work_id: str, *, lineage: list[str] | None = None) -> dict[str, Any]:
        return {
            "id": f"https://openalex.org/{work_id}",
            "display_name": TOPIC,
            "authorships": [{"author": {"display_name": "Alice Example"}}],
            "publication_year": 2022,
            "doi": "https://doi.org/10.1000/neural-ot",
            "cited_by_count": 7,
            "referenced_works": lineage or [],
            "ids": {
                "openalex": f"https://openalex.org/{work_id}",
                "doi": "https://doi.org/10.1000/neural-ot",
            },
            "type": "article",
            "publication_date": "2022-01-01",
        }

    def work_list(work_id: str, cost: float) -> bytes:
        return canonical_json_bytes({
            "meta": {
                "count": 1,
                "db_response_time_ms": 1,
                "page": 1,
                "per_page": 10,
                "next_cursor": None,
                "groups_count": 0,
                "cost_usd": cost,
            },
            "results": [work(work_id)],
            "group_by": [],
        })

    def arxiv_dispatch(descriptor: dict[str, Any]) -> bytes:
        return (
            atom("9999.00001v1", TOPIC)
            if descriptor["route_kind"] == "arxiv_topic"
            else atom(ARXIV_SEED, "Neural Optimal Transport")
        )

    def openalex_dispatch(request: Any) -> bytes:
        split = urllib.parse.urlsplit(request.full_url)
        query = urllib.parse.parse_qs(split.query)
        assert query.pop("api_key") == [canary]
        if "search" in query:
            return work_list(OPENALEX_ID, 0.001)
        if split.path.endswith(OPENALEX_ID):
            return canonical_json_bytes(work(OPENALEX_ID, lineage=["https://openalex.org/W1"]))
        return work_list("W2", 0.0001)

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    result = runner.run_campaign_attempt(
        campaign_root=campaign,
        credential_getter=lambda name: canary if name == "OPENALEX_API_KEY" else None,
        arxiv_dispatch=arxiv_dispatch,
        openalex_dispatch=openalex_dispatch,
        matrix_runner=run_matrix,
        replay_validator=validate_published_run,
        git_provenance=_provenance,
        now=lambda: "2026-07-17T00:01:00+00:00",
    )

    worker = campaign / "attempt-01" / "worker"
    assert result["classification"] == "M20_PROMOTED"
    assert result["offline_replay_status"] == "passed"
    assert result["attempt_reconciled_cost_usd"] == "0.0011"
    assert len(json.loads((worker / "request_ledger.json").read_text())["rows"]) == 5
    assert canary.encode() not in b"".join(
        path.read_bytes() for path in campaign.rglob("*") if path.is_file()
    )
