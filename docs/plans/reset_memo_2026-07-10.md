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
