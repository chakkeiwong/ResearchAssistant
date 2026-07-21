# M20 Recovery Promotion And Cost-Gate Repair Result

Date: `2026-07-17`
Status: `PASSED_LOCAL_REPAIR_SUCCESSOR_INTEGRATION_PENDING`
Plan: `docs/plans/literature_survey_north_star_m20_recovery_campaign_plan_2026-07-17.md`

## Trigger

The skeptical pre-execution audit rejected the unexecuted `ba659518` candidate
before any credential lookup or provider call. Two material gaps remained:

1. `campaign_validity=closed` covered valid negative identity outcomes, but the
   recovery closeout treated every such outcome as M20 success even when no
   explicit real candidate had selected authority.
2. The predecessor campaign state tracked cumulative remaining cost but did
   not prove before credential lookup that an attempt-02 state could cover the
   fixed maximum next-attempt reservation.

The `ba659518` packet and validation root are therefore superseded unexecuted
evidence and must not be launched.

## Repair

- Installed replay now derives `selected_candidate_authority` from the
  replayed explicit arXiv-seed outcome or the replay-validated OpenAlex direct
  case authority.
- Recovery closeout requires that authority for
  `m20_primary_criterion_passed=true`.
- A replay-valid, cost-reconciled, privacy-passing closed run without explicit
  candidate authority writes the exact terminal status
  `BLOCKED_NO_SELECTED_REAL_CANDIDATE_AFTER_FROZEN_MATRIX`; it is not promoted
  and is not retried merely to seek a better result.
- Supervisor campaign-state validation now requires `remaining_cost_usd` to
  cover the fixed OpenAlex route reservation sum of USD `$0.0011` before any
  credential lookup. This is derived from the reviewed route-cost table:
  topic list `$0.001`, direct singleton `$0`, and forward list `$0.0001`.

## Checks

All checks removed `OPENALEX_API_KEY`, intentionally hid GPU devices with
`CUDA_VISIBLE_DEVICES=-1`, disabled bytecode writing, and used no network.

| Check | Result |
| --- | --- |
| Focused worker, supervisor, launcher, and recovery-closeout matrix | `133 passed in 2.36s` |
| No-selection closeout catching case | exact blocker status; primary criterion false; retry false |
| Attempt-02 insufficient remaining-cost catching case | rejected in packet preflight before credential lookup |
| Python compile | passed |
| `git diff --check` | passed |

The first test invocation failed during collection because the active shell
environment did not install the repository package. It ran no tests and no
external action. The corrected source-tree invocation used explicit
`PYTHONPATH=src`; its first focused pass found one temporary-fixture Git
identity issue (`132 passed, 1 failed`), which was repaired without changing
product behavior, followed by the clean `133/133` result above.

## Evidence Boundary

| Boundary | State |
| --- | --- |
| Historical consumed M20B4 packet rerun | false |
| Superseded recovery packet execution | false |
| Real `OPENALEX_API_KEY` inspected, read, or used | false |
| Provider or other network call | false |
| Provider usage cost | USD `$0.00` |
| Source/PDF/full-text access | false |
| M21, push, release, or north-star claim | false |

## Handoff

Create a single-parent successor commit containing only this bounded repair,
its tests, and the updated campaign evidence contract. Reproduce it from a
clean isolated checkout, build an offline wheel, verify complete installed
member equality, run installed credential-free synthetic validation, and
freeze a fresh unexecuted attempt packet. Obtain one material advisory review
of that exact successor before reaching the credential/provider boundary.
