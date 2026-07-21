# M16 Phase 10 Subplan - Offline End-to-End Validation And Local Closeout

Date: `2026-07-13`
Status: `IMPLEMENTATION_REPAIR_ROUND2_AUTHORIZED`

## Phase Objective

Run a persistent deterministic positive mission and a predeclared adversarial
matrix through the public survey CLI and canonical safe-local supervisor. Prove
terminal behavior, exact blocker classification, current-selector use,
idempotent resume, forbidden descendant absence, and zero forbidden capability
calls; then close the M16 local engineering program without claiming Git, live,
human, scientific, prose-quality, product, or release evidence.

## Entry Conditions Inherited From Phase 9

- Phases 0-9 are `PASSED` locally.
- Governing Phase 9 subplan:
  `docs/plans/literature_survey_m16_phase9_evidence_semantics_subplan_2026-07-10.md`,
  SHA-256 `13301f7bd8235aea4d9c2bf200a9ee6110766a7c64022a95a2395a9a7816102e`.
- Phase 9 result:
  `docs/plans/literature_survey_m16_phase9_evidence_semantics_result_2026-07-12.md`,
  SHA-256 `312a276beceeafecd86fc17e8fa7cda60b830b3a35012876cc99e8e233d77649`.
- Phase 9 round-3 implementation verdict:
  `docs/reviews/literature_survey_m16_phase9_implementation_review_verdict_round3_2026-07-13.md`,
  SHA-256 `41c9313faea2ba5f0df6e6b0fcbee9c027c5713c24374af95fcbd21a9cb06353`,
  `VERDICT: AGREE`.
- Frozen Phase 9 change manifest:
  `docs/validation/literature_survey_m16_phase9_2026-07-12/change_manifest.json`,
  SHA-256 `9a5e1736d1587a80d8b9c976b996291e1aaf42c67b44368712c7e4db285f0443`.
- Phase 9 run manifest:
  `docs/validation/literature_survey_m16_phase9_2026-07-12/run_manifest.json`,
  SHA-256 `22b7de0ff22b3394dd4125b4468cfc857ad6937dbfdbc5fdc4bd6de1ac0f35a7`.
- Phase 9 final gates were `33` omission-lineage, `7` auxiliary-schema,
  `29` retained/current, `139` Phase 8, `209` Phase 9, `635` Phase 3-9,
  `985` full unit, `125` full CLI, and `6` exact script tests, plus clean UX,
  compile, parse, writer, AST, protected-hash, diff, and reconciliation gates.
- The Phase 8 `open_quarantine_risk` boundary remains open in missions that
  contain unresolved frontier targets. Phase 10 may create a separate
  deterministic zero-open-risk positive fixture; it may not rewrite Phase 8
  evidence or claim that real omissions are closed.
- The heavily dirty baseline is preserved. No staging, commit, reset, restore,
  stash, clean, or unrelated edit is authorized.

Entry verification command:

```bash
sha256sum \
  docs/plans/literature_survey_m16_phase9_evidence_semantics_subplan_2026-07-10.md \
  docs/plans/literature_survey_m16_phase9_evidence_semantics_result_2026-07-12.md \
  docs/reviews/literature_survey_m16_phase9_implementation_review_verdict_round3_2026-07-13.md \
  docs/validation/literature_survey_m16_phase9_2026-07-12/change_manifest.json \
  docs/validation/literature_survey_m16_phase9_2026-07-12/run_manifest.json
```

Any mismatch is a continuation veto until reconciled; it is not silently
accepted as a newer baseline.

## Research Intent And Evidence Contract

| Field | Contract |
| --- | --- |
| Engineering question | Does the integrated offline workflow reach the exact intended terminal state for a valid fixture mission and fail closed with the exact declared blocker for adversarial missions? |
| Candidate/mechanism | Public CLI imports plus the canonical `run-public-source-workflow --resume --run-safe-local` supervisor operating on current V2/V3 selectors. |
| Baseline/comparator | Phase 9 component and CLI tests. They establish local pieces but are not persistent Phase 10 E2E mission evidence. |
| Primary promotion criterion | The persistent positive mission reaches `terminal_ready_for_reviewed_prose_within_recorded_scope`, the second identical CLI run has zero transitions and byte-identical authoritative outputs, every persistent negative reaches its predeclared code with forbidden descendants absent, and all required repository gates pass. |
| Promotion vetoes | False readiness; wrong blocker; changed authoritative bytes on identical resume; stale/foreign/corrupt authority accepted; missing required negative; provider/network/source/model/GPU/outside write; Phase 8 open risk disappearing without a distinct valid fixture; hash or reconciliation mismatch. |
| Continuation vetoes | Invalid inherited hashes; unexplained overlapping user edit; correct repair requiring forbidden live/external/Git/human/scientific authority; repeated environment failure with no in-scope repair; five reviews on the same blocker without convergence. |
| Repair triggers | Harness failure, catching test failure, exact terminal mismatch, missing tripwire, static/hash drift, or a fixable review `REVISE`. |
| Explanatory only | Runtime, mission size, transition count, queue counts, broad non-CLI integration timeout, and intermediate failed repair artifacts. |
| What is not concluded | Authenticated human review, source safety in fact, claim truth, omission correctness, literature completeness, scientific correctness, prose quality, Git reproducibility, live reliability, product/release readiness, or superiority. |
| Preserving artifacts | `docs/validation/literature_survey_m16_phase10_2026-07-13/e2e_summary.json`, `run_manifest.json`, `change_manifest.json`, JUnit/log artifacts, and the Phase 10 result. |

