# M20B3 Code Review Verdict Round 4

Date: `2026-07-15`
Reviewer: fresh Codex read-only fallback
Verdict: `REVISE`

## Material Findings

1. Cost replay did not bind every producer status/error to its exact credential,
   observed-cost, cost-state, and block-code outcome.
2. A non-completed OpenAlex request row's error code was not required to equal
   its cost evidence error code.

## Resolution Status

The producer's four evidence statuses now have explicit compatible state
tuples. Credential lookup failures remain open with no block code;
post-credential state failures are blocked with matching error/block codes;
post-dispatch failures follow an explicit error-to-block map. Non-completed
request-row causes must equal cost-evidence causes. Positive invalid-credential
replay and adversarial mismatch tests pass.

This verdict is advisory and does not authorize M20B4.

`VERDICT: REVISE`
