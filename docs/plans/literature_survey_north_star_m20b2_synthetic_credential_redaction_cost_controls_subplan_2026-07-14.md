# M20B2 Synthetic Credential, Redaction, And Cost Controls Subplan

Date: `2026-07-14`
Status: `CLOSED_PASSED_LOCAL_SYNTHETIC_ONLY_M20B3_GIT_AUTHORITY_REQUIRED`
Milestone: `M20_live_discovery_and_citation_frontier`

## Phase Objective

Implement and locally test the smallest credential-injection, pre-format
redaction, and USD cost-accounting layer needed by the exact M20 OpenAlex
routes. Use only unique synthetic canaries. Do not inspect, read, request,
hash, or use a real key; do not call any provider; do not freeze the live
packet or perform Git integration.

## Entry Conditions Inherited From M20B1

- M20A route-independent and route-specific local engineering passes.
- M20B1 is permanently consumed at `2/2` documentation transactions and
  `867,402/4,000,000` accepted bytes with exact body/manifest closure.
- Official retained bytes establish query-parameter `api_key`, the current USD
  route schedule, `meta.cost_usd`, current rate-limit USD fields, reset and 429
  semantics, and deprecation of `credits_*` fields.
- Planned OpenAlex usage is `$0.0011`: search `$0.001`, singleton `$0`, and
  list/filter `$0.0001`.
- Before execution, the human must make all three decisions below without
  disclosing a secret value or secret-bearing path:
  1. select an authorized runtime interface and permit synthetic-canary local
     implementation;
  2. approve or revise the enumerated privacy/redaction requirements; and
  3. set a numeric maximum total M20 campaign usage cost and decide that
     unknown pre-request or unreconciled post-request cost stops dispatch.

Human decisions recorded `2026-07-15`:

- exact sole future runtime interface: `OPENALEX_API_KEY`;
- local M20B2 scope: synthetic canaries only; do not inspect, read, or use a
  real value;
- privacy: the enumerated M20B0 rules and reviewed two-occurrence canary
  contract are approved;
- maximum total M20 live-campaign usage cost: USD `$0.01`, counting usage
  covered by daily allowance or prepaid funds; and
- unknown pre-request cost, contradictory cost, or unreconciled post-response
  cost is a hard stop.

This authority excludes provider calls, real credential access, Git
integration, M20B3/M20B4, source access, push, and release.

## Skeptical Pre-Execution Audit

Status: `PASS_APPROVED_SELECTIONS_MATCH_REVIEWED_RECOMMENDATIONS`.

- Baseline: extend the reviewed credential-free `openalex_adapter.py`; do not
  replace its descriptors with secret-bearing descriptors.
- Proxy risk: canary absence is evidence only for enumerated tested surfaces,
  not universal secret safety.
- Cost risk: daily allowance is not zero usage cost. Route schedule and
  response `cost_usd` are cost evidence; result counts, bytes, latency, and
  citation counts are not.
- Environment risk: lookup of one selected variable is allowed only inside the
  worker after descriptor, route, output, and budget preflight. Broad
  environment enumeration is forbidden.
- Failure risk: standard URL/request exceptions can embed query strings. The
  authenticated construction and dispatch boundary must catch and convert
  every expected/unknown error to closed codes before any formatting,
  persistence, IPC, or captured stream.
- Artifact fitness: passing unit tests must prove exact route injection, cost
  state transitions, and canary absence across declared outputs and failure
  paths; they do not prove provider behavior or production security.
- Canary occurrence model: each isolated test case generates a fresh canary.
  Within one dispatching invocation, the selected named-interface value and at
  most one ephemeral authenticated request inside the worker/dispatch boundary
  are the only authorized in-memory occurrences. A fake dispatch sink must
  observe exactly one request for cases that reach dispatch and none for
  pre-dispatch failures. The canary must be absent from every value that
  crosses or survives that boundary. Test evidence records authorized
  occurrence type/count and prohibited-surface scan results without recording
  any canary bytes or digest.

The material plan review agreed after one canary-contract repair. Execution may
begin only after the three decisions are explicit and this audit is updated to
`PASS` with their exact selections. If a selection differs materially from the
reviewed recommendations, patch the plan visibly and run a focused rereview.

The `2026-07-15` audit passes. The approved selections exactly match the
reviewed recommendations, so no material redesign or rereview is required
before implementation. The credential-free adapter and route-independent
runtime remain at their previously reviewed hashes and are untracked program
artifacts, not overlapping tracked user edits. The planned live M20 supervisor
does not yet exist, so this phase uses a new standalone synthetic validation
script rather than inventing live orchestration. The implementation is limited
to a new boundary module, new focused tests, and new validation/plan artifacts.

