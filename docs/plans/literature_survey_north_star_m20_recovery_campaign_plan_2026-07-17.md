# M20 Live Discovery Recovery Campaign Plan

Date: `2026-07-17`
Status: `LOCAL_RECOVERY_IMPLEMENTATION_AUTHORIZED_EXTERNAL_BOUNDARY_PENDING`
Milestone: `M20_live_discovery_and_citation_frontier`
Closes if passed: `G3_live_citation_discovery`

## Objective

Recover from the historical M20B4 early exit without reusing or rerunning its
consumed packet. Produce one fresh, bounded, replayable live metadata and
citation-frontier result, or an evidence-complete stop that identifies the
failed stage closely enough for an authorized in-campaign infrastructure
repair.

The engineering question is whether the identified workflow can execute the
five reviewed arXiv/OpenAlex metadata routes, preserve complete request and
accepted-body evidence, replay accepted bodies offline, and distinguish
identity/frontier outcomes from source support and scientific claims.

## Preserved Baseline

- Historical packet `c3e250b0...d77ce` and its consumed attempt are immutable
  evidence and must never be invoked again.
- The historical attempt exited `2` before a live manifest existed. Its exact
  cause, credential state, provider activity, cost, and privacy state remain
  `not_established`.
- M20A-M20B3 local engineering remains the baseline. A new campaign must build
  a new identified install and packet after the recovery repair.
- M21-M23, source/PDF/full-text access, push, release, product-default changes,
  and scientific-completion claims remain outside this campaign.

## Skeptical Plan Audit

The historical command cannot answer the recovery question because
`m20_live_supervisor.main()` returns the same unrecorded exit `2` for packet
preflight failure and unavailable credentials. Repeating that command could
consume another live attempt without locating the failure. The campaign must
therefore add a credential-free diagnostic record before any new external
launch.

Audit results:

- Baseline is the identified M20B3 install, not the dirty working tree.
- Request counts, candidate counts, and latency are descriptive only. They are
  not promotion criteria or provider rankings.
- A missing or invalid credential is an external-boundary failure, not provider
  evidence.
- A failed candidate or empty frontier does not invalidate the harness and is
  not a continuation veto by itself.
- A missing manifest, incomplete disposition ledger, invalid replay, unknown
  cost, or unreaped process is a validity veto.
- Every attempt needs a fresh versioned root. Prior evidence is never
  overwritten.
- The campaign passes this audit for local recovery implementation only.
  Credential access, paid provider calls, and the live launch remain a separate
  explicit human boundary.

## Evidence Contract

| Item | Contract |
| --- | --- |
| Question | Can the five-route M20 metadata/frontier workflow execute with boundary-valid, replayable evidence? |
| Baseline | M20B3 commit `7283a00e...a25c`, installed packet preflight, and the historical early-exit result |
| Primary pass criterion | A fresh live root has a valid manifest, complete five-row disposition ledger, accepted-body inventory, offline replay, reconciled cost evidence, and valid identity/frontier outcomes |
| Promotion vetoes | Invalid identity binding, missing/extra artifacts, accepted-body mismatch, failed replay, unreconciled cost, credential representation in retained artifacts, or invalid process lifecycle |
| Continuation vetoes | Unknown prior provider/cost state before a retry, campaign budget exhausted, corrupted immutable evidence, unbounded process state, privacy-boundary failure, or changed scientific/provider contract |
| Repair triggers | Packet/install/preflight, launch instrumentation, serialization, process supervision, or other localized infrastructure failure with provider and cost state established |
| Explanatory only | Counts, latency, result ordering, citation yield, and observed provider differences |
| Nonclaims | Literature completeness, provider reliability, source support, scientific correctness, candidate superiority, product readiness, or north-star completion |
| Result artifacts | Versioned attempt roots plus a terminal campaign result under `docs/plans` and a run manifest under `docs/validation` |

## Default And Assumption Audit

| Choice | Provenance and status | Failure mode and early diagnostic |
| --- | --- | --- |
| Existing topic and seed identifiers | Reviewed M19/M20 baseline; retained to isolate recovery from query drift | Provider identity may change; exact identity outcomes preserve conflict/absence |
| Five-route order and metadata fields | Reviewed M20 route contract; baseline, not a universal default | Schema or route drift; installed synthetic replay and fresh packet preflight |
| `OPENALEX_API_KEY` | Sole previously reviewed runtime interface; external boundary | Missing/invalid value; diagnostic record must distinguish unavailable credential without exposing it |
| CPU-only execution | Metadata HTTP/JSON/XML workload; convenience choice | Unexpected accelerator dependency; installed import/preflight catches it |
| USD `$0.01` proposed total campaign cap | Previous approved cap and current documented route estimate; pending fresh external approval | Unknown/contradictory/unreconciled cost stops before another launch |
| Two provider-capable launches maximum | Allows one localized retry while bounding selection and cost; pending fresh external approval | A first attempt with unknown provider/cost state forbids the second |

