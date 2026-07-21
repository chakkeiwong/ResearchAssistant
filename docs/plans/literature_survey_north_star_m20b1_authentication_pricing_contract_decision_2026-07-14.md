# M20B1 OpenAlex Authentication And Pricing Contract Decision

Date: `2026-07-14`
Status: `SUPPORTED_BY_RETAINED_OFFICIAL_DOCUMENTATION`

## Evidence Boundary

This decision uses only the two official UTF-8 HTML bodies retained by the
single consumed M20B1 documentation attempt. No provider API route, credential,
account, billing state, source, PDF, or full text was accessed.

| Official body | SHA-256 | Relevant anchors |
| --- | --- | --- |
| Authentication and pricing | `5818a17a17b6391b5407412d51f24c75d880f1547afbc584af1578450d1bdb6a` | `Getting an API Key`, `Pricing by Endpoint`, `Keeping Tabs on Costs`, `Exceeding Limits` |
| Rate-limit operation | `25116016401635f2235063549ffc88f360a0b4e2644449f82596465280592219` | `GET /rate-limit`, required query `api_key`, current USD fields, deprecated credit fields |

## Supported Contract

1. A free key is obtained through an OpenAlex account at
   `https://openalex.org/settings/api`. The documented API interface supplies
   it as the `api_key` query parameter. This establishes provider syntax; it
   does not establish that this repository has a key or authority to use one.
2. The current pricing table states these costs per 1,000 calls: singleton
   lookup `Free`, list/filter `$0.10`, keyword search `$1`, semantic search
   `$1`, and content download `$10`.
3. The frozen M20 matrix plans three OpenAlex calls: one keyword-search call
   (`$0.001`), one singleton call (`$0`), and one list/filter call (`$0.0001`).
   The documented planned total is therefore `$0.0011`. This is a pre-run
   bound, not evidence of actual billing.
4. The page states a `$0.10/day` allowance without a key and a `$1/day`
   allowance with a free key. A prepaid balance is separate and may be used
   after the daily allowance. Therefore "inside the free allowance" is not the
   same claim as zero usage cost, and M20 must account for usage in USD whether
   it is covered by daily allowance or prepaid funds.
5. List responses expose `meta.cost_usd`. The official page also names
   `X-RateLimit-Credits-Used` as the request cost and documents a keyed
   `/rate-limit` response with `daily_budget_usd`, `daily_used_usd`,
   `daily_remaining_usd`, `prepaid_balance_usd`,
   `prepaid_remaining_usd`, reset fields, and `endpoint_costs_usd`.
6. `credits_limit`, `credits_used`, `credits_remaining`, and `credit_costs` in
   the rate-limit schema are explicitly deprecated in favor of the USD fields.
   M20 must not build new authority on the deprecated fields.
7. The documented global rate is at most `100` requests per second; exceeding
   that or the daily limit produces HTTP `429`. The five-request M20 matrix has
   only three OpenAlex calls and does not need concurrency.

## Unknowns And Conservative Decisions

- No key availability, owner, approved campaign use, runtime source, rotation,
  or revocation fact was checked. Those remain human decisions.
- No account's actual daily or prepaid balance was checked. No claim of free
  execution or zero financial impact is supported.
- The pricing page's semantic-search table (`$1/1,000`) and one illustrative
  rate-limit payload (`semantic: 0.01`) are inconsistent. M20 does not use a
  semantic route. Any future semantic request must stop for a refreshed
  contract rather than choosing one value.
- Generated example values such as `123` and example timestamps are schema
  illustrations, not actual account or pricing evidence.
- M20B2 should use current USD fields and `meta.cost_usd` where the planned
  response schema provides it. Unknown, non-finite, negative, contradictory,
  or over-budget cost is a hard stop, never zero.

## Recommended Human Decisions

These are recommendations, not selected authority:

- runtime interface: exact named environment variable `OPENALEX_API_KEY`, read
  only inside the trusted worker after descriptor and budget validation;
- privacy: approve the enumerated M20B0 no-persistence and pre-format redaction
  requirements, tested with a unique synthetic canary and limited to the named
  tested surfaces;
- cost: maximum total M20 live-campaign usage cost `$0.01`, including usage
  covered by a daily allowance or prepaid balance; route-cost unknown or
  contradiction stops before dispatch, and unreconciled post-response cost
  stops subsequent dispatch.

These decisions do not authorize a provider API call. M20B4 still requires an
identified key owner/controller, permission for the exact campaign, a reviewed
M20B3 packet, and explicit human authorization for its single live attempt.
