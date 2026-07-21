# M17 Terminal Implementation Read-Only Review Bundle

Status: `READY_FOR_REVIEW`

## Role Contract

Codex is supervisor and executor. Claude is a read-only reviewer only. Do not
edit files, run tests or experiments, launch agents, or change state. This
review cannot authorize Git, network, provider, source/PDF/full-text, human,
scientific-claim, product, release, or funding boundaries.

## Question

Does the M17 candidate correctly implement a topic-only mission without a
fabricated paper identity, enforce confirmation-before-call and at-most-once
fail-closed bootstrap authority across crashes/resume, preserve explicit-seed
V2 behavior, bind downstream use, and state only what its local evidence
supports?

## Scope

Review only these bounded symbols/ranges and the compact evidence summaries:

- `src/research_assistant/survey/mission_state.py:175-228` - V2/V3 fingerprint and common input view.
- `src/research_assistant/survey/mission_state.py:639-804` - input-mode dispatch and durable confirmation checkpoint.
- `src/research_assistant/survey/mission_state.py:1171-1540` - schema-family construction/validation and mission-control compatibility.
- `src/research_assistant/survey/bootstrap.py:34-211` - closed capability/outcome schemas.
- `src/research_assistant/survey/bootstrap.py:213-438` - safe store/history setup.
- `src/research_assistant/survey/bootstrap.py:442-820` - request, journal, result, prepare, select, and projection.
- `src/research_assistant/survey/bootstrap.py:821-976` - observe/validate/advance and indeterminate-call handling.
- `src/research_assistant/survey/orchestrate.py:129-234` - input-mode dispatch and fail-closed errors.
- `src/research_assistant/survey/orchestrate.py:304-561` - topic next action, authority projection, confirmation, and local downstream boundary.
- `src/research_assistant/survey/build.py:237-473` - bootstrap-bound local skeleton and replay validation.
- `src/research_assistant/survey/source_intake.py:907-1015` - topic bootstrap metadata-authority guard.
- `tests/unit/test_literature_survey_m17.py:174-875` - focused identity/outcome/crash/adversarial checks.
- `docs/validation/literature_survey_m17_2026-07-13/static_audit.json` - static/boundary summary.
- `docs/validation/literature_survey_m17_2026-07-13/decision_table.json` - decision/nonclaims.
- `docs/validation/literature_survey_m17_2026-07-13/post_run_red_team.json` - residual risks.
- `docs/validation/literature_survey_m17_2026-07-13/successor_manifest_replay.json` - exact replay status.
- `docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_result_2026-07-13.md` - candidate result.

Out of scope: live provider quality, paper/source content, scientific claims,
the entire repository, old rejected/diagnostic validation roots, and M18-M23
execution.

## Changed Surface

- Omitted CLI `--seed` selects topic input; explicit empty seed remains invalid.
- Topic input has sibling fingerprint/GENESIS/contract/control/public-result
  schemas; explicit-seed V2 persists unchanged.
- Selected candidates are derived authority, never original mission inputs.
- Bootstrap journal lifecycle is `intent -> call_started -> result_recorded ->
  prepared -> selected`; durable indeterminate calls never retry ordinarily.
- Prepared evidence exposes no effective seeds/authority. Valid pointer plus
  selected/reconciled journal is required.
- Default CLI topic execution records `unavailable` and does not call inherited
  provider code. Selected local fixtures may build only a bound skeleton.

## Evidence

| Gate | Exit | Key output | Artifact |
| --- | ---: | --- | --- |
| Focused M17 | 0 | 65 passed; 38 crash points | `docs/validation/literature_survey_m17_2026-07-13/focused_final_schema_round2.xml` |
| Cumulative M16+M17 | 0 | 846 passed | `docs/validation/literature_survey_m17_2026-07-13/cumulative_m16_m17_unit_round1.xml` |
| Persistent matrix | 0 | 13/13 passed | `docs/validation/literature_survey_m17_2026-07-13/persistent_matrix_final2/summary.json` |
| Full unit retry | 0 | 1,050 passed | `docs/validation/literature_survey_m17_2026-07-13/full_unit_retry_after_vscode_crash.xml` |
| Full CLI retry | 0 | 125 passed | `docs/validation/literature_survey_m17_2026-07-13/full_cli_retry_after_vscode_crash.xml` |
| Exact scripts and affected integration | 0 | 11 + 20 passed | `docs/validation/literature_survey_m17_2026-07-13/exact_scripts_final.xml`; `docs/validation/literature_survey_m17_2026-07-13/affected_non_cli_integration_final.xml` |
| Static/manifest replay | 0 | 502 rows, zero mismatch | `docs/validation/literature_survey_m17_2026-07-13/static_audit.json` |

Run context: commit baseline
`1b36af06efc7e1c2c086934cd8800691ae8a6da7`, dirty worktree preserved,
Python 3.11.14, pytest 9.0.2, CPU-only with `CUDA_VISIBLE_DEVICES=-1`, no
network/source/model/Git mutation. The immutable M16 snapshot replayed 38 direct
rows and the exact 1,137-row scoped inventory.

## Pass And Block Criteria

Pass only if no material flaw remains in:

- separation of original topic identity from effective paper authority;
- schema-family dispatch and V2 compatibility;
- durable confirmation ordering;
- at-most-once call knowledge and indeterminate-call blocking;
- result/set/pointer/journal crash recovery and authority exposure;
- stale, corrupt, foreign, symlink/nonregular, or partial evidence rejection;
- downstream skeleton/source-intake authority binding;
- successor-manifest/evidence honesty; or
- forbidden live/scientific/product claims.

Return `REVISE` for a concrete material correctness, regression, boundary,
artifact, or unsupported-claim issue. Do not block for legacy procedural
ceremony retired by the current academic-governance policy.

## Known Limitations

- M17 uses deterministic local capabilities; no production bootstrap adapter
  exists.
- At-most-once handling blocks an uncertain external call rather than claiming
  exactly-once execution.
- The worktree remains dirty and partly untracked; M18 must prove isolated Git
  reproducibility.
- The initial final full-unit/CLI attempts were interrupted by the editor crash;
  fresh complete retry JUnits are authoritative.

## Requested Verdict

Provide findings first, ordered by severity, with exact file/line anchors. End
with exactly one line:

```text
VERDICT: AGREE
```

or

```text
VERDICT: REVISE
```

