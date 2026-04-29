# Release Audit Gap Closure Plan - 2026-04-29

## Motivation

`docs/proposal/release_audit_second_agent_review_request_2026-04-29.md`
requested an independent review of
`docs/plans/whole_codebase_release_audit_2026-04-29.md`. The audit correctly
identified release-engineering gaps that matter before final publication of the
current v0.1 individual local release.

The user request referenced
`release_audit_second_agent_review_request_2026-04-20.md`, but no file with
that date exists in this workspace. The matching available request is the
2026-04-29 file above.

## Current Release Scope

This plan stays within the existing v0.1 target:

- individual local research assistant;
- local filesystem storage;
- offline/provider-disabled defaults;
- Git-based sharing by repository exchange and explicit merge/import;
- no current shared backend, shared database, hosted UI, SSO/RBAC, or real-time
  collaboration;
- generated/parser/benchmark/derivation/readiness artifacts remain review
  material, not accepted scientific conclusions.

## Audit Verdict

The audit is substantially correct, with one current-state correction:

- The previous working-tree branch-hygiene concern was true at the audit time,
  but the NeuTra showcase work has since been committed. The current remaining
  untracked item is `.codex`, plus ignored build/cache artifacts.

Confirmed high-priority gaps:

1. `scripts/run_tests.sh` is not repo-portable.
2. `tests/integration/test_cli_commands.py` contains a hard-coded personal PDF
   path.
3. `docs/release_notes_0.1.0.md` has inconsistent release-date/build evidence
   wording.
4. Release checklist wording does not make clear that performance evidence
   must be present before `validation-report`/`gate-build`.
5. Broad release remains blocked by real external/manual validations and
   release-owner approvals.

## Phases

### Phase 0 - Baseline And Claim Verification

- Record the missing 2026-04-20 filename and the available 2026-04-29 files in
  the reset memo.
- Inspect the audit request, whole-codebase audit, scripts, tests, release
  notes, and release checklist.
- Run or inspect enough evidence to classify each audit claim as correct,
  stale, or expected manual gating.

### Phase 1 - Make The Full Test Script Portable

- Update `scripts/run_tests.sh` to:
  - derive `ROOT` from the script location;
  - export `PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"`;
  - use `timeout`;
  - run the intended unit and integration tests from the repo root.

### Phase 2 - Remove Personal PDF Dependency

- Replace the hard-coded Palazzo PDF path in
  `tests/integration/test_cli_commands.py`.
- Preserve the test intent: parser consensus should drive metadata and summary
  identity when remote metadata is unavailable or weak.
- Prefer a temporary PDF file plus monkeypatched extractor/parser functions
  over committing private PDFs.

### Phase 3 - Align Release Notes And Checklist

- Refresh `docs/release_notes_0.1.0.md` date/evidence wording for the current
  2026-04-29 candidate.
- Make the validation sequence explicit: performance evidence should be run
  before `validation-report` and `gate-build`.
- Keep manual blockers visible.

### Phase 4 - Validation And Audit

Run:

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_cli_commands.py tests/integration/test_industrial_platform_cli.py -q
timeout 180 scripts/run_tests.sh
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
timeout 120 scripts/run_fast_tests.sh
git diff --check
git status --short --ignored
```

If `scripts/run_tests.sh` proves too broad for a short release-audit pass, record
the exact result and run the narrower release-critical suites.

### Phase 5 - Commit And Final Memo

- Stage only intentional files.
- Force-stage ignored plan/reset memo files intentionally.
- Do not stage `.codex`, `.claude/`, caches, bytecode, `build/`, `dist/`,
  private papers, backup archives, or temporary workspaces.
- Commit the implementation.
- Update and commit the reset memo closeout.

## Acceptance Criteria

- The audit request has been converted into an executable gap-closure plan.
- The two concrete reproducibility blockers are fixed.
- Release notes/checklist evidence wording is current and unambiguous.
- Tests pass or any remaining failures are explicitly documented as external
  manual blockers.
- Broad release remains blocked until real external validations and
  release-owner approvals are recorded.
