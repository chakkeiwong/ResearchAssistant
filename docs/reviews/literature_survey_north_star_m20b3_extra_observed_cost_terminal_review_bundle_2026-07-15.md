# M20B3 Extra Observed-Cost Terminal Review Bundle

Date: `2026-07-15`
Scope: one human-authorized extra local replay-integrity review
Role: Claude or fresh Codex is read-only and advisory

## Objective And Boundary

Decide only whether the round-5 blocker is closed: offline replay must bind
blocked-after-dispatch `observed_cost_usd` to shapes reachable from
`execute_authenticated_openalex_request()`.

Do not edit files, run code, access a credential, call a provider, stage or
commit, authorize M20B4, or expand review beyond this observed-cost predicate.

## Frozen Bytes

| File | SHA-256 | Change status |
| --- | --- | --- |
| `src/research_assistant/survey/m20_live_worker.py` | `ef873948aa3c61dea87a82a0af9d85154f7e8a2762961c4274dc941da1129157` | repaired replay only |
| `tests/unit/test_literature_survey_m20_live_worker.py` | `10d3b2f018d24d84a99eb1b4a0c788b6a0e2a6a9c6a20d89484842291fe28040` | focused replay tests only |
| `src/research_assistant/survey/m20_live_supervisor.py` | `96890d38f984bb579fdcc79eff1487dd39925a198d5d955980099a6ba7a30fb6` | unchanged |
| `tests/unit/test_literature_survey_m20_live_supervisor.py` | `f7013e5229aa29b9288aabc5789ce0cd0eadb87f2afd83668fc35cf815ea8c7e` | unchanged |

## Producer Derivation

Producer anchors are
`src/research_assistant/survey/openalex_credential_cost.py:43`,
`src/research_assistant/survey/openalex_credential_cost.py:231`, and
`src/research_assistant/survey/openalex_credential_cost.py:505`.

The producer canonicalizes a non-null observed `Decimal` with
`format(value, "f")`.

| Producer error | Reachable observed value |
| --- | --- |
| `dispatch_failed_closed` | `null`; dispatch threw before a body existed |
| `response_type_invalid` | `null`; response type rejected before parsing |
| `credential_echoed_in_response` | `null`; body rejected before parsing |
| `response_cost_unreconciled` | `null`; parser/cost extraction failed before assigning `observed` |
| `cost_contradiction` | canonical finite nonnegative decimal unequal to route prediction |
| `cost_state_changed_during_dispatch` | canonical finite nonnegative parsed decimal; relation to prediction is not reached |
| `invalid_cost_state` | canonical finite nonnegative parsed decimal; relation to prediction is not reached |
| `invalid_dispatch_reservation` | canonical finite nonnegative parsed decimal; relation to prediction is not reached |
| `campaign_cost_cap_exceeded` | canonical finite nonnegative decimal equal to route prediction; this branch follows equality and then cap validation |

## Repaired Replay Excerpt

The exact repaired branch at
`src/research_assistant/survey/m20_live_worker.py:688`:

```python
error_to_block = {
    "dispatch_failed_closed": "dispatch_cost_unreconciled",
    "response_type_invalid": "dispatch_cost_unreconciled",
    "credential_echoed_in_response": "credential_echoed_in_response",
    "cost_contradiction": "cost_contradiction",
    "response_cost_unreconciled": "response_cost_unreconciled",
    "cost_state_changed_during_dispatch": "cost_state_changed_during_dispatch",
    "invalid_cost_state": "invalid_cost_state",
    "invalid_dispatch_reservation": "invalid_dispatch_reservation",
    "campaign_cost_cap_exceeded": "campaign_cost_cap_exceeded",
}
null_observed_errors = {
    "dispatch_failed_closed",
    "response_type_invalid",
    "credential_echoed_in_response",
    "response_cost_unreconciled",
}
required_observed_errors = {
    "cost_state_changed_during_dispatch",
    "invalid_cost_state",
    "invalid_dispatch_reservation",
}
observed_raw = evidence["observed_cost_usd"]
observed: Decimal | None = None
if observed_raw is not None:
    if not isinstance(observed_raw, str):
        raise M20WorkerError("published_cost_evidence_invalid")
    try:
        observed = Decimal(observed_raw)
    except InvalidOperation:
        raise M20WorkerError("published_cost_evidence_invalid") from None
    if (
        not observed.is_finite()
        or observed < 0
        or format(observed, "f") != observed_raw
    ):
        raise M20WorkerError("published_cost_evidence_invalid")
error_code = evidence["error_code"]
if (
    reconciled != prior_reconciled
    or evidence["credential_present"] is not True
    or evidence["cost_state"] != "blocked"
    or error_code not in error_to_block
    or evidence["cost_block_code"] != error_to_block[error_code]
    or (error_code in null_observed_errors and observed_raw is not None)
    or (
        error_code == "cost_contradiction"
        and (observed is None or observed == expected_cost_decimal)
    )
    or (error_code in required_observed_errors and observed is None)
    or (
        error_code == "campaign_cost_cap_exceeded"
        and observed != expected_cost_decimal
    )
):
    raise M20WorkerError("published_cost_evidence_invalid")
```

Existing surrounding replay already binds exact route prediction, reservation,
dispatch count, reconciliation non-advance, credential presence, blocked state,
block code, request-row cause, and summary hashes.

## Test Contract

The helper at
`tests/unit/test_literature_survey_m20_live_worker.py:115` mutates a real
cost-contradiction result, then rebinds both the request ledger SHA-256 in the
campaign summary and the final summary cost state. Therefore a rejection is
not caused by a stale outer digest.

The positive matrix covers every producer error using its allowed null or
canonical finite/nonnegative relation. The adversarial matrix covers:

- non-null values for all null-only errors;
- missing, predicted-equal, non-finite, and negative contradictions;
- missing, malformed, non-finite, negative, and noncanonical state-failure
  values; and
- wrong-cost and wrong-type cap-exceeded values.

## Checks Actually Run

All checks removed `OPENALEX_API_KEY`, used `PYTHONPATH=src`, deliberately hid
GPU with `CUDA_VISIBLE_DEVICES=-1`, injected only local synthetic transports,
and made no provider or network call.

- focused worker: `54 passed in 1.55s`;
- cumulative discovery/adapter/M20B2/worker/supervisor: `227 passed in 2.07s`;
- `py_compile`, milestone JSON validation, and `git diff --check`: passed;
- Git index: empty; no clone, wheel, packet, credential lookup, or live root.

## Verdict Question

Report only a material mismatch between the producer and repaired replay, a
test that does not actually exercise digest-rebound replay, or a boundary
regression caused by this repair.

End exactly with one of:

`VERDICT: AGREE`

`VERDICT: REVISE`
