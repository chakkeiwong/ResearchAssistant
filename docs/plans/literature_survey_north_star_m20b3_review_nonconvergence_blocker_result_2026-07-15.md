# M20B3 Review Nonconvergence Blocker Result

Date: `2026-07-15`
Status: `BLOCKED_M20B3_REVIEW_NONCONVERGENCE_AFTER_FIVE_ROUNDS_NO_GIT_ACTION`
Milestone: `M20_live_discovery_and_citation_frontier`

## Phase Result

M20B3 did not pass. The bounded worker/supervisor candidate reached five
material review rounds, and the final round found that offline replay still
accepts a producer-impossible `observed_cost_usd` value for
blocked-after-dispatch evidence. The defect is localized and repairable, but
the phase's explicit five-round nonconvergence stop fired before Git
integration.

No payload was staged or committed. No isolated clone, wheel, installed-member
manifest, installed synthetic validation, or M20B4 packet was created. No real
`OPENALEX_API_KEY` value was inspected or used, and no provider or other
network call occurred.

## Entry And Preserved Baseline

- Git `HEAD` remains `ad4e2d52ab9df7198547b3cb98d8acbd1b9680a5` with tree
  `0796411d72225075518bd62dd83b9c15edf85f8b`.
- The Git index is empty.
- Protected unrelated dirty paths remain unstaged and untouched by M20B3.
- M20A, M20B1, and M20B2 remain passed only in their already recorded bounded
  scopes.
- The absent M20B3/M20B4 live roots remain absent.

## Candidate Artifacts

| Artifact | Frozen SHA-256 | Status |
| --- | --- | --- |
| `src/research_assistant/survey/m20_live_worker.py` | `74e28e5099481826008a54a800dde10c314d914d7ecdd6ac7f4714261047b92b` | local candidate; not integrated |
| `src/research_assistant/survey/m20_live_supervisor.py` | `96890d38f984bb579fdcc79eff1487dd39925a198d5d955980099a6ba7a30fb6` | local candidate; not integrated |
| `tests/unit/test_literature_survey_m20_live_worker.py` | `b3603622905d3b19ae9d7b89e5676f311133515d331f6d955b0e7e4250fa4bd3` | local candidate; not integrated |
| `tests/unit/test_literature_survey_m20_live_supervisor.py` | `f7013e5229aa29b9288aabc5789ce0cd0eadb87f2afd83668fc35cf815ea8c7e` | local candidate; not integrated |

## Five-Round Review Record

| Round | Verdict | Material issue class |
| --- | --- | --- |
| 1 | `REVISE` | early backward veto, strict arXiv parsing, replay depth, partial-secret cleanup |
| 2 | `REVISE` | moving review target, exact route cost transitions, finite-decimal replay |
| 3 | `REVISE` | replay exception closure, status vocabulary, contradictory arXiv total |
| 4 | `REVISE` | exact status/cost-state mapping and request-row/evidence error coupling |
| 5 | `REVISE` | blocked-after-dispatch `observed_cost_usd` remains underconstrained |

Claude returned the tiny health token but returned no output for the bounded
packet-read/substantive prompts. Under the read-only review probe procedure, a
fresh Codex reviewer was used. The reviewer was advisory only and performed no
execution or repository mutation.

## Required Local Checks

| Check | Result |
| --- | --- |
| resumed invocation without `PYTHONPATH=src` | collection failed because the shell resolved a different installed package; classified environment-mismatch non-evidence |
| corrected focused worker/supervisor suite | `43 passed in 1.07s` with `PYTHONPATH=src`, `OPENALEX_API_KEY` removed, and `CUDA_VISIBLE_DEVICES=-1` |
| `py_compile` on four frozen artifacts | passed |
| `git diff --check` on four frozen artifacts | passed |
| frozen SHA-256 replay | all four exact hashes matched |
| staged-path check | empty Git index |
| live-root check | M20B3 and M20B4 live roots absent |

These checks show that the existing candidate is locally executable under its
tested synthetic cases. They do not rebut the adversarial replay counterexample
and therefore cannot promote M20B3.

## Exact Repair Needed

A future narrowly scoped repair should change only installed-artifact cost
replay and focused tests:

1. Parse any non-null `observed_cost_usd` as a finite nonnegative `Decimal`.
2. Require `null` for `dispatch_failed_closed`, `response_type_invalid`,
   `credential_echoed_in_response`, and `response_cost_unreconciled`.
3. Require a finite nonnegative observed value unequal to the route's predicted
   cost for `cost_contradiction`.
4. Bind state/reconciliation failure codes to the exact observed-value shapes
   reachable from `execute_authenticated_openalex_request()`.
5. Add positive producer cases and digest-rebound adversarial tests for every
   blocked-after-dispatch error code.
6. Rerun focused and cumulative credential-free CPU-only checks and obtain one
   terminal read-only review of the repaired frozen bytes.

This repair must not weaken the five-request matrix, cost cap, privacy model,
route contract, output contract, nonclaims, or later human boundaries.

## Decision Table

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Stop M20B3 before Git integration | Failed: five-round material review did not converge | Continuation veto fired: producer-impossible cost evidence can pass offline replay | Exact reachable observed-value set for rare state/reconciliation failures needs an explicit test matrix | Obtain human direction for one narrowly scoped replay-integrity repair and one terminal review round | M20B3 pass, identified install, packet readiness, M20B4 authority, live provider behavior, M20 completion, or north-star completion |

## Stop And Handoff

The exact next safe action is a new human decision on whether to permit one
additional narrowly scoped local repair and terminal review round limited to
the `observed_cost_usd` replay automaton and its tests. Until then, do not edit
the four frozen candidate artifacts, stage or commit the M20 payload, clone or
build the candidate, freeze or execute M20B4, inspect a credential, call a
provider, access source/PDF/full text, push, release, or start M21.
