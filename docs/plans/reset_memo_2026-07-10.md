# Reset Memo - Literature Survey Automation Reboot - 2026-07-10

## Objective

Resume the `research-assistant` literature-survey automation lane without
rediscovering the recent M15 work. The mission is not to build benchmarks for
their own sake; it is to let another agent or user start from an idea, topic, or
paper and run the survey evidence workflow in an easy way, preferably one
command.

Primary command surfaces:

```bash
ra survey run-public-source-workflow --topic "<topic>" --out <mission-dir>
ra survey run-public-source-workflow --topic "<topic>" --seed "<paper-id-or-title>" --out <mission-dir>
```

## Scope

Current release target:

- Brainstorming-first exploratory literature assistant.
- One user-friendly public-discovery confirmation per mission.
- Local/public discovery should proceed under that recorded confirmation until
  a real evidence, source/status, privacy, credential, review, or claim boundary
  is reached.

Files and artifacts in scope:

- `src/research_assistant/survey/orchestrate.py`
- `src/research_assistant/cli.py`
- `scripts/literature_survey_phase8_ux_validation.py`
- `tests/integration/test_cli_commands.py`
- `docs/plans/literature_survey_automation_mission_control_2026-07-06.md`
- `docs/plans/literature_survey_automation_milestones.json`
- `docs/plans/literature_survey_m15_*_2026-07-10.md`
- `docs/validation/literature_survey_live_public_source_phase8_2026-07-07/phase8_ux_validation_result.json`
- `docs/validation/literature_survey_benchmark_feedback_loop_2026-07-07/benchmark_findings.json`

Out of scope unless separately approved:

- Real Codex/Claude/Copilot subject trials.
- Credentials, private databases, hidden evaluator material, paid model-worker
  review, unbounded crawling, or writes outside the mission output directory.
- Live source/PDF/full-text execution outside a bounded mission approval.
- Scientific, product, literature-completeness, or final-prose-readiness claims
  from metadata, abstracts, citation counts, source availability, or unreviewed
  downloaded text.

## Current State

Checkpoint `2026-07-14`: M17 passed as
`PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`. Topic-only startup is now
implemented locally without fabricated original seeds; explicit-seed V2
behavior remains unchanged. The final successor manifest has `1,671` unique
sorted paths, includes all `1,137` canonical Phase 10 members (`1,136` files
and one symlink), validates all `38` direct logical rows, and replays with zero
mismatch. Primary Claude code review and fresh Codex artifact-closure fallback
review both returned `AGREE`. M18 reproducible local Git integration is now the
sole active milestone. No live provider/source, genuine human review, push,
release, or north-star completion claim follows from M17.

Policy migration: the current repository `AGENTS.md` supersedes legacy
hash-bound approval-token ceremony. The user's execute/resume request
authorizes reviewed non-destructive trusted-local M18 staging, commits, `/tmp`
clone/venv/wheel work, and CPU-only tests. External/irreversible boundaries
remain separately gated.

M16 Phases 0-10 are closed as
`PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`. Phase 10's fifth and final
independent implementation review returned `AGREE` with no findings against the
frozen candidate. Phase 11 is optional, unexecuted, and remains
`HUMAN_APPROVAL_REQUIRED_DO_NOT_EXECUTE`.

The canonical milestone ledger was reconciled on `2026-07-13`. Historical
M0-M15 entries are now completed/superseded by the stronger M16 authority rather
than incorrectly left active or pending. M16 is the completed local integrated
alpha. M17 is the sole active local planning milestone and closes the verified
idea/topic-start gap: current CLI and mission state still require at least one
paper seed. M18-M23 are the ordered path through Git reproducibility, bounded
live metadata, real citation discovery, source/anchor intake, genuine human
review and representative real missions, and final operator acceptance. No Git
action is authorized. The controlling program is
`docs/plans/literature_survey_north_star_gap_closure_master_program_2026-07-13.md`.
Phase 2 now provides coverage-before-queue topology, immutable selected
artifact sets, exact semantic queue identity, complete crash/retry coverage,
stale/corrupt/foreign downstream classification, and public-writer protection
for selected and orphan artifact-state paths. Final Phase 2 gates were `50`
focused tests, `142` combined Phase 1+2 tests, `346` unit tests, `69` CLI
integration tests, `6` exact survey-script tests, compilation/diff hygiene,
NUL-safe reconciliation, and fresh read-only `VERDICT: AGREE` after one repair.

