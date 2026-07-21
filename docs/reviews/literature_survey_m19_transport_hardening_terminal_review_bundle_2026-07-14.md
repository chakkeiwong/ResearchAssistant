# M19A Terminal Implementation And Result Rereview Bundle

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer
Authority: advisory only

## Review Question

Return `AGREE` only if the repaired M19A commit and superseding evidence support
the narrow claim that the future four-request live metadata attempt is locally
closed and eligible to proceed to an exact human approval request. Return
`REVISE` with concrete file/line findings for any material defect.

The reviewer cannot authorize live access, source retrieval, M20, human-review
claims, scientific claims, product readiness, release, or funding.

## Inspect

- the three-file repair diff `945332f..bb4300c` and current committed code;
- `src/research_assistant/survey/build.py` at `bb4300c`;
- `scripts/literature_survey_m19_live_metadata_supervisor.py` at `bb4300c`;
- both M19 tests at `bb4300c`;
- `docs/plans/literature_survey_north_star_m19_metadata_transport_hardening_subplan_2026-07-14.md`;
- `docs/plans/literature_survey_north_star_m19_metadata_transport_hardening_result_2026-07-14.md`;
- the refreshed M19 parent and draft approval packet;
- the seven top-level JSON records in the round-3 validation root;
- the five JUnit/log pairs and `fake_run/` summary/ledger/inventory; and
- isolated installed-wheel hash and exact commands recorded in `run_manifest.json`.

## Required Checks

1. Confirm the round-1 parser-fallback finding is fixed and caught at both
   transport and worker levels; then look for another route/proxy/redirect/retry/byte/time/process/IPC/write escape or a
   boundary failure that can collapse into provider `unavailable`.
2. Check that request, worker, ledger, and manifest validation fail closed and
   that passing publication is manifest-last and race-safe.
3. Check JUnit counts/hashes, fake-run replay claims, commit lineage, protected
   hashes, exact-root grammar, and isolated-wheel claims for consistency.
4. Distinguish the two failed harness attempts from product failures without
   excusing a real defect.
5. Check that the result and parent avoid provider/source/scientific/product or
   north-star claims.
6. Check that the draft packet cannot be mistaken for live authority and that
   no command is frozen before the post-review closeout commit exists.

## Known Limitations To Classify

- The original evidence root is rejected by round-1 terminal review and round
  2 is an import-harness failure; only round 3 is current evidence.
- No packet capture or real provider access occurred by design.
- The current shell has no installed package with `PYTHONPATH` unset; all five
  round-3 gates ran from the isolated force-reinstalled wheel.
- Pytest scratch contains intentional malformed and symlink negative fixtures
  and is opaque retained gate output under the reviewed root grammar.

## Expected Verdict Format

List material findings first with file/line references. Then state exactly one
of:

- `VERDICT: AGREE`
- `VERDICT: REVISE`