Evidence roles are fixed before execution. A component test can catch or explain
an invariant but cannot be reported as a persistent E2E mission. A fixture
builder result cannot be promoted; only the public CLI/import/supervisor outputs
and their exact validators satisfy the primary criterion.

## Skeptical Pre-Execution Audit

The prior 77-line draft was not executable. It omitted exact terminal codes,
test layering, harness allowlist, timeouts, tripwires, artifact schemas, and the
distinction between fixture construction and the system under test.

This refresh addresses the required skeptical checks:

1. `Wrong baseline`: Phase 10 compares against the hash-attested Phase 9 dirty
   workspace, not a clean checkout and not M15.
2. `Proxy promotion`: metadata/source fixture construction is input setup only.
   It cannot satisfy the primary criterion. The CLI imports, current selectors,
   safe-local supervisor, validators, and byte replay are the system under test.
3. `Missing stop conditions`: continuation vetoes and repair triggers are
   separated. A rejected negative candidate or fixable implementation failure
   does not stop the program.
4. `Unfair comparison`: this is deterministic state-machine validation, not a
   method ranking. No performance or scientific comparison is made.
5. `Hidden assumptions`: synthetic human-shaped decisions must carry
   `fixture_only=true` where the V3 schema requires it and must be labeled
   `synthetic-fixture-reviewer`; they are never represented as authenticated
   human work.
6. `Stale context`: the plan binds the final Phase 9 result, verdict, manifest,
   run manifest, and code hashes. Every mission resolves current selectors at
   runtime rather than using copied sidecar paths.
7. `Environment mismatch`: every Python/test command sets
   `CUDA_VISIBLE_DEVICES=-1`; GPU is intentionally hidden. No package install or
   network access is needed. GNU `timeout` is available.
8. `Non-answering commands`: the standalone harness persists the positive and
   negative mission trees and a structured matrix; named component nodes cover
   exhaustive crash/schema/path cases that would be wastefully duplicated in
   the persistent harness.
9. `Misleading pass pre-mortem`: the harness could pass if its fixture builder
   bypasses the CLI or if monkeypatches suppress validators. Therefore fixture
   setup and CLI execution are separately logged, CLI return/payload/artifact
   paths are asserted, public provider transports are tripwired to raise, and
   the positive mission is replayed by the same CLI command without setup
   monkeypatches.
10. `Misleading fail pre-mortem`: a negative could fail during fixture setup
    rather than at its intended gate. Each row records `setup_status`, exact
    `observed_stage`, `expected_status/action/reason`, and forbidden descendants;
    setup failure does not count as observing the target veto.

Round 1 independent review returned `REVISE`. The same plan was visibly
repaired by demoting the injected hostile-veto case to component evidence,
preserving a genuinely absent output root until the harness starts, correcting
the noncanonical-root terminal action, and distinguishing the declared
synthetic V1 packet input from forbidden generated descendants.

Round 2 independently reviewed plan SHA-256
`911545c9935f5f5a7e6cb94acccf9ef24a90b0e903cfc482257b095430823730`
and returned `VERDICT: AGREE`. The status and this review record are an
administrative post-review delta only; they do not change the reviewed
execution contract.

The first focused harness run then showed that a symlinked reviewed packet is
rejected by the earlier generic artifact-safety observation as action
`terminal_blocked_invalid_artifact`, reason `unsafe_artifact_file`. The later
`repair_reviewed_final_packet` shape classifier is therefore not reachable for
this input. The matrix row below is amended to the observed earlier fail-closed
contract before the harness expectation changes; all other cases passed.

Round 3 confirmed the amended terminal tuple but required one additional exact
absence predicate: the readiness-view descendant must be absent alongside the
hostile result. The same plan and harness predicate are visibly repaired.

