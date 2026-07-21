# M20B3 Worker And Supervisor Read-Only Review Bundle

Date: `2026-07-15`
Scope: local M20B3 implementation only
Authority: reviewer is read-only and advisory; this bundle cannot authorize a
real credential, provider call, M20B4 execution, source access, push, release,
or any M20/north-star completion claim.

## Objective

Assess whether the bounded five-request M20 worker and its package supervisor
are internally consistent and fail closed before they are integrated into an
identified commit and frozen into a non-executable M20B4 packet.

Exact route order is arXiv topic, OpenAlex topic, arXiv seed `2201.12220v3`,
OpenAlex direct `W4387130479`, and OpenAlex forward
`filter=cites:W4387130479`. Caps are five requests, no retry/redirect/proxy,
2,000,000 bytes/request, 10,000,000 bytes total, 30 seconds/request, 367 seconds
whole attempt, and OpenAlex cost at most USD `$0.01` with unknown,
contradictory, or unreconciled cost a hard stop.

## Exact Reviewed Bytes

| File | SHA-256 | Relevant symbols/lines |
| --- | --- | --- |
| `src/research_assistant/survey/m20_live_worker.py` | `1bf151fa0075b0bf6109d5184843026a713511e9264fc6b642f5141e40638f88` | route manifest, strict arXiv parse, case derivation, offline replay, execution |
| `src/research_assistant/survey/m20_live_supervisor.py` | `e4624374b8d04836164a9b0f0cb0c50a7032e9da1f44d520f7ecf0dd8e149018` | packet preflight, artifact/replay validation, partial scrub, bounded lifecycle, one env lookup |
| `tests/unit/test_literature_survey_m20_live_worker.py` | `05bf710dcecf9a0b69ab6a14a35b96d6268d52da1521d129574407d143c07380` | focused worker and offline replay regressions |
| `tests/unit/test_literature_survey_m20_live_supervisor.py` | `8709b667c78f41c1eb5c6bef8ef7c1abb2fd9e4ad4b87605d3d1a000e61b6b64` | packet, lifecycle, privacy, and manifest regressions |

Do not infer these paths are committed yet. M20B3 integration follows review.

## Prior Independent Codex Findings And Visible Repairs

1. Backward boundary invalidity initially reached request five too late.
   Repair: successful direct parsing now sets the campaign hard stop immediately
   when its backward view is boundary-invalid. Regression verifies the forward
   ledger row is `not_dispatched_due_to_veto` and only two OpenAlex dispatches
   occur.
2. The initial arXiv parser accepted weak envelopes/identifiers and dropped DOI.
   Repair: it now requires an Atom `feed`, exactly one nonnegative ASCII-decimal
   `opensearch:totalResults`, canonical arXiv entry URLs/IDs, row-level malformed
   dispositions, DOI normalization, and cap propagation. Regressions cover
   malformed envelope/total, malformed row identity, cap, DOI retention, and
   cross-provider DOI merging.
3. Supervisor replay was initially shallow.
   Repair: installed worker `validate_published_run()` reparses every bound raw
   body, reconstructs exact per-case inventories/replays and identity/frontier
   outcomes, checks route-row schemas/bindings/statuses, accepted-body
   counts/bytes, lookup evidence, cost progression, summary hashes, campaign
   validity, and negative results. Supervisor completion requires that replay.
   Tamper regressions cover raw body, inventory, classifier, accounting, and
   lookup count.
4. Failure paths initially did not remove partial credential-bearing artifacts.
   Repair: every non-completed lifecycle scrubs the bounded fresh root before
   manifest-last publication; completed paths scan all allowed artifacts for
   credential representations and remove a detected secret-bearing file.
   Regressions cover zero-exit leak, nonzero partial leak, timeout partial leak,
   and symlink-root replacement.

## Checks Actually Run

All commands removed `OPENALEX_API_KEY`, deliberately hid GPU devices with
`CUDA_VISIBLE_DEVICES=-1`, used `PYTHONPATH=src`, injected synthetic transports,
and made no provider call.

- `py_compile` on the three retained M20 modules, worker/supervisor, and focused
  tests: exit `0`.
- cumulative M20 discovery/adapter/M20B2/worker/supervisor pytest set:
  `190 passed in 1.11s`, exit `0`.
- `git diff --check` on the exact M20 code/test candidates: exit `0`.
- Synthetic canaries are absent from persisted result roots. No real
  `OPENALEX_API_KEY` value was inspected or used.

## Review Questions

Return material correctness or boundary findings only.

1. Does the repaired worker stop request five when direct identity or backward
   view is boundary-invalid while preserving unavailable-provider continuation?
2. Is the strict arXiv envelope/identifier/DOI/cap behavior consistent with the
   frozen M20 identity automaton?
3. Can a self-consistent top-level artifact rewrite, raw-body mutation,
   inventory/replay mismatch, classifier mutation, credential-lookup mutation,
   or inconsistent cost progression still receive supervisor `completed`?
4. Can a crash, timeout, nonzero worker, root replacement, stream, argv,
   environment inheritance, or exception text persist the credential in a
   reviewed artifact?
5. Does packet preflight validate exact packet hash, Git/tree, wheel/member,
   installed module origins/hashes, route manifest, caps, command, and absent
   root before the single named environment lookup?
6. Is any code or wording treating M20B3 review or packet freeze as M20B4
   execution authority or as M20 completion?

Known limitation: M20B3 is synthetic-only engineering. It establishes neither
provider behavior nor live result validity. The exact commit, isolated wheel,
installed-member equality, and final non-executable packet are not yet created;
they follow only if this code review converges.

End with exactly one of:

`VERDICT: AGREE`

`VERDICT: REVISE`
