# Final Maintainability Refactoring Result - 2026-07-20

## Decision

`READY_FOR_RELEASE_CANDIDATE_REVIEW`

The maintainability plan survived skeptical audit and was executed without
changing the Python 3.11-only contract, parser schema, CLI output/exit-code
surface, arXiv-only defaults, protected survey output checks, or mission
durability semantics.

## Changes

- Split survey and SurveyBench action execution into named handlers with
  immutable dispatch maps in `src/research_assistant/cli_actions/`.
- Kept `cmd_survey()` and `cmd_surveybench()` as small service-injecting facades
  in `src/research_assistant/cli.py`.
- Extracted pure next-action construction into
  `src/research_assistant/survey/next_action.py`, including explicit helpers for
  gate handling, review progression, blocker repair, and final packet/hostile
  review progression.
- Kept mutable stage dispatch, supervisor orchestration, and mission durability
  in their existing modules.
- Updated `docs/maintainer_guide.md` and `scripts/run_static_checks.sh` with the
  ownership and type-check boundaries.
- Added direct dispatch, immutability, review-order, command-byte, and final
  progression characterization tests.

## Verification

| Check | Result |
| --- | --- |
| Focused architecture/action/next-action/Phase 5-8 suite | `291 passed, 73 skipped` |
| Full release test inventory | `1717 passed, 229 skipped` across four isolated partitions |
| Release gate commands | All 8 returned zero |
| Python | `3.11.14` |
| Source fingerprint | `9ea1e58b127958d35aaf95e9b1c0c77d92f83809672ccf3de8c7e87a86c70a14` |
| Evidence validation | Passed, no issues |
| Disposable workspace release report | `ready_for_release_candidate_review`, zero blockers/warnings |
| Ruff/mypy | Not installed locally; configured CI checks remain required |

The full gate was CPU-only with `CUDA_VISIBLE_DEVICES=-1`. The release evidence
does not claim scientific correctness, literature completeness, cross-platform
support, hosted deployment readiness, or full PDF extraction quality.

The active test wrapper was hardened after the host repeatedly terminated the
monolithic pytest process at about 1,026 seconds with exit 143. The replacement
uses four `setsid`-isolated partitions and preserves the complete test inventory;
the partitioned run passed without termination or failure.

## Maintenance Boundary

The next high-risk refactor candidates are the mutable stage executor in
`survey/orchestrate.py` and `MissionStateManager`. They were deliberately not
moved because their replay, crash-recovery, lock, orphan, tamper, and canonical
artifact invariants need a separate characterization plan. The current release
does not depend on that movement.
