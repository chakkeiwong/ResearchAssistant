# Release Audit Second-Agent Review And Execution Plan - 2026-04-29

## Status

This document supersedes the original second-agent review request. The original
request asked for a read-only review of
`docs/plans/whole_codebase_release_audit_2026-04-29.md`; the current release
task requires executing the verified audit findings.

The user referred to
`release_audit_second_agent_review_request_2026-04-20.md`, but no file with
that date exists in this repository. The available matching request is this
2026-04-29 document.

## Release Scope

The review and execution target is the bounded v0.1 individual release:

- individual local research assistant;
- local filesystem storage;
- offline/provider-disabled default workflows;
- Git-based sharing by repository exchange and explicit merge/import;
- no current shared backend, shared database, hosted UI, SSO/RBAC, or real-time
  collaboration;
- generated/parser/benchmark/derivation/readiness artifacts remain review
  material, not accepted scientific conclusions.

## Second-Agent Audit Verdict

The whole-codebase audit is substantially correct. The strongest findings are
real release-engineering issues, not taste or broad future-platform concerns.

Confirmed findings:

1. `scripts/run_tests.sh` was not portable because it used a hard-coded
   maintainer-local path and did not export `PYTHONPATH=src`.
2. `tests/integration/test_cli_commands.py` used a hard-coded personal Palazzo
   PDF path outside the repository.
3. `docs/release_notes_0.1.0.md` mixed a 2026-04-28 document date with
   2026-04-29 artifact evidence.
4. `docs/release_checklist.md` and release notes could better explain that
   representative workspace performance evidence must be recorded before
   `validation-report` and `gate-build`.
5. Broad release remains blocked by real fresh-reader onboarding, real macOS
   validation, real minimal-parser-tool validation, tag approval, and
   publication approval.

Current-state correction:

- The audit's branch-hygiene warning was true when the audit was written, but
  the intervening NeuTra/DSGE showcase work has since been committed. The
  remaining local state is `.codex` untracked plus ignored build/cache outputs.

## Executable Plan

The executable plan is tracked in:

- `docs/plans/release_audit_gap_closure_plan_2026-04-29.md`

Implementation phases:

1. Verify audit claims against current files.
2. Make `scripts/run_tests.sh` repo-portable and bounded.
3. Replace the personal PDF dependency with a deterministic temporary fixture
   and monkeypatched parser/extractor outputs.
4. Align release notes and checklist evidence wording.
5. Run affected integration tests, full test script, individual release tests,
   fast tests, and diff hygiene.
6. Commit intentional files only and update the reset memo.

## Expected Remaining Blockers

Do not mark the following as passed unless real evidence is collected:

- real fresh-reader onboarding;
- real macOS validation;
- real minimal parser-tool machine validation;
- release-owner tag approval;
- release-owner artifact publication approval.

These are expected blockers for broad publication, not code bugs.
