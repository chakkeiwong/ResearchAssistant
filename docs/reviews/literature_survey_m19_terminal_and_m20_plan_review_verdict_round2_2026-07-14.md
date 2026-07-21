# M19 Terminal Result And M20 Plan Review Verdict Round 2

Date: `2026-07-14`
Reviewer: fresh Codex read-only fallback
Verdict: `REVISE`

## Material Finding

The repaired outcome contract still used one case-outcome precedence table for
both direct identity/bootstrap and frontier observations. A capped, empty, or
unavailable forward query could conflict with the intended selected direct
identity; forward citing rows could also be misread as identity candidates
when the direct-work request was unavailable.

## Repair Applied

- Split the result into `identity_outcome` and one row per
  `frontier_outcome`.
- Scope identity and frontier caps to their respective roles.
- State that forward rows never enter the direct-identity candidate set.
- Add separate identity/bootstrap and per-frontier automata.
- Add the direct-work identity by forward-query cross-product, including global
  boundary vetoes and navigation-only behavior for every nonselected direct
  identity state.
- Require the future canonical machine artifact to expand all summarized
  cross-product rows and exhaustively test them before packet freeze.

Focused checks and a fresh rereview are required.

`VERDICT: REVISE`
