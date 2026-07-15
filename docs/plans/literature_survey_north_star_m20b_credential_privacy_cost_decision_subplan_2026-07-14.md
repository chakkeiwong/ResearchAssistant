# M20B0 Credential, Privacy, And Cost Decision-Setup Subplan

Date: `2026-07-14`
Status: `M20B0_CLOSED_SUCCESSORS_M20B1_M20B2_PASSED_M20B3_GIT_AUTHORITY_REQUIRED`
Milestone: `M20_live_discovery_and_citation_frontier`

## Phase Objective

Define the smallest proportionate decision surface and phase sequence needed to
turn the passed M20A descriptor/parser surface into a future bounded M20B live
proposal. Produce only non-executable plans, decision requests, and boundary
requirements. Do not fetch documentation, implement credential handling,
inspect or use a key, freeze a live packet, or call a provider in this phase.

## Entry Conditions Inherited From M20A

- M19 is closed and its one live attempt is consumed; it cannot be rerun or
  treated as M20 authority.
- M20A local no-network engineering passes under the close record dated
  `2026-07-14`.
- The official documentation campaign is permanently closed at `6/6`; it
  cannot be extended or reused.
- Checked OpenAlex singleton/list operations require `api_key`; anonymous API
  access is contradicted.
- The list response exposes `meta.cost_usd`, but retained route-operation pages
  do not establish the complete authentication/pricing/rate-limit policy.
- No key source, secret-handling authority, maximum cost/credit budget,
  provider API authority, identified M20 successor commit, or live packet
  exists.
- M20B, M21, source/PDF/full-text, push, and release remain forbidden.

## Required Artifacts

1. A bounded M20B1 authentication/pricing evidence-acquisition subplan covering
   exact official documentation targets, transaction/byte/time limits,
   retention, stop conditions, and a fresh output root. It cannot reopen the
   closed six-transaction campaign and remains non-executable until separately
   reviewed and authorized.
2. A credential decision request containing no secret value and asking the
   human to identify key ownership/authorization, permitted campaign, exact
   source interface, and rotation or revocation responsibility.
3. A privacy/redaction requirements record naming every tested persistence and
   diagnostic surface: descriptors, accepted bodies, filenames, process
   arguments, captured streams, logs, exceptions, manifests, JUnit, review
   packets, Git, and result documents.
4. A cost decision request asking for a numeric maximum campaign cost or credit
   use, request cap, accounting rule, and stop behavior when cost cannot be
   known before or reconciled after a request.
5. A phase map assigning exact ownership:
   M20B1 checks official authentication/pricing/rate-limit semantics;
   M20B2 implements and tests synthetic-canary credential/redaction/cost logic
   after the required human design decisions;
   M20B3 binds an identified commit/install and freezes the exact packet; and
   M20B4 is the separately authorized one-attempt live execution.
6. An M20B0 result or blocker record and a reviewed M20B1 subplan.

## Required Checks, Tests, And Review

- Skeptically audit wrong/stale pricing, proxy metrics, hidden environment
  assumptions, key leakage surfaces, post-response-only cost controls,
  unbounded retry/rate behavior, and artifacts that cannot prove redaction.
- Check that the M20B1 documentation plan uses a fresh campaign identity,
  exact official targets, bounded transaction/byte/time limits, no redirects
  or retries, fresh roots, and no provider API route.
- Check that the credential and cost decision requests contain no secret,
  implied approval, default key source, or assumed free-cost claim.
- Check the phase map assigns documentation acquisition only to M20B1,
  implementation/testing only to M20B2, commit/install/packet freeze only to
  M20B3, and provider execution only to M20B4.
- Check that later synthetic-canary criteria say no canary occurrence was
  observed across enumerated tested surfaces and failure paths; they must not
  claim universal zero secret persistence.
- Check that unknown or contradictory cost is a later fail-closed state and is
  never described as zero cost.
- Run JSON/Markdown structural checks, `git diff --check`, exact hash checks,
  stale-status searches, and forbidden-action scans. Runtime regressions are
  not required because M20B0 edits planning/control artifacts only.
- Obtain one material read-only review of M20B0 and the drafted M20B1 subplan.
  Review is advisory and cannot authorize documentation access, a key,
  implementation, spending, packet freeze, provider access, or live execution.

## Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Is the M20B credential/privacy/cost boundary decomposed into feasible phases with exact human and external-action gates before any implementation or provider access? |
| Baseline | M20A non-executable descriptors declare `required_external_not_present`; no current runtime reads or sends a key. |
| Primary criterion | Decision requests, phase ownership, successor documentation plan, handoff predicates, and forbidden actions are internally consistent and materially reviewed. |
| Hard vetoes | This phase reads a secret, fetches documentation, implements credential handling, assumes key ownership/cost, freezes a live packet, authorizes provider access, or makes a later phase reachable without its exact human/external gate. |
| Explanatory only | Proposed request counts, canary length, estimated response volume, and expected implementation effort. |
| Not concluded | Authentication/pricing correctness, key safety, absence of leaks, bounded provider cost, installed execution readiness, provider availability, search relevance, citation completeness, M20 success, M21 authority, product readiness, or north-star completion. |

