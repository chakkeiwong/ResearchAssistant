# M23 Terminal Fallback Review Round 2

Date: `2026-07-19`
Reviewer: fresh Codex read-only fallback
Surface: `_r6` compact terminal packet
Verdict: `REVISE`

## Material Finding

The derived replay from Round 1 was repaired, but three case predicates remained
weaker than the predeclared outcomes:

- command discovery did not validate package/version identity or the active
  boundary text in installed help output;
- unchanged resume did not prove valid generation ancestry, zero-transition
  resume, or unchanged gate/artifact state; and
- M22 replay did not expose the required forward-citation, 50-row, and 195-unit
  limitations.

The reviewer confirmed false passes after mutating the version payload and
resume state while `_validate_cases()` still returned passed cases.

## Required Repair

Strengthen those exact predicates, add focused false-pass tests, build a fresh
wheel/root, rerun the affected regression gate, and submit the new root to a
fresh terminal review.

`VERDICT: REVISE`