## Campaign Stages

### Stage 1 - Local Recovery Instrumentation

Add a required, credential-free launch diagnostic record to the new packet and
supervisor command. It must be validated before credential lookup and written
exactly once with one of these stage outcomes:

- packet/preflight failure with a bounded safe error code;
- credential unavailable after successful preflight;
- supervised execution returned, with exit code and manifest-presence facts;
- unexpected supervisor error, without exception text or environment data.

The record must never contain the credential, its digest, headers, URLs with
credentials, environment enumeration, or provider response content.

Required checks: focused unit tests for all four branches, existing worker and
supervisor suites, compile, JSON parsing, and `git diff --check`.

### Stage 2 - Identified Fresh Install And Packet

Create a fresh identified Git commit containing only the reviewed recovery
delta and required plan/control updates. Reproduce it from an isolated clone,
build an offline wheel, verify complete wheel/install member equality, run
installed synthetic validation, and freeze a new packet with fresh diagnostic
and live roots. The historical packet and roots remain unchanged.

Required checks: source and installed tests, exact module origins and hashes,
packet preflight with `OPENALEX_API_KEY` removed, root freshness, process
absence, JSON parsing, and empty Git index after the bounded commit.

### Stage 3 - Material Advisory Review

Review the compact plan/code/test/packet evidence once. Claude may act only as
a read-only reviewer through bounded probes; if unavailable, record that and
use a fresh Codex review. Material engineering, privacy, cost, or scientific
findings must be repaired and retested. Procedural-only review disagreement is
not execution authority and does not block adequate local evidence.

### Stage 4 - External Campaign Boundary

Before the first provider-capable launch, obtain explicit confirmation that:

- the key owner/controller permits this fresh campaign;
- `OPENALEX_API_KEY` may be read by the installed supervisor after complete
  preflight;
- arXiv/OpenAlex provider calls are authorized;
- total campaign usage cost is capped at USD `$0.01`, including prepaid or
  allowance-covered use; and
- at most two provider-capable launches may occur, with no second launch if
  prior provider activity or cost is unknown or unreconciled.

The user's authorization to open the campaign authorizes Stages 1-3. It is not
interpreted as permission to inspect a secret or incur provider usage cost.

### Stage 5 - Live Attempts And Repair Loop

Run each launch with trusted network/credential permissions and a fresh
versioned attempt root. Preserve command, commit, environment, CPU-only status,
times, exit, diagnostic record, live manifest, ledgers, and closeout result.

After an unsuccessful attempt, classify it before deciding whether to continue:

- Localized failure before provider dispatch with established zero cost:
  repair, run focused regression, rebuild a fresh identified packet if bytes
  changed, and continue within the campaign.
- Failure after dispatch with complete reconciled cost and remaining campaign
  budget: one localized repair/retry may continue if the target, routes, data,
  privacy boundary, and promotion criteria are unchanged.
- Unknown provider activity, unknown/unreconciled cost, privacy failure,
  corrupted evidence, or unbounded process state: stop immediately.
- Boundary-valid empty, ambiguous, conflicting, or candidate-negative result:
  record it as scientific/provider observation; do not relabel it as harness
  failure or retry merely to improve the outcome.

## Campaign Budget

- Local focused tests and synthetic/preflight attempts: bounded by three
  versioned implementation/install iterations before human direction.
- Provider-capable launches: proposed maximum `2`, pending Stage 4 approval.
- Total provider usage cost: proposed maximum USD `$0.01`, pending Stage 4
  approval.
- No retry may overwrite evidence or proceed with unknown prior cost/provider
  state.

## Handoff And Stop Conditions

M20 may close only when the primary pass criterion is met and terminal result
review finds no material evidence defect. Then refresh M21 from actual M20
artifacts; do not execute M21 without its own source-access boundary.

Stop for human direction when the external boundary is not granted, the
campaign budget is exhausted, a continuation veto fires, more than three local
recovery iterations are needed, or closing G3 would require changing the topic,
seed, provider contract, privacy boundary, cost cap, product behavior, or
scientific claim.
