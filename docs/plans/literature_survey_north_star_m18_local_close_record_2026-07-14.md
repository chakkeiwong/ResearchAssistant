# M18 Reproducible Git Integration Local Close Record

Date: `2026-07-14`
Status: `PASSED_LOCAL_GIT_INSTALL_REPRODUCIBILITY`
Milestone: `M18_reproducible_git_integration`
Closes: `G1_reproducible_git_integration`

## Close Decision

M18 passes its bounded engineering objective. Candidate commit
`654e6e1a1213bc03b7693ff1a8aea945a5bf08ac` is an identified,
single-parent, path-complete local-alpha integration that builds and installs
offline in the observed environment and passes the declared isolated local
gate matrix without relying on dirty RA source imports or absorbing protected
worktree changes.

The candidate contains `1,725` exact paths: `1,684` payload paths with digest
`0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318`,
`40` controls, and the stage record. Attempt 1 passed; no repair child was
created. Terminal evidence review converged in three rounds with final fresh
Codex read-only `VERDICT: AGREE`.

## Required Evidence

- Result:
  `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_result_2026-07-14.md`.
- Run/gate/trace/static/decision/inference/red-team records:
  `docs/validation/literature_survey_m18_2026-07-14/`.
- Row-level import provenance:
  `docs/validation/literature_survey_m18_2026-07-14/import_origin_inventory.json`.
- Row-level wheel/source provenance:
  `docs/validation/literature_survey_m18_2026-07-14/wheel_source_inventory.json`.
- Actual command/procedure ledger:
  `docs/validation/literature_survey_m18_2026-07-14/command_manifest.json`.
- Final terminal verdict:
  `docs/reviews/literature_survey_m18_terminal_review_verdict_round3_2026-07-14.md`.

## Handoff

M19 is the sole active planning lane. Its refreshed parent subplan is
`REFRESHED_PLANNING_ONLY_DO_NOT_EXECUTE_LIVE`. The exact next action is to
write and skeptically audit the dedicated M19 transport/supervisor-hardening
child subplan. No live request, transport implementation, source action, push,
or release is authorized by this close.

## Closeout Commit Nonclaim

This record is intended to be carried by the docs/evidence-only direct child
of candidate `654e6e1...`. A tracked file cannot contain the hash of the commit
that contains itself. The actual closeout hash and replay result are therefore
written only after commit to `/tmp/ra_m18_closeout_record.json`; no third
self-reference commit is created. The closeout replay must verify the direct
parent, candidate payload, installed origins, CLI help, and topic confirmation
stop before this operational handoff is reported complete.

## Nonclaims

M18 does not establish a bare-machine dependency wheelhouse, cross-platform
support, live provider behavior, citation recall, source/PDF/full-text access,
genuine human review, scientific correctness, literature completeness,
product/release readiness, or north-star completion.
