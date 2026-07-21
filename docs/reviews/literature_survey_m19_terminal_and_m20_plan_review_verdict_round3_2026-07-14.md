# M19 Terminal Result And M20 Plan Review Verdict Round 3

Date: `2026-07-14`
Reviewer: fresh Codex read-only fallback
Verdict: `REVISE`

## Material Finding

The round-2 repair defined frontier outcomes by request, but the backward
frontier attempt is derived from `referenced_works` inside the direct-work
identity response. It therefore lacked a frontier-request row and was absent
from the identity by forward-query cross-product.

## Repair Applied

- Define one frontier outcome per frontier attempt with an exact origin request
  binding.
- Bind the backward attempt to the retained direct-work request/body and the
  forward attempt to the forward-query request/body.
- Add backward derivation outcomes for unavailable direct response, invalid
  backward parse, zero/within-cap/over-cap references, and nonselected direct
  identity.
- State that backward cap/failure does not overwrite identity; a backward
  boundary error remains a global veto.
- Require a canonical, exhaustively tested three-axis tuple over direct
  identity, backward attempt, and forward attempt, including rejected tuples
  and dispatch-veto states.

Focused checks and a fresh rereview are required.

`VERDICT: REVISE`
