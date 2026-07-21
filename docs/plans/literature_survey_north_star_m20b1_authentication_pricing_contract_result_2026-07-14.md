# M20B1 Authentication/Pricing Documentation Result

Date: `2026-07-14`
Status: `PASSED_DOCUMENTATION_CONTRACT_HUMAN_DECISIONS_REQUIRED`
Milestone: `M20_live_discovery_and_citation_frontier`

## Result

The single reviewed M20B1 documentation attempt is complete and consumed. It
retained exactly two official OpenAlex documentation pages as HTTP `200`,
UTF-8 HTML with no redirects, retries, credentials, provider API calls, or
overflow. Accepted bytes were `867,402/4,000,000`; both transaction slots are
consumed and no rerun is permitted.

| Artifact | SHA-256 |
| --- | --- |
| Authentication/pricing HTML | `5818a17a17b6391b5407412d51f24c75d880f1547afbc584af1578450d1bdb6a` |
| Rate-limit HTML | `25116016401635f2235063549ffc88f360a0b4e2644449f82596465280592219` |
| Fetch manifest | `f82120e4c462cfe88ecc36fcdef87ac92d75f93c7761e687610f4779a38289d9` |
| Campaign manifest | `24710e8b97dd6defeafd5d3ed305e89f0bbec7e77710b45ad6dcf36184b99990` |
| Supervisor manifest | `ff35ef3f7b6881b4aab88e498c5516c9ba5776c746aef56cde4a4016ca49fe84` |

The worker exited `0`, was confirmed reaped, and closed in `3.898030` seconds.
Exact artifact replay took `0.002095` seconds. The final supervisor
classification is `completed`.

## Contract Finding

Official retained bytes establish a query-parameter `api_key`, a `$1/day`
keyed daily allowance, current USD endpoint pricing, `meta.cost_usd`, current
rate-limit USD fields, midnight-UTC reset semantics, and a `100` requests per
second ceiling. Planned OpenAlex usage for the frozen M20 matrix is `$0.0011`:
one keyword search `$0.001`, one free singleton, and one list/filter `$0.0001`.
Deprecated `credits_*` fields are not suitable for new cost authority.

The source-anchored decision is:
`docs/plans/literature_survey_north_star_m20b1_authentication_pricing_contract_decision_2026-07-14.md`.

## Decision Table

| Decision | Primary criterion status | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Pass M20B1 and stop at the M20B2 human gate | Both exact pages and manifests closed and the official contract answers authentication/pricing/rate-limit questions | No M20B1 acquisition veto fired | Authorized key interface, approved privacy handling, and numeric human budget are unselected | Obtain the three explicit human decisions, then execute only synthetic-canary M20B2 local engineering | Key availability/use, account balance, free execution, provider readiness, M20 completion, M21 authority, or north-star completion |

## Engineering, Numerical, And Interpretation Ledgers

- Engineering: exact target, body, manifest, byte, transaction, lifecycle, and
  inventory closure passed.
- Numerical: pricing arithmetic is a direct documented schedule calculation,
  not a stochastic estimate. Actual billed/allowance usage was not observed.
- Interpretation: the pages establish provider contract semantics only. They
  do not authorize or validate an authenticated provider call.

## Post-Run Red Team

The strongest alternative explanation is documentation drift between this
snapshot and a later M20B4 run. M20B3 must bind this dated contract and stop if
live response cost fields contradict it. A changed official pricing schedule,
unmapped route, or contradictory `cost_usd` would overturn the cost bound. The
weakest evidence is account-specific allowance/prepaid state, which was
deliberately not inspected and remains outside M20B1.

## Handoff

Next subplan:
`docs/plans/literature_survey_north_star_m20b2_synthetic_credential_redaction_cost_controls_subplan_2026-07-14.md`.

M20B2 is non-executable until the human selects an authorized key interface,
approves the privacy/redaction requirements, and sets a numeric maximum total
campaign cost. No secret value should be sent or recorded. Credentials,
provider APIs, M20B3+, source/PDF/full-text, push, and release remain forbidden.