Round 4 returned `VERDICT: AGREE` on plan SHA-256
`e946c9f44d8ae4107ae6f2f4f241f609efdd0d3c63ccfce3605f7316a0babd73`
and harness SHA-256
`32f8aed1144609c7b1f128b83e4dd40d37bdd143cd1445c8f7e66f18fc047da0`.

Audit disposition: `PASSED_AFTER_ROUND4_AGREEMENT`.
Execution resumes within the unchanged allowlist.

Post-run portability audit found a separate material artifact defect: cases
were built below a temporary `/tmp` staging root and copied after execution,
but canonical mission artifacts contain absolute paths. The copied repository
trees therefore retained references to a deleted staging root and are not
replayable persistent mission authority. This invalidates the Phase 10
artifact candidate, not the production implementation or the observed terminal
classifications.

The repair is to create the previously absent final validation root, build all
case trees directly below it, and publish `e2e_summary.json` last. A failed
partial root has no passing summary and is never promoted. The current invalid
candidate is preserved, not deleted, by renaming it to
`docs/validation/literature_survey_m16_phase10_2026-07-13_invalid_temp_paths/`
before the repaired run creates a fresh absent canonical root.

Round 5 agreed with this diagnosis but found two operational omissions. The
repair now includes exact guarded preservation commands, focused empty and
nonempty existing-root rejection tests, and a byte-oriented scan persisted in
`static_audit.json` before the summary is published.

The second focused portability review returned `VERDICT: AGREE` on plan
SHA-256 `f5befbb3fdd7cbc0fbcb60e5140d7041c08dfad5f90d3c165e37d9224d31a650`.

Audit disposition: `PORTABILITY_REPAIR_REVIEW_AGREED_EXECUTION_RESUMED`.

## Harness Architecture And System Boundary

Add one standalone artifact-producing harness:

- `scripts/literature_survey_m16_phase10_offline_e2e.py`.

Add its exact test module:

- `tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py`.

The harness may call in-process fixture setup helpers so it can inject a
deterministic public-metadata collection and a closed
`MissionSourceCapability`. It must use `research_assistant.cli.main()` for all
review imports and every tested safe-local resume/terminal transition. It must
not import helpers from test modules. Shared fixture constructors live in the
harness and are tested directly.

Before any provider-capable operation, install tripwires on:

- `research_assistant.survey.build._collect_public_metadata` after the one
  declared deterministic fixture collection;
- `urllib.request.urlopen` and the provider transport helpers;
- any source capability other than the closed fixture capability;
- model-worker/subprocess launch from the harness;
- writes outside the per-case temporary root and final validation root.

The persisted Phase 10 validation root is:

`docs/validation/literature_survey_m16_phase10_2026-07-13/`.

The harness creates the previously absent validation root, builds every case
directly below it so canonical absolute paths remain replayable, and writes
`e2e_summary.json` only after all case classifications finish. It must reject a
pre-existing output root and offers no `--force` mode. A partial root without a
passing summary is incomplete evidence and must be preserved under a visibly
labeled invalid-candidate name before a fresh absent root is used.

## Persistent Positive Mission

The positive case uses topic
`Neural Optimal Transport for generative modeling and inference` and seed
`arxiv:2201.12220v3`, with one deterministic V2 metadata record, one fixture
source record, no recorded reference/citation frontier, and zero unresolved
omission target.

Fixture setup must produce canonical mission-local metadata, source-intake,
anchors, public packet, selected artifact set, and review queue. Then the public
CLI imports:

- one V3 claim decision with an exact source dependency graph;
- one V3 source observation/decision set with recorded fixture-only status;
- the complete V2 omission decision set for the selected queue;
- the complete workflow-blocker decision set.

The first identical safe-local CLI command must return code `0` and:

- status `terminal_ready_for_reviewed_prose_within_recorded_scope`;
- action `terminal_ready_for_reviewed_prose`;
- reason `authoritative_hostile_result_is_clear_within_recorded_scope`;
- readiness classification `READY_FOR_REVIEWED_PROSE_WITHIN_RECORDED_SCOPE`;
- transitions exactly `merge_reviewed_evidence`,
  `compose_reviewed_final_packet`, `run_hostile_review`;
- current review/source/claim/omission selectors and selected artifact-set ID;
- authoritative merge, reviewed packet, hostile result, readiness view,
  mission-control, and selector bytes.

The second identical CLI command must return code `0`, the same terminal
status/action/classification, an empty transition history, the same selected
artifact-set and decision-set IDs, and byte-identical authoritative merge,
reviewed-packet, hostile-result, selectors, and external upstream roots. A
regenerable readiness view is checked separately and cannot override the hostile
result.

