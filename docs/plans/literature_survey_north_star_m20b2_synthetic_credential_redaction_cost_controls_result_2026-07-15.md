# M20B2 Synthetic Credential, Redaction, And Cost Controls Result

Date: `2026-07-15`
Status: `PASSED_LOCAL_SYNTHETIC_ENGINEERING_TERMINAL_REVIEW_AGREED_M20B3_GIT_AUTHORITY_REQUIRED`
Milestone: `M20_live_discovery_and_citation_frontier`

## Result

The authorized synthetic-only M20B2 implementation is complete locally. A new
boundary module accepts only the reviewed credential-free OpenAlex descriptor,
preflights exact route cost under the human-approved USD `$0.01` campaign cap,
then calls an injected getter for only `OPENALEX_API_KEY`. It constructs at
most one ephemeral authenticated request per dispatching invocation and returns
only accepted response bytes plus closed credential-free cost/error evidence.

Neither the module nor the synthetic validation script reads the real
environment, opens a network connection, or contains a live provider host.
No real key was inspected, read, requested, hashed, or used. The original
credential-free adapter remains byte-identical at SHA-256
`e079e50a5e6024eda3425393816ecfe75e05608a1e8c99890648af3c28ffd31e`.

## Exact Behavior

- Route costs are `topic_list=$0.001`, `direct_singleton=$0`, and
  `forward_list=$0.0001`; the exact planned total reserves and reconciles to
  `$0.0011` under the `$0.01` cap.
- Unknown route/cost, invalid descriptor, missing/blank/ambiguous/wrong-source
  credential, cap exhaustion, dispatch failure, malformed response,
  contradictory/missing/non-finite cost, or credential echo fails closed.
- Any dispatched request whose cost cannot be reconciled poisons the campaign
  budget and stops subsequent lookup/dispatch.
- Response-echo detection covers raw, percent-encoded, form-encoded,
  JSON-escaped, and one nested JSON-escaped representation. This is bounded
  tested coverage, not universal encoding detection.
- Closed evidence records the descriptor digest, route, selected interface
  name, credential-presence state, predicted/observed/reserved/reconciled USD,
  and closed error code. It contains no credential, authenticated URL, request
  object, exception text, account data, or billing state.

## Evidence And Repairs

Authoritative reviewed root:
`docs/validation/literature_survey_m20b2_synthetic_credential_cost_v8_2026-07-15/`.

The `v8` report contains 11 isolated success/failure scenarios. Every
dispatching invocation records exactly one named-source occurrence class and
one ephemeral fake-sink request occurrence class. Missing/wrong-source cases
record zero actual canary occurrences. Exact runtime scans found no canary on
the named prohibited surfaces, and final report/JUnit/code/test scans found no
runtime-canary prefix or credential-shaped literal.

Earlier roots are preserved but not promotable:

- attempt 1 incorrectly counted an empty credential getter result as a canary
  occurrence;
- `v2` followed that accounting repair but preceded the fake-sink
  ephemerality repair;
- `v3` followed the ephemerality repair but preceded encoded-echo hardening;
- a focused encoded-echo run passed `26` cases and failed the nested-JSON case,
  triggering the representation repair rather than weakening the test; and
- `v4` followed encoded-echo hardening but preceded the initial getter
  re-entrancy repair; and
- `v5` re-ran cost preflight after lookup, but round-1 terminal review correctly
  found that it did not bind an exact reservation token and scanned only raw
  canary bytes during IPC serialization; and
- `v6` implemented the material repairs, but the final concurrency audit found
  an unlock gap between reservation commit and dispatcher entry. `v6` is
  preserved as superseded by the `v7` transaction repair; and
- `v7` used manual context-manager entry/exit. It passed tests, but the final
  maintainability audit replaced that awkward control flow with a structured
  `with` transaction. `v7` is preserved as superseded by `v8`.

The round-1 repair makes budget properties read-only, validates finite,
nonnegative, mutually consistent internal state before every transition and
evidence read, and binds exact versioned state tokens across the getter and
dispatcher callbacks. Reservation is compare-and-set under one re-entrant lock
that remains held through the synchronous dispatcher, response validation,
reconciliation, and evidence construction. A separate in-flight flag excludes
overlapping dispatch even for the zero-cost singleton, and re-entrant mutation
or invalid state produces closed evidence. The approved raw,
percent/form, JSON, and one nested JSON representation set is now shared by
response, pre-serialization evidence/IPC, final serialized bytes, and runtime
validation scans. Tests cover blocked, under-cap re-entrant, concurrent getter,
dispatcher, counter, cap, non-finite, negative, wrong-type, and inconsistent
state mutations.

## Checks

| Check | Result |
| --- | --- |
| focused M20B2 | `33 passed in 0.20s` |
| combined M19/M20/M20B2 | first concurrent attempt exited `143` without an artifact; isolated retry `221 passed in 4.82s` |
| retained M20B1 suite | `42 passed in 0.28s` |
| authoritative report replay | `M20B2_V8_REPLAY_OK`; 11 scenarios; exact `$0.0011/$0.01` closure |
| canary-prefix scan | zero matches |
| credential-pattern scan | zero matches |
| compile / JSON / diff hygiene | passed |

The final local gates are complete. Round-1 material review returned `REVISE`;
the exact findings were repaired and the round-2 read-only review returned
`AGREE` with no material finding. M20B2 is closed in its authorized local
synthetic-only scope.

Review artifacts:

- `docs/reviews/literature_survey_north_star_m20b2_terminal_review_bundle_round1_2026-07-15.md`;
- `docs/reviews/literature_survey_north_star_m20b2_terminal_review_verdict_round1_2026-07-15.md`;
- `docs/reviews/literature_survey_north_star_m20b2_terminal_review_bundle_round2_2026-07-15.md`; and
- `docs/reviews/literature_survey_north_star_m20b2_terminal_review_verdict_round2_2026-07-15.md`.

## Decision Table

| Decision | Primary criterion status | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Close M20B2 local synthetic-only engineering after round-2 agreement | Exact interface, two-class occurrence model, locked versioned cost-state transaction, `$0.0011/$0.01` closure, `221` combined tests, and enumerated scans pass | No real-secret, network, cost, or canary-persistence veto observed on tested paths; round-2 review agrees | Untested OS/provider/proxy/shell/crash/swap surfaces and future live-worker integration | Stop and request new explicit human authority before the exact bounded M20B3 Git-integration operation | Universal leak freedom, real-key availability/use authority, provider readiness, actual balance/billing, Git integration, M20B3/B4 authority, M20 completion, or M21 readiness |

## Post-Run Red Team

The strongest alternative explanation is that the injected fake dispatcher and
enumerated encodings underrepresent a future real transport. The result does
not promote this standalone module directly to live use. M20B3 must integrate
the reviewed bytes into an identified worker/commit/install, rerun canary tests
against that exact transport, and freeze a separately reviewed packet. Any new
representation, callback retention, logging, IPC, proxy, or exception surface
invalidates the current scan claim until tested.

## Handoff Boundary

This result has passed material review. M20B3 nevertheless remains
non-executable until the human separately authorizes the exact bounded Git
payload, stage/commit, isolated-clone, and offline-wheel integration operation.
Even after any future M20B3 integration, no real key lookup or provider call is
authorized.
M20B4 remains a separate exact human authorization boundary. Source access,
M21, push, and release remain forbidden.