Phase 3 now provides exact four-type reviewed-decision coverage, bound envelope
and sidecar replay, normative workflow evidence scopes, exact four-way merge,
stale/tampered/path-attack rejection, and a permanent Phase 3
`ready_for_prose=false` boundary. Final gates were `138` Phase 3 plus CLI,
`197` combined Phase 1-3, `401` unit, `83` CLI, `6` survey scripts, UX harness,
compilation, parse/diff/reconciliation, and a fresh hash-pinned read-only
`VERDICT: AGREE`.

Phase 4 now provides one canonical replayable packet binding selected packet
and coverage bytes, all four sidecars and decision envelopes, the clear merge,
anchor/source evidence, and optional local evidence. Hostile review consumes
only that packet, writes one authoritative result, and treats readiness as a
regenerable digest-bound view. Final gates were `30` focused, `227` combined
M16 Phase 1-4, `431` unit, `85` CLI integration, `6` survey scripts, UX,
compilation, parsing, writer-table, diff, reconciliation, and a fresh
hash-pinned `VERDICT: AGREE` after two bounded repair rounds.

Phase 5 now provides a writer-free observer, one lock-held bounded supervisor,
a closed typed local registry, exact multi-file and single-file repair
classification, crash/restart and concurrency behavior, and source-record-
bound anchor/public-packet replay. Final gates were `105` focused Phase 5/CLI,
`65` Phase 5 unit, `296` combined M16 Phase 1-5, `500` unit, `124` CLI, `6`
scripts, UX/compile/parse/writer/diff/reconciliation, and a fresh hash-pinned
`VERDICT: AGREE` after two implementation repair rounds.

Phase 6 now provides mission-scoped fixture-only V2 source intake. It binds
status to active ancestry, immutable generation payloads, exact metadata and
candidate authority, confirmation, budgets, ordered outcomes, and canonical
mission-local record bytes. Final gates were `79` Phase 6 unit, `121` focused
Phase 6/CLI, `375` combined M16 Phase 1-6, `579` unit, `124` CLI, `6` scripts,
UX/compile/parse/writer/diff/reconciliation, and four primary Claude Opus/max
`VERDICT: AGREE` excerpt reviews. The unrelated dirty arXiv modules remained
byte-identical.

Phase 7 now provides a replayed public-metadata V2 authority with conservative
seed/identity semantics, stable paper IDs, relevance-before-citation routing,
complete dispositions, and manifest-last durability. Its final gates were `58`
Phase 7 unit, `62` focused Phase 7/CLI, `137` Phase 6+7, `433` M16, `637` full
unit, `124` full CLI, `6` scripts, static/reconciliation checks, and four
primary compact Claude Opus/max agreements.

Phase 8 passed with deterministic fixture-only frontier/omission authority,
one-to-one risk reconciliation, immutable complete omission-decision sets, and
downstream invalidation. Phase 9 passed with exact fail-closed V2/V3 source,
claim, omission, merge, packet, hostile-review, and supervisor authority.

Phase 10 passed one positive and ten adversarial persistent offline missions.
Its final frozen manifest binds `38` direct rows; independent review reproduced
all `1,137` transitive rows and tree digest
`b6d5ddb4f52238abadaa07b5bd80ed74e478dab64088efa65eac3c7fd6c09d41`.
The eight JUnit artifacts total `2,337` tests with zero failures, errors, or
skips. Review rounds 1-4 found `14` defects, all repaired; round 5 agreed with
no findings. Claude export was policy-rejected, so the final reviews used fresh
Codex read-only fallbacks with explicitly downgraded provenance.

Phase 11 remains a separate human boundary. No live/API/provider/source/PDF/
full-text/GPU/paid action has been run by M16. Git integration is also pending
as a separate authority/procedure; the dirty worktree is not clean-checkout
reproducibility evidence.

M15 is complete for the current local orchestration surface.

Implemented:

- `run-public-source-workflow` emits a first-class
  `public_discovery_confirmation` object.
- Without confirmation, `next_action.json` asks one clear question:
  "Do you want RA to search public web/archive sources for this idea or paper?"