The positive record must say `fixture_only=true`,
`authenticated_human_review=false`, and list all forbidden nonclaims.

## Persistent Negative Mission Matrix

Every row records case ID, setup status, CLI argv, return code, exact observed
status/action/reason or blocked reason, authoritative bytes before/after,
forbidden descendant paths, tripwire counters, and evidence path.

| Case | Expected result | Forbidden descendants/actions |
| --- | --- | --- |
| `missing_public_confirmation` | `terminal_blocked_public_discovery_confirmation`; action `public_metadata`; reason `provider_metadata_is_not_a_phase5_local_action` | No metadata/source/queue/review/merge/packet/hostile artifact; zero provider call |
| `changed_topic_resume` | CLI return `1`, `blocked_reason=mission_identity_mismatch` | Current mission pointer unchanged; no descendant mutation |
| `changed_seed_resume` | CLI return `1`, `blocked_reason=mission_identity_mismatch` | Current mission pointer unchanged; no descendant mutation |
| `open_omission_review` | `terminal_blocked_reviewed_evidence`; action `resolve_reviewed_evidence_blockers`; reason `reviewed_evidence_has_open_outcomes` | Merge may exist blocked; no reviewed final packet, hostile result, or readiness |
| `missing_current_workflow_review` | `terminal_blocked_human_review`; action `import_reviewed_workflow_blockers`; reason `explicit_review_input_is_required` | No merge/packet/hostile descendants; other current families unchanged |
| `noncanonical_reviewed_claim_root` | `terminal_blocked_invalid_artifact`; action `terminal_blocked_invalid_artifact`; reason `noncanonical_safe_local_reviewed_claims_root` | No merge dispatch or descendants; external copied root unchanged |
| `malformed_reviewed_merge` | `terminal_blocked_invalid_artifact`; action `merge_reviewed_evidence`; reason `reviewed_evidence_shape_is_not_repairable` | No repair dispatch, packet, hostile result, or readiness |
| `symlinked_reviewed_packet` | `terminal_blocked_invalid_artifact`; action `terminal_blocked_invalid_artifact`; reason `unsafe_artifact_file` | No symlink following, hostile result, readiness view, or outside write |
| `upstream_packet_change` | New selected artifact-set/queue; prior decision bytes retained and reported `stale_lineage`; next action `import_reviewed_claims` | No stale merge/packet/hostile readiness |
| `legacy_v1_promotion` | Exact `legacy_evidence_authority` from merge, compose, and hostile attempts; the hostile attempt uses one declared synthetic canonical-path V1 reviewed-packet input | No generated merge or reviewed-packet output, hostile result, readiness, or prose-ready state; the declared synthetic V1 packet input is exempt and must remain byte-identical |

The harness must not weaken the public CLI to manufacture these codes. If an
exact observed code differs because the current implementation contract is
wrong, that is a failed case and repair trigger; the expected table is not
edited post hoc without a revised reviewed plan.

## Component Coverage Matrix

The following named tests are required catching evidence but are not labeled
persistent E2E missions:

- mission identity/current preservation:
  `test_cli_changed_topic_or_seed_blocks_without_changing_current`,
  `test_cli_existing_state_requires_resume_and_force_never_overwrites`;
- mission/genesis/generation crash and corrupt orphan matrices:
  `test_generation_two_crash_matrix_selects_valid_authority`,
  `test_genesis_atomic_write_crash_recovers_without_inventing_authority`,
  `test_corrupt_or_foreign_generation_two_orphan_blocks`;
- artifact-set/current crash matrices:
  `test_every_artifact_set_crash_boundary_allows_deterministic_retry`,
  `test_every_selector_crash_boundary_exposes_complete_set_and_retries`;
- source-intake crash, duplicate, tamper, symlink, cap and outside-write cases:
  all Phase 6 unit tests plus
  `test_confirmed_provider_write_outside_mission_root_blocks_before_call_or_commit`;
- supervisor partial/multifile and stage failure:
  `test_safe_local_partial_multifile_restart_is_terminal_invalid`,
  `test_partial_writer_exception_is_reobserved_as_invalid_artifact`;
- packet/hostile/readiness crash and legacy cases:
  `test_hostile_no_force_and_crash_preserve_authoritative_result`,
  `test_readiness_view_tamper_cannot_override_result_and_is_regenerated`,
  `test_safe_local_supervisor_reports_replay_valid_blocked_hostile_terminal`,
  `test_hostile_blockers_independently_veto_unsafe_snowball_policy_and_missing_claim_safety`,
  and both legacy V1 authority tests; the first hostile-terminal test injects
  `_hostile_blockers` and is therefore component catching evidence only;
