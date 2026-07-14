# Literature Survey North-Star Visible Stop And Handoff Record

Date: `2026-07-14`
Status: `M18_PASSED_M19_PLANNING_ONLY_DO_NOT_EXECUTE_LIVE`

## Current Position

M18 is complete as `PASSED_LOCAL_GIT_INSTALL_REPRODUCIBILITY`. Candidate
`654e6e1a1213bc03b7693ff1a8aea945a5bf08ac` passed the isolated local
engineering contract and terminal review. M19 is the sole active planning
milestone. No live M19 action is authorized.

## M18 Authority

- Candidate parent: `1b36af06efc7e1c2c086934cd8800691ae8a6da7`.
- Candidate paths: `1,725` (`1,684` payload + `40` controls + stage record).
- Payload digest:
  `0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318`.
- Wheel digest:
  `891e1e152d4d53fec3287b8209514b47383d9d2d85a02671b9e4358b343dcee2`.
- Result:
  `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_result_2026-07-14.md`.
- Close record:
  `docs/plans/literature_survey_north_star_m18_local_close_record_2026-07-14.md`.
- Terminal verdict:
  `docs/reviews/literature_survey_m18_terminal_review_verdict_round3_2026-07-14.md`,
  fresh Codex read-only `AGREE` after two focused evidence repairs.

The earlier `c378d271...` digest in pre-review planning notes is superseded by
the committed reviewed payload digest above.

## Validation

Authoritative attempt 1 passed payload replay, offline wheel installation,
all `49` import origins, all `89` source/wheel member pairs, focused/cumulative
M16-M17, persistent matrix, script, unit, CLI, arXiv compatibility,
SurveyBench, Phase 10 portability, candidate/static, trace, and protected-path
gates. All authoritative JUnit files have zero failures, errors, or skips.

Six protected dirty paths remain byte-identical and excluded. The worktree's
`src/research_assistant/cli.py` remains intentionally dirty relative to the
candidate because the candidate contains the reviewed four-line decoupling
while user bytes were preserved.

## M19 Boundary

The refreshed M19 parent is
`docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_subplan_2026-07-13.md`
with status `REFRESHED_PLANNING_ONLY_DO_NOT_EXECUTE_LIVE`.

Before any live request, M19 still requires:

1. a dedicated transport/supervisor-hardening child subplan;
2. skeptical audit and exact local no-network catching tests;
3. identified hardening code/test authority and exact route/cap manifest;
4. fresh read-only agreement on plan/code/approval packet; and
5. fresh user authorization for exactly one frozen live attempt.

## Exact Next Safe Action

Create the dedicated M19 transport/supervisor-hardening child subplan and run
its skeptical audit. Do not yet write transport code or call OpenAlex, arXiv,
DNS, proxies, source/PDF/full-text endpoints, or any other network service.

## Boundaries And Nonclaims

No push, release, destructive/history-rewriting action, live provider/source
access, credential, paid compute, privacy change, genuine human decision, or
scientific/product direction change is authorized. M18 does not establish
bare-machine/cross-platform dependency closure, live quality, source support,
scientific correctness, genuine human review, product/release readiness,
literature completeness, or north-star completion.

The actual docs/evidence closeout commit hash cannot be self-recorded in its
tracked contents. It is written after commit and replay only to
`/tmp/ra_m18_closeout_record.json`.
