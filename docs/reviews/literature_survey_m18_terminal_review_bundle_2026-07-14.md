# M18 Terminal Review Bundle

Date: `2026-07-14`
Reviewer role: read-only; passive inspection only
Requested output: findings ordered by severity, then `VERDICT: AGREE` or
`VERDICT: REVISE`

## Review Question

Do the M18 result/evidence support only the claimed local Git/install
reproducibility conclusion, and is refreshed M19 consistent, feasible,
artifact-complete, and fail-closed at the live boundary?

## Exact Material Surface

- Candidate commit: `654e6e1a1213bc03b7693ff1a8aea945a5bf08ac`
- Candidate parent: `1b36af06efc7e1c2c086934cd8800691ae8a6da7`
- Reviewed M18 subplan:
  `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_subplan_2026-07-13.md`
- Draft M18 result:
  `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_result_2026-07-14.md`
- Refreshed M19:
  `docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_subplan_2026-07-13.md`
- Compact evidence:
  `docs/validation/literature_survey_m18_2026-07-14/run_manifest.json`,
  `gate_summary.json`, `trace_summary.json`, `static_audit.json`,
  `decision_table.json`, `inference_status.json`, and
  `post_run_red_team.json` in the same directory.
- Existing payload/stage authority:
  `payload_manifest.json`, `stage_record.json`, and
  `prepare_integration.py` in the same directory.
- Round-1 finding and focused repair:
  `docs/reviews/literature_survey_m18_terminal_review_verdict_round1_2026-07-14.md`,
  `generate_inventory.py`, `import_origin_inventory.json`,
  `wheel_source_inventory.json`, and `command_manifest.json` under the M18
  validation root.

## Frozen Facts To Verify

- Candidate is an exact single-parent child and has `1,725` changed paths.
- Payload is `1,684` paths with digest
  `0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318`.
- Attempt 1 passed every declared gate; no repair child exists.
- Eight authoritative JUnit records total `2,137` executed testcases with
  overlap and have zero failures/errors/skips.
- The zero-test selector artifact is diagnostic-only and not promoted.
- All 49 imports resolve under the attempt venv; wheel/source coverage is
  `89/89`. The focused repair must expose every row and byte hash rather than
  only aggregates.
- Six protected dirty paths stayed byte-identical and are excluded.
- Targeted traces contain no dirty checkout path and no
  `socket`/`connect`/`sendto`; no universal claim is made for untraced suites.
- No live/provider/source/GPU/push/release/destructive action occurred.
- M19 explicitly remains `DO_NOT_EXECUTE_LIVE` and requires a dedicated child
  hardening plan, exact route/cap manifest, review, and fresh approval.

## Projected Close Transition

On `AGREE`, Codex will:

1. write the M18 close record and mark G1/M18 complete in milestone/master,
   ledger, runbook, handoff, and reset memo;
2. set M19 as the sole planning-only active lane while keeping live execution
   forbidden;
3. exact-stage only result/evidence/review/M19/program-control files;
4. require the candidate-to-closeout diff to contain no product/test/source or
   protected path;
5. commit `Document reproducible literature survey integration` without amend
   or push; and
6. fresh-clone that closeout commit, verify its single-parent relationship to
   the candidate, replay the candidate payload, install the candidate wheel,
   and rerun CLI help/topic smoke. The actual closeout hash will be written
   only to `/tmp/ra_m18_closeout_record.json`.

## Reviewer Constraints

Do not run tests, Python, helper scripts, Git mutation, network, source, GPU,
or external-model actions. Read files and inspect Git objects only. The review
cannot authorize live M19 action, push, release, human decisions, scientific
claims, or product capability.

Return `REVISE` only for a material correctness, evidence, feasibility,
artifact-coverage, or boundary-safety defect. Purely stylistic or superseded
legacy-governance issues are nonblocking.