- `--confirm-public-discovery` records the single mission confirmation.
- Confirmed public metadata orchestration uses the existing bounded
  OpenAlex/arXiv metadata builder when metadata is missing.
- If public metadata exists and source/status is missing after confirmation,
  the workflow reports `blocked_missing_public_source_intake_artifact` with
  `approval_required=false` and `covered_by_public_discovery=true`.
- Source/status absence is now an implementation/artifact blocker, not a
  second ordinary public source/archive approval.
- Runtime nonclaims explicitly include live web coverage, literature
  completeness, survey completeness, source/PDF/full-text completion,
  retraction/version safety, technical claim support, final prose readiness,
  product readiness, and scientific correctness.

Updated control artifacts:

- `docs/plans/literature_survey_automation_mission_control_2026-07-06.md`
- `docs/plans/literature_survey_automation_milestones.json`
- `docs/plans/literature_survey_m15_single_approval_exploratory_discovery_master_program_2026-07-10.md`
- `docs/plans/literature_survey_m15_phase6_mission_feedback_closeout_result_2026-07-10.md`
- `docs/plans/literature_survey_m15_visible_stop_handoff_2026-07-10.md`

Review status:

- Claude external review was not retried because the earlier gate was rejected
  by the environment approval reviewer as external-model exfiltration risk.
- A fresh Codex read-only fallback review returned `VERDICT: AGREE`.
- Two low consistency issues from that review were patched:
  - stale "once Phase 2 is implemented" guidance;
  - missing literature/survey completeness runtime nonclaims.

## Validation

Latest checks run for M15:

```bash
python -m json.tool docs/plans/literature_survey_automation_milestones.json
PYTHONPATH=src:. python scripts/literature_survey_benchmark_feedback_summary.py
python scripts/literature_survey_phase8_ux_validation.py
PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k "run_public_source_workflow or public_metadata" -q
python -m py_compile src/research_assistant/survey/orchestrate.py src/research_assistant/cli.py
git diff --check
```

All passed.

Additional Phase 5 boundary regression checks passed:

```bash
PYTHONPATH=src pytest tests/integration/test_cli_commands.py -k "hostile_review or coverage_ledgers or run_public_source_workflow or public_metadata" -q
PYTHONPATH=src:. pytest tests/scripts/test_literature_survey_benchmark_feedback_summary.py tests/scripts/test_literature_survey_phase7_validation_harness.py tests/scripts/test_literature_survey_phase5_command_validation.py -q
```

Results:

- Integration boundary set: `10 passed, 52 deselected`.
- Script boundary set: `5 passed`.
- M15 focused set after review fixes: `8 passed, 54 deselected`.

## Remaining Gaps

No remaining gap blocks the M16 Phases 0-10 local engineering goal. The open
items are the north-star gap register, explicitly outside that completion claim:

1. `G0`: honest idea/topic bootstrap without requiring a fabricated paper seed.
2. `G1`: path-complete Git integration and clean-checkout reproducibility.
3. `G2`: converged hardening and one approved bounded live metadata smoke.
4. `G3`: real bounded idea/topic bootstrap, title/identifier resolution, and
   backward/forward/adjacent discovery.
5. `G4`: reviewed production source/status and capped source/PDF/full-text
   transport with hash-bound anchor candidates.
6. `G5`: genuine human identity/attestation and decisions; fixture/model rows
   must not impersonate human review.
7. `G6`: a predeclared representative real-mission matrix with at least one
   within-scope reviewed terminal and honest outcomes for the other cases.
8. `G7`: clean-install operator acceptance, documentation, recovery,
   compatibility, known limitations, and final control-plane closeout.

Literature completeness, universal scientific correctness, autonomous human
review, provider reliability at scale, and unattended production readiness are
not promised north-star completion claims.

## Evidence Contract For Next Work

The M17-M23 contracts are defined in the north-star master program. M17 must
close idea/topic bootstrap locally while preserving explicit-seed behavior and
write an immutable pre-edit M16 snapshot plus cumulative M17 successor
manifest. M18 must integrate every cumulative M16+M17 dependency, exclude
diagnostic/unrelated roots, and obtain exact approval before Git mutation. It
validates old hashes against the historical snapshot and current bytes against
the successor manifest. M19/Phase 11 must bind reviewed plan/code hashes, providers/domains,
query count, byte/time caps, output root, watchdog, and network boundary before
fresh live approval. Later milestones require separate citation, source-access,
human-review, and acceptance evidence. No milestone may reinterpret fixture
evidence as live, human, scientific, or product evidence.