Baseline attempt 1 failed during test collection because the selected
environment did not have this dirty source tree installed and omitted the
repository-required `PYTHONPATH=src`. No test executed. The unchanged command
was repaired as an environment invocation issue; with `PYTHONPATH=src` and
`CUDA_VISIBLE_DEVICES=-1`, the required M19/M20 baseline passed `188/188` in
`4.66s`, CPU-only and no-network.

## Required Artifacts

1. A credential-boundary module that:
   - accepts only an already validated credential-free OpenAlex descriptor;
   - reads only the human-selected exact runtime interface;
   - rejects missing, blank, duplicate/ambiguous, malformed, or wrong-source
     state before dispatch;
   - appends exactly one `api_key` query parameter only in worker memory;
   - returns no key, authenticated URL, request object, environment mapping, or
     secret-bearing exception; and
   - exposes only closed credential-presence and error codes.
2. A USD cost-policy module bound to the three exact OpenAlex route kinds:
   `topic_list=0.001`, `direct_singleton=0`, and `forward_list=0.0001`, plus the
   human-selected total campaign ceiling. It must reserve predicted cost before
   dispatch, reconcile finite nonnegative `meta.cost_usd` for list/search
   responses, treat the documented singleton as zero, and stop subsequent
   dispatch on unknown, contradiction, missing required reconciliation, or
   ceiling breach.
3. A unique runtime-generated synthetic-canary test matrix covering success,
   provider HTTP error, parser error, timeout, worker termination,
   IPC/serialization rejection, manifest-write failure, malformed credential
   state, unknown route cost, cost mismatch, and budget exhaustion. It must
   prove exactly two authorized occurrence classes per dispatching invocation:
   the selected named source value and one ephemeral authenticated request
   observed by a fake dispatch sink. A pre-dispatch failure may observe only
   the named source or neither class. No occurrence may be persisted or leave
   the boundary.
4. An enumerated scan manifest listing every tested file, stream, argument,
   returned value, exception, IPC value, temporary file, Git diff candidate,
   and serialized value that crosses or survives the dispatch boundary. It
   records authorized occurrence classes/counts separately from prohibited
   surfaces and stores no canary value or digest.
5. Focused and affected no-network test records, code/test SHA-256 manifest, a
   phase result or blocker, and a refreshed M20B3 subplan.

Planned edit surface, subject to material review:

- new `src/research_assistant/survey/openalex_credential_cost.py`;
- new `scripts/literature_survey_m20b2_synthetic_validation.py`; the planned
  live M20 supervisor does not yet exist and must not be created in M20B2;
- new `tests/unit/test_literature_survey_m20b2_credential_cost.py`;
- new `tests/scripts/test_literature_survey_m20b2_synthetic_validation.py`;
- M20B2 plan/result/review/validation artifacts; and
- north-star control records at the phase handoff.

No dependency, CLI, provider, route, source module, unrelated dirty file, or
product default may change without visible plan repair and focused rereview.

## Required Checks, Tests, And Review

1. Reparse both M20B1 manifests and verify the two official body hashes before
   using the documented schedule.
2. Run existing M20 route-independent, OpenAlex adapter, M19 transport, and
   supervisor tests before and after the change.
3. Test the credential-free descriptor remains byte-identical and rejects an
   embedded `api_key`; injection occurs only after descriptor and budget
   validation.
4. Test exact named-interface lookup without enumerating the environment, and
   fail before dispatch for absent/blank/malformed/wrong-source state.
5. Test that a fake dispatch sink sees exactly one query `api_key` carrying the
   runtime canary in the ephemeral authenticated request. The named source and
   that request are the only authorized occurrences; every returned,
   persisted, raised, serialized, IPC, logged, or captured representation must
   be canary-free.
6. Test the documented `$0.0011` route sum, exact reservation order, no
   overspend, daily/prepaid neutrality, finite/nonnegative USD validation,
   mismatch/unknown hard stops, and no use of deprecated `credits_*` authority.
7. Run the unique canary through every enumerated success and failure path.
   Evidence must show the two authorized ephemeral occurrence classes and no
   occurrence on any named prohibited surface. The only permitted claim is
   that this exact occurrence contract held for the enumerated tested paths.
8. Use `CUDA_VISIBLE_DEVICES=-1` before imports for all local checks and record
   CPU-only/no-network status. Run compile, JSON parse, secret-pattern scan,
   exact artifact inventory, and `git diff --check`.