## Default And Assumption Audit

| Choice | Provenance | Risk | Early diagnostic | Status |
| --- | --- | --- | --- | --- |
| Query-parameter key placement | Retained operation schemas require `api_key` in query | URLs commonly leak through logs/errors/process surfaces | M20B1 official authentication contract, then M20B2 canary matrix | Hypothesis pending M20B1 |
| Environment-based injection | Common local secret interface; not yet authorized | Broad environment inspection or inherited wrong credential | Human interface decision before M20B2; exact named-variable lookup only if selected | Convenience option, not selected |
| One live attempt | M20 master contract | Failure consumes campaign evidence budget | Local fake-provider and crash matrix | Inherited campaign constraint |
| Five-request maximum | M20 predeclared matrix | Provider pricing/rate semantics may make it inappropriate | Checked pricing/rate contract and computed worst-case bound | Pending reviewed default |
| Zero retries/redirects | M19/M20 boundary | Transient failure remains final | Honest unavailable/error disposition | Reviewed baseline |
| `meta.cost_usd` as accounting evidence | Retained list schema | Singleton or failed requests may lack comparable cost evidence | Per-route official contract and fail-closed unknown-cost state | Hypothesis only |

## Forbidden Claims And Actions

- Do not read, enumerate, print, hash, transmit, create, rotate, revoke, or use
  any real credential under this planning-only subplan.
- Do not fetch authentication/pricing documentation until the separate M20B1
  subplan is reviewed and authorized.
- Do not implement credential/redaction/cost runtime, call
  `api.openalex.org`, create a final live packet, or launch any M20B provider
  execution.
- Do not place a key in a command line, descriptor, file, test fixture, review
  packet, Git object, log, exception, or accepted-body store.
- Do not infer that absence of `meta.cost_usd` means zero cost, or that a free
  credit allowance authorizes spending.
- Do not use the M19 approval, reopen the closed documentation campaign, access
  source/PDF/full-text, start M21, mutate unrelated work, push, or release.
- Do not claim M20, the master program, or the north-star mission is complete.

## Exact Next-Phase Handoff Conditions

A separately bounded M20B1 documentation-acquisition phase may begin only
when:

1. M20B0 decision requests and the four-phase ownership map exist;
2. the M20B1 subplan names exact official documentation targets, fresh budget,
   fresh output root, retention, stop conditions, and nonclaims;
3. local structural, stale-status, forbidden-action, and boundary checks pass;
4. material read-only review finds no unresolved consistency, feasibility,
   artifact-coverage, proportionality, or boundary defect; and
5. the exact bounded documentation command receives the applicable trusted
   platform/network permission at launch.

M20B1 platform permission permits only the frozen public-documentation
acquisition. The user's existing execute/resume direction is sufficient
campaign authority for this bounded read-only documentation step under current
repository policy; no new ceremonial human wording is required. Neither that
direction nor platform permission authorizes environment inspection, a
credential, implementation, cost, packet freeze, a provider API call, or M20B4
execution.

M20B2 may be drafted after M20B1 retains and checks the official contract, but
may execute only after the human separately selects an authorized key
source/interface, privacy handling, and numeric maximum cost/credit budget.
M20B3 owns the identified commit/install and packet freeze after M20B2 passes.
Only exact human authorization of the final M20B3 packet can hand off to M20B4
and authorize the first provider API call.

## Stop Conditions

Stop with a blocker if phase ownership remains circular, the documentation
campaign cannot be bounded, decision requests require secret material, cost or
key authority is silently assumed, the successor plan authorizes more than
documentation acquisition, structural checks fail, review finds a material
unrepaired defect, or required trusted platform/network permission is denied.
Missing later key/cost decisions is an expected M20B0 handoff boundary, not
authority to guess them.

## Skeptical Pre-Execution Audit

Status: `PASS_FOR_PLANNING_ONLY`.

The current artifacts are sufficient to define the decision surface and draft
the separate M20B1 documentation phase, but not to check the external contract,
implement credential use, bind execution bytes, freeze a packet, or execute a
provider call. The most important hidden risk is collapsing those distinct
boundaries into one phase. Accordingly, M20B0 stops after reviewed planning and
before the frozen M20B1 command requests trusted platform/network permission.

## Successor Checkpoint - 2026-07-15

M20B1 and M20B2 subsequently passed in their bounded scopes. The human selected
`OPENALEX_API_KEY`, approved the enumerated privacy/two-occurrence canary
contract, and set the USD `$0.01` total campaign cap. M20B2 terminal review
agreed after material repair. The next phase is M20B3, which remains
non-executable until new explicit human authority for its exact bounded Git
payload, stage/commit, isolated clone, and offline wheel operation. No current
artifact authorizes a real key, provider call, M20B4, source access, push, or
release.