- omission/frontier crash, quarantine, and schema closure:
  all Phase 8 unit tests;
- V3 authority crash, unavailable source, open quarantine, model-only,
  dependency, and merge publication ordering:
  all Phase 9 unit tests;
- public supervisor late-stage shape and missing-sidecar matrix:
  the CLI tests from `test_safe_local_supervisor_executes_merge_packet_hostile_and_terminal`
  through `test_direct_review_consumers_reject_selected_path_symlink_aliases_without_output`.

## Exact Implementation Scope And Allowlist

Before the harness runs, Phase 10 may add/edit only:

- `scripts/literature_survey_m16_phase10_offline_e2e.py`;
- `tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py`;
- this Phase 10 subplan and its review bundle/verdict;
- `docs/validation/literature_survey_m16_phase10_2026-07-13/**`;
- the preserved invalid candidate
  `docs/validation/literature_survey_m16_phase10_2026-07-13_invalid_temp_paths/**`;
- the Phase 10 result and final control-document reconciliation;
- the refreshed Phase 11 subplan and its read-only review records.

No production module or existing test is pre-authorized for edit in Phase 10.
If the new harness exposes a real product defect, patch this same subplan with
the exact production file/symbol and catching test, obtain a fresh read-only
plan agreement, and only then edit that path. Existing unrelated dirty arXiv
files and protected Phase 8/9 producer/transport files remain byte-gated.

## Required Artifacts

- `docs/validation/literature_survey_m16_phase10_2026-07-13/e2e_summary.json`;
- `positive/` with setup manifest, first/second CLI payloads, exact argv,
  mission tree inventory, selected IDs, authoritative hashes, and byte replay;
- `negative/<case-id>/` with setup manifest, CLI payload, exact expected versus
  observed classification, forbidden-descendant inventory, tripwire counters,
  and preserved pre/post hashes;
- `focused_harness.xml`, `phase8_unit.xml`, `phase9_unit.xml`,
  `phase3_through_phase10.xml`, `full_unit.xml`, `full_cli.xml`,
  `exact_scripts.xml`, and bounded logs;
- `phase8_ux_validation_result.json` in the Phase 10 root;
- `static_audit.json`, `run_manifest.json`, `change_manifest.json`, and
  `nul_safe_reconciliation.json`;
- `decision_table.json`, `inference_status.json`, and `post_run_red_team.json`;
- `docs/plans/literature_survey_m16_phase10_offline_e2e_result_2026-07-13.md`;
- compact Phase 10 implementation/evidence review packet and verdict;
- reconciled master, runbook, ledger, reset memo, and stop handoff;
- refreshed Phase 11 subplan with status
  `HUMAN_APPROVAL_REQUIRED_DO_NOT_EXECUTE` and its plan-review verdict.

## Exact Commands, Timeouts, And Logs

Every Python/test command sets `CUDA_VISIBLE_DEVICES=-1` before import. `timeout`
exit `124` is a hard veto for required gates. Commands write full output to the
named log; JUnit/JSON artifacts are authoritative.

```bash
test -d docs/validation/literature_survey_m16_phase10_2026-07-13
test ! -e docs/validation/literature_survey_m16_phase10_2026-07-13_invalid_temp_paths
mv docs/validation/literature_survey_m16_phase10_2026-07-13 \
  docs/validation/literature_survey_m16_phase10_2026-07-13_invalid_temp_paths
test ! -e docs/validation/literature_survey_m16_phase10_2026-07-13

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:src timeout 600 \
  python scripts/literature_survey_m16_phase10_offline_e2e.py \
  --out docs/validation/literature_survey_m16_phase10_2026-07-13 \
  > /tmp/literature_survey_m16_phase10_e2e_harness.log 2>&1

test -d docs/validation/literature_survey_m16_phase10_2026-07-13/logs
cp /tmp/literature_survey_m16_phase10_e2e_harness.log \
  docs/validation/literature_survey_m16_phase10_2026-07-13/logs/e2e_harness.log

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:src timeout 600 \
  pytest -q tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/focused_harness.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/focused_harness.log 2>&1

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src timeout 1200 \
  pytest -q tests/unit/test_literature_survey_m16_phase8.py \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/phase8_unit.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/phase8_unit.log 2>&1

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src timeout 1200 \
  pytest -q tests/unit/test_literature_survey_m16_phase9.py \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/phase9_unit.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/phase9_unit.log 2>&1

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:src timeout 1200 \
  pytest -q tests/unit/test_literature_survey_m16.py \
  tests/unit/test_literature_survey_m16_phase2.py \
  tests/unit/test_literature_survey_m16_phase3.py \
  tests/unit/test_literature_survey_m16_phase4.py \
  tests/unit/test_literature_survey_m16_phase5.py \
  tests/unit/test_literature_survey_m16_phase6.py \
  tests/unit/test_literature_survey_m16_phase7.py \
  tests/unit/test_literature_survey_m16_phase8.py \
  tests/unit/test_literature_survey_m16_phase9.py \
  tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/phase3_through_phase10.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/phase3_through_phase10.log 2>&1

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src timeout 1500 \
  pytest -q tests/unit \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/full_unit.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/full_unit.log 2>&1

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src timeout 1500 \
  pytest -q tests/integration/test_cli_commands.py \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/full_cli.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/full_cli.log 2>&1

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:src timeout 600 \
  pytest -q tests/scripts/test_literature_survey_phase5_command_validation.py \
  tests/scripts/test_literature_survey_phase6_boundary_validation.py \
  tests/scripts/test_literature_survey_phase7_validation_harness.py \
  tests/scripts/test_literature_survey_benchmark_feedback_summary.py \
  tests/scripts/test_literature_survey_m16_phase10_offline_e2e.py \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/exact_scripts.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/exact_scripts.log 2>&1

CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:src \
  RA_LITERATURE_SURVEY_PHASE8_VALIDATION_DIR=docs/validation/literature_survey_m16_phase10_2026-07-13 \
  timeout 600 \
  python scripts/literature_survey_phase8_ux_validation.py \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/phase8_ux.log 2>&1
```

