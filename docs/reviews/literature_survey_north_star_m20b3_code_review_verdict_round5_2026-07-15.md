# M20B3 Code Review Verdict Round 5

Date: `2026-07-15`
Reviewer: fresh Codex read-only fallback
Verdict: `REVISE`

## Exact Reviewed Bytes

| File | SHA-256 |
| --- | --- |
| `src/research_assistant/survey/m20_live_worker.py` | `74e28e5099481826008a54a800dde10c314d914d7ecdd6ac7f4714261047b92b` |
| `src/research_assistant/survey/m20_live_supervisor.py` | `96890d38f984bb579fdcc79eff1487dd39925a198d5d955980099a6ba7a30fb6` |
| `tests/unit/test_literature_survey_m20_live_worker.py` | `b3603622905d3b19ae9d7b89e5676f311133515d331f6d955b0e7e4250fa4bd3` |
| `tests/unit/test_literature_survey_m20_live_supervisor.py` | `f7013e5229aa29b9288aabc5789ce0cd0eadb87f2afd83668fc35cf815ea8c7e` |

## Material Finding

The installed-artifact replay at
`src/research_assistant/survey/m20_live_worker.py:688` does not bind
`observed_cost_usd` to the producer's blocked-after-dispatch automaton. A real
`dispatch_failed_closed` row has `observed_cost_usd=null`, but replacing that
value with `"not-a-cost"`, rebinding the enclosing ledger digest, and replaying
the artifact still returned `passed`.

Replay must require:

- `null` for dispatch failure, invalid response type, credential echo, and
  response-cost-unreconciled;
- a finite nonnegative decimal unequal to predicted cost for
  `cost_contradiction`; and
- the producer-compatible finite observed value for cost-state and
  reconciliation failures.

The round-4 request-row/evidence error coupling and the other producer status,
credential, cost-state, and block-code mappings are repaired correctly.

## Checks

All four hashes matched. With `OPENALEX_API_KEY` removed,
`CUDA_VISIBLE_DEVICES=-1`, and `PYTHONPATH=src`, the worker/supervisor suite
passed `43` tests. `py_compile` and `git diff --check` passed. No provider or
network action occurred.

## Gate Consequence

This is the fifth material review round on the M20B3 replay-integrity blocker.
The subplan's five-round stop condition is therefore active. No Git staging,
commit, isolated clone, wheel build/install, M20B4 packet freeze, real
credential access, or provider execution may follow this verdict without new
human direction.

`VERDICT: REVISE`
