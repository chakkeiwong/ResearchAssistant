# M20B3 Code Review Verdict Round 3

Date: `2026-07-15`
Reviewer: fresh Codex read-only fallback
Verdict: `REVISE`

## Material Findings

1. `M20WorkerError` from installed artifact replay escaped the supervisor,
   preventing failure scrub and terminal manifest publication.
2. Cost replay did not close the producer status vocabulary and accepted an
   invented non-dispatch state.
3. The arXiv parser accepted `totalResults` smaller than the returned entry
   count while claiming a complete envelope.

## Resolution Status

The supervisor now catches replay errors as `worker_artifact_invalid`, scrubs
the fresh root, and publishes its terminal manifest. Cost evidence is closed to
the producer's exact four statuses with compatible credential, dispatch,
observed-cost, cost-state, error, and block-code combinations. Contradictory
arXiv totals are boundary-invalid. Focused regressions cover all three findings.

This verdict is advisory and does not authorize M20B4.

`VERDICT: REVISE`