The broader non-CLI integration diagnostic is bounded separately:

```bash
CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src timeout 1200 \
  pytest -q tests/integration --ignore=tests/integration/test_cli_commands.py \
  --junitxml=docs/validation/literature_survey_m16_phase10_2026-07-13/broader_non_cli_integration.xml \
  > docs/validation/literature_survey_m16_phase10_2026-07-13/logs/broader_non_cli_integration.log 2>&1
```

For this broader diagnostic only, exit `124` with no in-scope failure is
`INCOMPLETE_EVIDENCE`, not a pass and not automatically a Phase 10 continuation
veto. Any observed in-scope failure is a repair trigger. No result may say the
full integration suite passed unless this command exits `0` and the JUnit
parses with zero failures/errors.

Also run changed-module `py_compile`, every JSON/JUnit parse, writer-table
coverage, provider-transport AST identity, protected hashes, `git diff --check`,
NUL-safe Phase 0 reconciliation, and an exact scan proving no final canonical
artifact contains `/tmp/m16-phase10-`. No shell command may delete a prior
root; preserve the invalid candidate under its reviewed label and use a fresh
absent canonical Phase 10 output root.

## Required Checks And Pass Predicates

Phase 10 local gates pass only if:

1. `e2e_summary.json.status == "passed"` and its case IDs exactly equal the
   positive case plus all 10 declared persistent negatives.
2. The positive first/second run contract passes every exact terminal,
   transition, selected-ID, byte, selector, and tripwire predicate.
3. Every negative observes its intended stage and exact expected result; setup
   failures, earlier fail-closed codes, or generic exceptions do not count.
4. Every forbidden descendant/action count is zero for its case.
5. The focused harness test independently reads and validates the persisted
   summary/case evidence; it does not merely call `run_validation()` and trust
   an in-memory result. It also creates empty and nonempty pre-existing output
   roots and requires both to be rejected without mutation.
6. Required Phase 8/9, combined, full unit, CLI, exact scripts, UX, compile,
   parse, writer, AST, protected-hash, diff, and reconciliation gates pass.
7. All final hashes match the Phase 10 change manifest.
8. `static_audit.json` is written before `e2e_summary.json`, records a
   byte-oriented scan of every regular canonical output file, reports zero
   occurrences of `/tmp/m16-phase10-`, encodes the forbidden needle as hex so
   the audit record does not match its own predicate, and is independently
   checked by the focused test and a post-publication byte scan.
9. A fresh material read-only implementation/evidence review agrees on the
   frozen Phase 10 surface. Claude is preferred only if policy permits; the
   recorded export rejection is not retried or routed around. A fresh Codex
   reviewer is the downgraded fallback.
10. The Phase 11 plan is refreshed and independently reviewed but remains
   unexecuted.

## Phase-End Review And Repair Loop

After local gates:

1. Write the Phase 10 result/close record with decision table, inference-status
   table, exact commands, evidence roles, uncertainties, and nonclaims.
2. Freeze a compact implementation/evidence packet with exact hashes.
3. Obtain a read-only material review. A fixable `REVISE` patches the same
   allowlisted harness/test/result, reruns the smallest catching gate plus all
   affected broad gates, refreshes hashes, and repeats review.
