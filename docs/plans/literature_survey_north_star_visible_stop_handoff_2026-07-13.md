# Literature Survey North-Star Visible Stop And Handoff Record

Date: `2026-07-14`
Status: `M17_PASSED_M18_PLAN_REVIEW_PENDING`

## Current Position

M17 is complete as `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`. M18 is
the sole active milestone. Its skeptical audit and disposable-clone dependency
preflight have passed after two visible repairs; its material plan review is the
next gate. The Git index remains empty and no M18 commit or authoritative
candidate attempt has run.

## Current Authority

- M17 result:
  `docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_result_2026-07-13.md`,
  SHA-256 `027cb69cbac7052d26acd5e3c64585b0f1d4549fa2832c7791502f9e6e9ff9bb`.
- M17 successor manifest:
  `docs/validation/literature_survey_m17_2026-07-13/successor_manifest.json`,
  file SHA-256 `46fd3d4e444fc5fd43b9d10f05dce110980c75bd13b98b345ae459a5b4277571`,
  payload SHA-256 `163f9ca026e18903d219690ed88647c1bc26ae7f45cd0752aa05a9cb891d485f`.
- M17 primary review:
  `docs/reviews/literature_survey_m17_terminal_implementation_review_verdict_2026-07-14.md`,
  Claude Opus/max `AGREE`.
- M17 closure review:
  `docs/reviews/literature_survey_m17_artifact_closure_repair_review_verdict_2026-07-14.md`,
  fresh Codex fallback `AGREE` after a policy-rejected second Claude export.
- M18 execution-ready subplan:
  `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_subplan_2026-07-13.md`.
- M18 payload:
  `docs/validation/literature_survey_m18_2026-07-14/payload_manifest.json`,
  `1,684` paths and payload SHA-256
  `c378d271ef8402e7980437b4e46ee25557872d30df0725cdace0fc25e0afd172`.
- Policy migration:
  `docs/plans/literature_survey_north_star_policy_migration_2026-07-14.md`.

## M18 Audit Findings And Repairs

1. M17's manifest omitted 13 canonical test inputs: three SurveyBench prompt
   files and the 10-file Phase 6 packet. They are now exact payload additions.
2. M17 inherited four optional arXiv plan-file CLI lines whose implementation
   exists only in excluded unrelated dirty `arxiv_batch.py`. The M18 candidate
   removes exactly those four lines in the index while preserving worktree
   bytes.
3. A host-installed older RA package could mask wheel defects. M18 force-installs
   the candidate wheel and asserts all RA origins lie under the attempt venv.
4. The one historical absolute symlink is preserved as negative evidence and
   may be inspected only with `lstat`/`readlink`; trace evidence must show no
   dereference.

Disposable-clone preflight passed compile/import/arXiv decoupling, `65` M17,
`22` SurveyBench, `8` CLI, and the full `11` exact script tests. These checks
are diagnostic preflight, not the authoritative identified-commit result.

## Protected Unrelated Work

The M18 plan freezes six excluded current hashes for `.gitignore`,
`docs/benchmark_plan.md`, the two arXiv implementation modules, and their two
focused test files. They must remain unchanged and absent from both M18 commits.
All unlisted diagnostic and historical roots remain excluded.

## Boundaries And Nonclaims

- M18 local staging/commit/clone/wheel/CPU-only work is authorized by the
  user's execute/resume request and current repository policy after material
  plan review.
- No push, public release, destructive/history-rewriting action, network,
  provider, source/PDF/full-text, credential, paid compute, privacy change,
  product/scientific direction change, or genuine human decision is authorized.
- M17/M18 evidence does not establish live quality, source support, scientific
  correctness, genuine human review, product/release readiness, literature
  completeness, or north-star completion.

## Exact Next Action

Create and submit the compact M18 material plan-review bundle. On `AGREE`, run
`prepare_integration.py stage`, verify the exact staged set and protected
exclusions, create the non-destructive candidate commit, and begin attempt 1 in
a fresh `/tmp` clone under the reviewed 120-minute/two-attempt budget. On a
material `REVISE`, patch the same subplan/helper visibly and rerun focused
preflight before staging.