M19-M21 fresh approvals are development/supervisor validation authority, not
additional production user prompts. Normal in-scope public metadata, citation,
archive, source-status, and capped source/PDF/full-text actions remain covered
by the single persisted mission confirmation once their transports exist.

## Next Safe Step

Preserve the frozen Phase 10 surface and its separate close record. Draft and
review the exact M17 idea/topic-bootstrap subplan and implement only after its
local contract converges. M18 then requires a separate reviewed Git-integration
subplan; do not stage, commit, push, or mutate Git until the user approves its
exact procedure. M19/Phase 11 remains pending after M18 and still requires
hardening convergence plus fresh exact live-access approval.

## Tidy Notes

- The worktree contains many existing untracked plan and validation artifacts
  from the broader literature-survey/SurveyBench effort. Do not delete or
  revert them unless the user explicitly asks.
- Preserve unrelated dirty files. The M15 closeout touched the survey
  orchestration, CLI, focused integration tests, Phase 8 UX validation, mission
  control, milestones, and M15 plan/result artifacts.
- The user approved sending repository artifacts to Claude for read-only
  review. Claude is responsive but Opus/max first-token latency can exceed 90
  seconds; use tiny health probes, self-contained micro-contracts, and bounded
  synthesis verdicts rather than accepting silence or fallback agreement.

## M18 Closeout Checkpoint - 2026-07-14

This checkpoint supersedes the older M17/M18 next-step prose above.

M18 passed local Git/install reproducibility at candidate
`654e6e1a1213bc03b7693ff1a8aea945a5bf08ac`, parent `1b36af0...`.
The exact candidate contains `1,725` paths; all `1,684` payload rows replayed
with digest `0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318`.
Attempt 1 built and installed wheel `891e1...` offline and passed all local
candidate gates. Terminal read-only review converged at round 3 after adding
row-level import/wheel provenance and a faithful command/procedure ledger.

`G0` and `G1` are now locally closed. Remaining north-star gaps are `G2-G7`:
bounded live metadata, real citation discovery, real source/status and anchors,
genuine human-attested review, representative real missions, and independent
operator/operational closeout. The north-star mission is not accomplished.

M19 is now the sole planning-only lane. Its refreshed parent remains
`DO_NOT_EXECUTE_LIVE`. The next safe action is a dedicated transport/
supervisor-hardening child subplan and skeptical audit. Live OpenAlex/arXiv
access still requires converged hardening, exact frozen routes/caps/hashes,
fresh material review, and fresh exact user approval.

No push, live provider/source action, GPU, credential, release, or destructive
Git action occurred in M18. Preserve the unrelated dirty/untracked worktree.

## M20A Route-Independent Checkpoint - 2026-07-14

M19 remains complete and its one approved attempt is consumed. Do not rerun it.

M20A route-independent engineering now passes. Runtime
`src/research_assistant/survey/discovery_capability.py` remains at SHA-256
`ceea83a8efcfb21d40533b0f42ff75e8b4cc0d0131916fb080a77ca2278189ba`.
The focused test was repaired to exercise the complete `6 x 7 x 7 = 294`
composition space: all `40` permitted tuples close from real producers and all
`254` forbidden tuples fail closed. The updated test SHA-256 is
`50a78d05365ad6660533916e071675cba233a07c04605ebd2be9149d9d5029ff`.

Final local gates pass CPU-only and no-network: M19+M20 `128 passed in 4.92s`;
affected M16/M17 `262 passed in 105.47s`. The result is
`docs/plans/literature_survey_north_star_m20a_route_independent_hardening_result_2026-07-14.md`.

The current repository policy retires hash-bound approval-token machinery for
trusted local work. Preserve the prior M20A blocker/review as history, but do
not rebuild canonical manifests merely to authorize more local work. The real
remaining M20A prerequisite is checked official arXiv/OpenAlex route evidence.
The next subplan is
`docs/plans/literature_survey_north_star_m20a_official_provider_contract_subplan_2026-07-14.md`.
M20B, provider API calls, M21, source/PDF/full-text, push, and release remain
`DO_NOT_EXECUTE`.