4. Maximum five review rounds for the same material blocker. A fifth unresolved
   round writes a blocker result and requests human direction.
5. Refresh Phase 11, review it for consistency, correctness, feasibility,
   artifact coverage, evidence-role safety, exact live caps, and human boundary.
6. Reconcile master, runbook, ledger, reset memo, and handoff only after Phase
   10 implementation agreement and Phase 11 plan agreement.

## Forbidden Claims And Actions

- No live provider/network/public web/archive/source/PDF/full-text action.
- No real credential, private/paid database, model worker, model file, GPU,
  package install, or external subject trial.
- No staging, commit, push, reset, restore, stash, clean, destructive Git, or
  edit outside the reviewed allowlist.
- No synthetic review label represented as authenticated human review.
- No fixture source/status represented as source safety in fact.
- No metadata, citation count, abstract, availability, venue, or unreviewed text
  promoted to technical support.
- No open quarantine or unavailable source treated as ready.
- No failed setup treated as observing the intended negative veto.
- No broad-suite timeout called a pass.
- No Phase 10 success called clean-checkout or Git reproducibility.
- No local terminal called final prose quality, scientific correctness,
  literature completeness, product readiness, release readiness, or live
  reliability.
- No Phase 11 command is run under existing offline or review approvals.

## Exact Next-Phase Handoff Conditions

If every required gate and review converges, M16 local status becomes:

`PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`

The handoff must include:

- exact Phase 10 plan/result/review/change-manifest/run-manifest hashes;
- the persistent positive and negative summary;
- final test counts and any broader integration incomplete evidence;
- zero forbidden capability/action counts;
- unresolved nonclaims and the non-blocking classifier hardening note;
- a proposed Git integration manifest only, with no stage/commit;
- Phase 11 status `HUMAN_APPROVAL_REQUIRED_DO_NOT_EXECUTE`.

Phase 11 may begin only after a fresh user approval naming the exact topic,
seed, providers/domains, record/query/source/byte caps, retries, redirects,
timeouts, output root, and metadata-only versus source/PDF/full-text scope.
Claude or a read-only reviewer cannot grant this approval.

At phase end: run checks, write the close record, refresh/review Phase 11,
repair fixable findings, reconcile control artifacts, and stop at the Phase 11
human boundary rather than silently executing it.

## Stop Conditions

Stop, write a blocker result, and request direction only if:

- an inherited Phase 9 hash or authority cannot be validated;
- an unexplained overlapping user edit cannot be preserved;
- correct completion requires forbidden live/network/source/model/GPU/package/
  credential/private/paid/Git/human/scientific/product authority;
- the evidence distinction cannot be represented without weakening Phases 1-9;
- a required local environment failure repeats and no in-scope repair exists;
- the same material blocker fails five review rounds; or
- Phase 10 passes and Phase 11 lacks fresh exact human approval.

These are repair triggers, not stops: a negative fixture misses its intended
gate, the positive fixture fails, a catching test exposes a product defect, a
required suite fails for an in-scope defect, an artifact/hash mismatch is
repairable, or a read-only reviewer returns a fixable `REVISE`.

Before stopping, the result must answer whether the harness, implementation,
fixture, authority, or artifact is invalid, versus only the current candidate
failing. Continue through the planned repair whenever no continuation veto
fired.

## Implementation Review Repair Round 1

The first independent implementation review returned `VERDICT: REVISE`. This
is a fixable evidence/harness candidate failure, not a continuation veto. The
submitted candidate root must be preserved as
`docs/validation/literature_survey_m16_phase10_2026-07-13_rejected_review_round1/`
and excluded from promotion evidence and proposed Git integration.

Exact repairs:

1. The harness writes `e2e_static_audit.json` before publication, then a
   deterministic `e2e_artifact_inventory.json` that contains path, SHA-256, and
   byte size for every regular file in `positive/**`, `negative/**`, and the
   E2E audit. Its tree digest is canonical JSON over the sorted rows. The
   summary hashes the inventory and records its tree digest/count; the change
   manifest hashes both summary and inventory. Neither file self-hashes.
2. The focused test validates both a new temporary run and the frozen canonical
   root named by `RA_M16_PHASE10_CANONICAL_ROOT` or the reviewed default. It
   independently replays the inventory, every indexed case result, the exact
   terminal/CLI records, tripwire counters, mutation contracts, and audit.
3. The positive case snapshots selected artifact, claim-decision,
   source-observation, source-decision, and omission-decision IDs after the
   first run and after the second run. It requires equality, binds the artifact
   set to both CLI payloads, and requires the same exact status/action/reason/
   classification on replay with empty transition history.
