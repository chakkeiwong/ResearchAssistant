# M20B2 Synthetic Credential/Cost Terminal Review Bundle, Round 2

Date: `2026-07-15`
Supervisor/executor: Codex
Reviewer: fresh Codex read-only fallback
Status: `REVIEW_PENDING_AFTER_ROUND1_REVISE`

## Read-Only Boundary

Review only. Do not edit, run commands, inspect environment variables or real
credentials, use network, call a provider, stage/commit, access sources, push,
release, or execute M20B3/M20B4. Agreement is advisory only. Current authority
still excludes Git integration, provider calls, real credential access,
M20B3/M20B4 execution, sources, push, and release.

## Round-1 Findings To Verify

1. M20B3 lacked an explicit new-human-Git-integration authority gate.
2. Mutable budget state was not fully validated or closed on corruption.
3. The claimed post-getter exact reservation token did not exist; under-cap
   re-entrant mutation remained possible.
4. IPC serialization scanned only raw canary bytes, not the approved encoded
   forms.
5. `v5` result/manifest claims overstated those repairs.

The exact round-1 verdict is:
`docs/reviews/literature_survey_north_star_m20b2_terminal_review_verdict_round1_2026-07-15.md`.

## Final Candidate And Exact Hashes

Authoritative candidate root:
`docs/validation/literature_survey_m20b2_synthetic_credential_cost_v8_2026-07-15/`.

- boundary module:
  `9fe8f51937589c07d2cfe2e03807f96834f42e14fdadde56c5b6da1423717a8c`;
- validation script:
  `50c58a86eaf6af29487343af8fb1e99714b3cfc3f91e2fe569cc52160c659449`;
- unit tests:
  `923189643b9411bdb4a8c7570d35e2a80ae76a8c9c8106cf346b4c9f4334d68d`;
- script tests:
  `54d4f70d8077848b015891a460cc433b219552905b75c8f3d1b6ae3383981689`;
- synthetic report:
  `e7bfcee324c3d0c318da7b95cd4e02ccffddbf8e8d63697abc23fc8d5380c58a`;
- focused JUnit:
  `c3ca2326cd63031c65ee851fe0415c21eab3deaab43aca4220c99bffb8347a14`;
- isolated combined-retry JUnit:
  `35c2d06961c867f920f10cb099410f4153a578631d1db167f6bfb3f1a6f2e591`;
- retained M20B1 JUnit:
  `f57156b9ae01c226bbcc0c312994f3942cffa4051da91da9abca7735b6f53ede`.

## Bounded Repair Surface

Inspect only:

- `src/research_assistant/survey/openalex_credential_cost.py`, lines 61-277,
  381-430, and 433-end;
- `tests/unit/test_literature_survey_m20b2_credential_cost.py`, especially the
  invalid-state, getter mutation, dispatcher mutation, concurrent lock, encoded
  response, campaign closure, and IPC tests;
- `scripts/literature_survey_m20b2_synthetic_validation.py`, especially the
  shared representation scan in `_run_case`;
- `docs/validation/literature_survey_m20b2_synthetic_credential_cost_v8_2026-07-15/evidence_manifest.json`;
- `docs/plans/literature_survey_north_star_m20b2_synthetic_credential_redaction_cost_controls_result_2026-07-15.md`;
- `docs/plans/literature_survey_north_star_m20b3_identified_integration_and_live_packet_subplan_2026-07-15.md`, especially status, entry conditions, forbidden
  actions, handoff, and stop conditions.

Do not inspect the whole repository.

## Repair Summary

- Budget fields are exposed as read-only properties; internal finite,
  nonnegative, cap, reconciliation, count, block-code, in-flight, and version
  invariants are validated before transitions and evidence.
- `prepare_reservation()` emits a frozen exact state token.
  `_mark_dispatched_locked()` compares that token before reservation.
- One re-entrant lock remains held through synchronous dispatcher execution,
  response validation, cost reconciliation, and returned evidence construction.
  Re-entrant callback changes alter the version/token and fail closed; external
  threads cannot create a commit/dispatch/reconcile unlock gap.
- An explicit in-flight flag excludes overlap even for the zero-cost singleton.
- The raw, percent/form, JSON, and one nested JSON representation set is shared
  by response scanning, validation scans, pre-serialization evidence-leaf
  scans, and final IPC-byte scans.
- Adversarial tests cover negative/non-finite/wrong-type/cap/counter/inconsistent
  state, invalid budget object, already-blocked mutation, under-cap same-thread
  and concurrent getter mutation, dispatcher mutation, no concurrent unlock
  gap, encoded response echo, encoded/nested IPC, poisoning, cap closure, and
  exact three-route reconciliation.
- M20B3 status and entry/forbidden clauses explicitly require new human
  authority for the exact bounded Git payload, stage/commit, isolated clone,
  and offline wheel operation. Review or prior execute/resume cannot substitute.
- Roots through `v7` remain preserved and are marked superseded. `v8` is the
  only candidate.

## Final Local Evidence

- report replay: 11 cases, exact occurrence classes, zero prohibited-surface
  occurrence, `$0.0011/$0.01` closure;
- focused: `33 passed in 0.20s`;
- combined attempt 1: exited `143` while multiple local pytest commands ran
  concurrently, before creating an XML artifact; classified infrastructure and
  not evidence;
- exact combined retry run alone: `221 passed in 4.82s`, zero failures/errors;
- retained M20B1: `42 passed in 0.28s`;
- compile, JSON/XML parse, scans, and `git diff --check`: passed;
- all commands were CPU-only, removed `OPENALEX_API_KEY` from the child
  environment, and used no network.

## Review Questions

1. Does the state-token plus locked transaction now close both under-cap
   re-entrant and concurrent mutation without allowing invalid state or
   exceptions to escape?
2. Is holding the re-entrant lock through the synchronous injected dispatcher,
   response validation, reconciliation, and evidence consistent with this
   M20B2 local boundary and honestly limited as a synchronous design?
3. Do the shared representation generator and pre-/post-serialization scans
   satisfy the explicitly bounded raw/percent/form/JSON/one-nested-JSON
   contract without implying universal encoding coverage?
4. Are the tests and `v8` evidence adequate and accurately classified,
   including the interrupted combined attempt and isolated retry?
5. Does the result avoid unsupported safety/provider/billing/completion claims?
6. Is M20B3 unambiguously non-executable absent new human Git-integration
   authority, and does it avoid treating review as later-phase authority?

Return findings in severity order with exact anchors. End exactly:

`VERDICT: AGREE`

or

`VERDICT: REVISE`