9. Obtain one material read-only plan review before implementation and one
   material code/result review after the focused and affected gates. Reviewer
   agreement is advisory and authorizes no real credential, provider, Git,
   cost, or later-phase action. Repair material findings for at most five
   rounds on the same blocker.

## Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Can the exact M20 OpenAlex descriptors receive a credential only inside a bounded worker and account for USD route cost without exposing a synthetic canary on the enumerated tested surfaces? |
| Baseline | Reviewed credential-free OpenAlex adapter plus retained official M20B1 authentication/pricing bytes. |
| Primary criterion | Exact interface and descriptor ordering pass; a fake sink observes the canary only in the named source and one ephemeral authenticated request; no occurrence crosses or survives the dispatch boundary on any enumerated prohibited surface; all route costs reserve/reconcile within the human ceiling; and all focused/affected tests pass. |
| Hard vetoes | Real-secret access; broad environment inspection; secret in descriptor/argv/output/error/IPC/artifact; missing/duplicate key; unmapped or contradictory cost; overspend; provider call; source access; stale official evidence; unreviewed scope expansion. |
| Explanatory only | Test duration, canary length, response bytes, provider examples, daily allowance, result count, and route latency. |
| Not concluded | Universal leak freedom, untested OS/provider/proxy/shell/crash/swap surfaces, real-key availability or authority, actual balance/billing, provider readiness, M20B3/B4 authority, M20 completion, M21 readiness, product security, or scientific validity. |
| Preserving artifacts | Exact code/test hashes, canary scan inventory and result, cost truth table, CPU/no-network JUnit or logs, result/blocker, review verdict, and refreshed M20B3 plan. |

## Forbidden Claims And Actions

- Do not execute before the three human decisions and material plan review.
- Do not inspect environment variables now, ask for or persist a key, use a
  real key as a canary, hash a key, or record a secret-bearing path.
- Do not call `api.openalex.org`, `/rate-limit`, documentation, arXiv, source,
  PDF, full-text, or any network route.
- Outside the exact named source and ephemeral authenticated request inside the
  worker/dispatch boundary, do not put a key in a descriptor, returned value,
  command argument, filename, manifest, accepted body, log, exception,
  captured stream, IPC, review packet, test report, Git object candidate, or
  result.
- Do not treat canary absence as universal safety; do not treat the daily
  allowance as zero cost; do not silently map unknown cost to zero.
- Do not create/freeze M20B3 live execution bytes or packet, perform Git
  integration, spend funds/credits, start M20B4/M21, push, or release.

## Exact Next-Phase Handoff Conditions

Draft or refresh M20B3 only after the selected human decisions are recorded
without secrets; every focused and affected CPU-only/no-network check passes;
the exact canary occurs only in the two authorized ephemeral classes and is
absent from every enumerated prohibited surface; route-cost reservation and
reconciliation close under the selected ceiling; a result and code/test
manifest exist; and material review finds no unresolved issue.

M20B3 may integrate only the exact passed payload into an identified commit,
isolated wheel, and member-equality record, then freeze a separately reviewed
single-attempt packet. It may not read/use a real key or call a provider.
M20B4 remains a separate explicit human authorization boundary.

## Stop Conditions

Stop before implementation if any human decision is absent or contradictory,
the interface would require broad environment/secret inspection, the numeric
ceiling is not greater than or equal to `$0.0011`, retained official evidence
does not replay, the implementation surface overlaps protected user work, or
material plan review does not converge within five rounds.

During local implementation, stop with a blocker for any canary occurrence
outside the two authorized ephemeral classes, persistence of an authorized
occurrence, unbounded/unknown cost path, inability to sanitize before
formatting or IPC, failed affected regression, required dependency/CLI/product
change, real-key need, network need, or scope expansion. A fixable local test
defect triggers a visible repair and focused rerun; it does not authorize
crossing the human or provider boundary.

## Phase Close - 2026-07-15

M20B2 passed its authorized local synthetic-only scope. The authoritative
reviewed root is
`docs/validation/literature_survey_m20b2_synthetic_credential_cost_v8_2026-07-15/`;
the phase result is
`docs/plans/literature_survey_north_star_m20b2_synthetic_credential_redaction_cost_controls_result_2026-07-15.md`.
Final gates are `33` focused, `221` combined M19/M20/M20B2, and `42` retained
M20B1 tests. Round-2 material review returned `AGREE` after the round-1 findings
were repaired.

The next subplan is
`docs/plans/literature_survey_north_star_m20b3_identified_integration_and_live_packet_subplan_2026-07-15.md`.
Its consistency, correctness, feasibility, artifact coverage, and boundary
safety were included in the terminal review. It remains non-executable until
new explicit human authority for the exact bounded M20B3 Git integration.