4. Every negative snapshots the complete mission tree immediately before its
   measured CLI action and declares exact path prefixes that may change. The
   case fails if any changed path is outside that allowlist. Identity mismatch
   and each direct legacy promotion attempt require no mission-tree mutation;
   expected supervisor generations, artifact-set selection, or reviewed-merge
   output are allowlisted only in the cases that intentionally create them.
5. The write tripwire resolves the allowed root and candidate through existing
   symlink ancestors, rejects unknown path-like values, and has a focused test
   proving a lexical in-root symlink cannot write outside.

Because these changes alter persistent evidence and boundary instrumentation,
preserve the rejected root, construct a fresh absent canonical root, and rerun
all Phase 10 commands and audits. The implementation/evidence review bundle,
change manifest, result counts/hashes, and reconciliation must be regenerated
before implementation review round 2.

## Implementation Review Repair Round 2

Round 2 returned `REVISE` after confirming every direct and transitive hash.
The remaining findings are fixable and do not fire a continuation veto.

Exact repairs:

1. Frozen-candidate validation independently derives both exact terminal tuples
   and second empty history from `first_cli.json`/`second_cli.json`. It derives
   claim/source-observation/source-decision/omission IDs from canonical current
   pointer files and compares them with both persisted positive snapshots. It
   does not treat agreement among fields in `case_result.json` as evidence.
2. The legacy case snapshots the complete mission tree after its declared
   synthetic packet setup but before merge. That one snapshot spans merge,
   compose, and hostile CLIs; no mission mutation is permitted across any of
   them.
3. The inventory includes symlink rows with exactly `path`, `kind: symlink`, and
   lexical `target`. Regular rows include `kind: file`, SHA-256, and byte size.
   The focused test independently enumerates and replays both kinds; the
   symlinked reviewed-packet target cannot drift unnoticed.
4. Descriptor authorization stores descriptor plus `fstat` device/inode/mode,
   is removed on guarded close, and is invalidated on dup2 replacement. Guarded
   fdopen verifies current identity then consumes authorization. Direct
   `os.write` to any descriptor not currently authorized is rejected; dup and
   dup2 do not transfer write authorization. Catching tests recycle the integer
   through close/dup2 and require rejection.

Preserve the round-2 rejected candidate as diagnostic only, rebuild a fresh
canonical root, rerun every Phase 10 gate, refresh hashes/evidence, and submit
implementation review round 3.

The first round-3 UX invocation returned `127` because the validation-directory
assignment was incorrectly placed after `timeout`, causing `timeout` to treat
the assignment as an executable name. Preserve that diagnostic as
`logs/phase8_ux_invalid_env_order.log`; the corrected exact command above places
all environment assignments before `timeout`. This is a plan-command repair,
not product or UX evidence.

## Implementation Review Repair Round 3

Round 3 returned `REVISE` after independently confirming all 37 direct manifest
rows and all 1,137 current inventory rows. The three remaining findings are
focused catching-test gaps, not current evidence mismatches or production-code
defects:

1. derive claim, source-observation, source-decision, and omission IDs separately
   from each CLI record's selected `required_path` artifacts instead of checking
   only each CLI artifact-set ID and trusting positive summaries;
2. open `merge_cli.json`, `compose_cli.json`, and `hostile_cli.json` and derive
   each exact `blocked_reason` rather than trusting legacy `case_result.json`;
3. require `artifact_count == len(artifacts)` and exact row-path uniqueness so a
   duplicate inventory row cannot be collapsed by the path dictionary.

These are repair triggers under the existing evidence contract. Patch the same
focused validator, preserve the round-3 candidate as diagnostic only, rebuild a
fresh canonical root, rerun every Phase 10 gate, regenerate all hashes and
closeout records, and submit implementation review round 4. The five-round
same-blocker limit remains in force.

## Implementation Review Repair Round 4

Round 4 returned `REVISE` after independently confirming all direct hashes,
all 1,137 inventory rows, both CLI selector maps, and all 2,337 JUnit tests. Two
fixable issues remain for the fifth and final review round:

1. replace the stale prior-candidate tree digest in the human-readable result
   with the current candidate digest, then refresh it again from the fresh
   round-5 root before freezing hashes; and
2. require exactly three legacy summary rows, three unique evidence paths, three
   unique command IDs, and equality between every summary row and its opened CLI
   file for full argv, return code, command identity, and blocker reason before
   projecting the exact command/result map.

Preserve the round-4 candidate as diagnostic only, rebuild a fresh canonical
root, rerun every Phase 10 gate, regenerate every closeout hash, and submit
round 5. If round 5 finds the same material blocker unresolved, write a blocker
result and stop for human direction; do not invent a sixth round.
