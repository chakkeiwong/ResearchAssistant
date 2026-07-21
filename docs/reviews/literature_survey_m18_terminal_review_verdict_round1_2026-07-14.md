# M18 Terminal Review Verdict, Round 1

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer (`/root/m18_terminal_review`)
Status: `REVISE`

## Findings

1. High: the subplan requires an install/import/console-origin manifest, but
   the first compact evidence recorded only aggregate `49/49` import-origin
   and `89/89` wheel/source claims. It did not preserve module paths, resolved
   origins, wheel members, or per-file hashes for independent inspection.
2. Medium: the first run manifest omitted the exact commands actually run.
   This is material because the attempt included corrected selectors and
   harness-command repairs. JUnit binds test outcomes but not every venv,
   CPU-only, offline, or corrected audit invocation.

Candidate lineage/path counts, JUnit hashes and totals, protected-path
exclusion, targeted trace scope, claim boundaries, and M19's
`DO_NOT_EXECUTE_LIVE` controls otherwise checked out.

VERDICT: REVISE

## Repair Disposition

This is a fixable evidence-serialization/coverage defect, not a candidate,
test, target, or product defect. The focused repair adds a deterministic
generator plus per-module origin, per-wheel/source member, and exact command
manifests from the retained attempt-1 environment. It does not consume M18's
candidate attempt-2 budget or change the candidate commit.
