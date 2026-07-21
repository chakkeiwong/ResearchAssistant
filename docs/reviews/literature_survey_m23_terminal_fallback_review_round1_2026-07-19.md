# M23 Terminal Fallback Review Round 1

Date: `2026-07-19`
Reviewer: fresh Codex read-only fallback
Surface: authoritative-at-the-time `_r5` compact terminal packet
Verdict: `REVISE`

## Material Finding

The `_r5` wheel embedded the older `replay_acceptance()` implementation, which
verified command-output hashes but trusted stored parsed JSON, aggregate case
pass projections, and the terminal pass projection. The stronger replay code
was added only after `_r5`, so that root could not satisfy the claimed exact
installed-process replay contract.

## Required Repair

Build a fresh wheel/root after replay reparses captured stdout, verifies exact
command identity and environment, reruns all nine predicates, compares exact
case and terminal projections, recomputes documentation/capabilities, and
rejects rehashed projection tampering. Rerun focused tests and the affected
regression gate before a fresh terminal review.

`VERDICT: REVISE`