## M20A Official Contract Attempt 1 - 2026-07-14

The exact reviewed documentation fetch ran once and stopped correctly after two
transactions. It retained the official arXiv API manual (`160,616` bytes,
SHA-256 `14579fd2abb6d7c1aa0fe01af75754ea283852d4b8f63c3072ae31ebeb04b445`)
and observed a legacy OpenAlex documentation `301` to
`https://developers.openalex.org/`. The redirect was not followed; no retry or
alternate URL was attempted.

The local extract anchors arXiv `search_query`, `id_list`, `start`,
`max_results`, `sortBy`, `sortOrder`, Atom fields, and the documented
three-second multi-request cadence. OpenAlex route/field semantics remain
unchecked. Campaign budget use is `2/6` transactions and
`160,783/8,000,000` accepted response-body bytes, zero diagnostic overflow.

Treat this as an infrastructure repair trigger, not evidence against M20. The
next plan is
`docs/plans/literature_survey_north_star_m20a_openalex_documentation_root_subplan_2026-07-14.md`,
which may inspect exactly the observed official root once after review. M20B,
provider APIs, M21, source/PDF/full-text, push, and release remain forbidden.

## M20A Local Close - 2026-07-14

M20A local no-network engineering is complete. The fixed official
documentation campaign closed permanently at `6/6` transactions and
`2,390,766/8,000,000` accepted bytes with zero overflow. Both checked OpenAlex
operations require `api_key`; correct list syntax is `per_page` and
`sort=-cited_by_count`; the official `ids` object does not establish an arXiv
alias.

The strict route-specific adapter result is
`docs/plans/literature_survey_north_star_m20a_route_specific_openalex_adapter_result_2026-07-14.md`.
Adapter SHA-256 is
`e079e50a5e6024eda3425393816ecfe75e05608a1e8c99890648af3c28ffd31e`;
tests SHA-256 is
`a2a4603828ef6846df908df521f198a66d2161b0d4ba82f7f42fc3ccf8738c73`.
Final gates are adapter `59 passed`, M19+M20 `188 passed`, and affected
M16/M17 `846 passed`. Provider-returned OpenAlex IDs now require exact
`https://openalex.org/W<digits>` form across top-level identity,
`ids.openalex`, and backward lineage.

Claude was responsive to a tiny probe, but the substantive export was
policy-rejected and not routed around. A fresh Codex read-only fallback returned
`AGREE` and independently reproduced the focused test gate.

M20 is not complete. No live M20 frontier attempt or selected M20 authority
exists. The next planning-only artifact is
`docs/plans/literature_survey_north_star_m20b_credential_privacy_cost_decision_subplan_2026-07-14.md`.
Before any provider call, obtain current authentication/pricing/rate-limit
evidence, an authorized key source, approved redaction/privacy handling, a
numeric cost/credit cap, passing secret-leak and cost-accounting tests,
identified installed execution bytes, a reviewed exact packet, and explicit
human campaign authorization. Do not inspect environment secrets, reopen the
closed documentation campaign, execute M20B, start M21, push, or release.

## M20B1 Authentication/Pricing Checkpoint - 2026-07-14

M20B1 passed and its exact two-document attempt is consumed. The immutable
root retained `867,402/4,000,000` bytes over `2/2` successful transactions,
with zero overflow, redirects, retries, credentials, or provider API calls.
The worker exited `0`, was reaped, and terminal replay plus `42/42` post-run
CPU-only/no-network tests passed.

Official retained bytes establish query-parameter `api_key`, a `$1/day` keyed
allowance, current USD route pricing, `meta.cost_usd`, current rate-limit USD
fields, midnight-UTC reset, and a 100 requests/second ceiling. Planned M20
OpenAlex usage is `$0.0011`: one search `$0.001`, one singleton `$0`, and one
list/filter `$0.0001`. This does not establish a key, use authority, actual
balance, free execution, or provider readiness.

Terminal review converged in two rounds after repairing the M20B2 canary model
to allow only the named synthetic source and one ephemeral fake-sink-observed
authenticated request, with no occurrence allowed to persist or cross the
dispatch boundary.

The active plan is
`docs/plans/literature_survey_north_star_m20b2_synthetic_credential_redaction_cost_controls_subplan_2026-07-14.md`.
It is `DO_NOT_EXECUTE` until the human selects an authorized runtime interface,
approves the enumerated privacy/redaction rules, and sets a numeric maximum
total campaign cost. Recommended: `OPENALEX_API_KEY`, existing M20B0 privacy
rules, and `$0.01` total usage with unknown or unreconciled cost as a stop. Do
not send a secret value. M20B3/B4, provider calls, M21, source/PDF/full-text,
push, and release remain forbidden.

## M20B2 Local Synthetic Engineering Checkpoint - 2026-07-15

M20B2 is closed as passed in its authorized synthetic-only local scope. The
sole future runtime interface is `OPENALEX_API_KEY`; no real value was
inspected, read, hashed, or used. No provider or other network call occurred.
The approved total live-campaign usage cap remains USD `$0.01`, with unknown,
contradictory, or unreconciled cost as a hard stop.

The authoritative candidate is
`docs/validation/literature_survey_m20b2_synthetic_credential_cost_v8_2026-07-15/`.
It records 11 synthetic scenarios and exact `$0.0011/$0.01` closure. Final
local gates pass `33` focused, `221` combined M19/M20/M20B2, and `42` retained
M20B1 tests. Round-1 review returned `REVISE`; repairs added validated read-only
budget state, exact versioned reservation tokens, a locked synchronous
dispatch/reconciliation/evidence transaction, shared encoded-canary scanning,
and an explicit new-human-Git-authority gate. Round-2 review returned `AGREE`.

M20 and the north-star mission remain incomplete. The next plan is
`docs/plans/literature_survey_north_star_m20b3_identified_integration_and_live_packet_subplan_2026-07-15.md`,
but it is `DO_NOT_EXECUTE` until the human explicitly authorizes the exact
bounded M20B3 Git payload, stage/commit, isolated clone, and offline wheel
operation. This checkpoint authorizes no Git integration, real key access,
provider call, M20B4, source access, push, or release.

## M20B3 Five-Round Review Blocker - 2026-07-15

The human authorized bounded M20B3 local integration, but review did not
converge before the subplan's five-round stop. Round 5 found that
blocked-after-dispatch cost replay accepts producer-impossible
`observed_cost_usd` values; specifically, a digest-rebound
`dispatch_failed_closed` row with `"not-a-cost"` still passed replay.

The frozen candidate hashes are worker
`74e28e5099481826008a54a800dde10c314d914d7ecdd6ac7f4714261047b92b`,
supervisor
`96890d38f984bb579fdcc79eff1487dd39925a198d5d955980099a6ba7a30fb6`,
worker tests
`b3603622905d3b19ae9d7b89e5676f311133515d331f6d955b0e7e4250fa4bd3`,
and supervisor tests
`f7013e5229aa29b9288aabc5789ce0cd0eadb87f2afd83668fc35cf815ea8c7e`.
Focused checks pass `43/43`, but that does not rebut the adversarial finding.

No Git path was staged or committed; `HEAD` remains
`ad4e2d52ab9df7198547b3cb98d8acbd1b9680a5`. No clone, wheel, installed
validation, packet, credential lookup, or provider call occurred. The exact
blocker is
`docs/plans/literature_survey_north_star_m20b3_review_nonconvergence_blocker_result_2026-07-15.md`.
Continuing requires human direction on one additional narrowly scoped local
replay-integrity repair and terminal review round. M20B4, M21, source access,
push, release, and all completion claims remain blocked.

## M20B3 Extra Replay Repair Agreement - 2026-07-15

The human authorized one extra local repair and terminal review round limited
to blocked-after-dispatch `observed_cost_usd`. The repaired worker is
`ef873948aa3c61dea87a82a0af9d85154f7e8a2762961c4274dc941da1129157`;
the repaired worker tests are
`10d3b2f018d24d84a99eb1b4a0c788b6a0e2a6a9c6a20d89484842291fe28040`.
The supervisor artifacts remain unchanged.

Focused tests pass `54/54`, cumulative M20 tests pass `227/227`, and the fresh
Codex read-only fallback returned `AGREE`. Claude export was policy-rejected
before invocation and was not routed around. The five-round blocker is
historical but preserved. The already authorized bounded M20B3
Git/clone/wheel/install/packet-freeze lane is active. M20B4, real credentials,
provider calls, source access, M21, push, release, and completion claims remain
forbidden.
