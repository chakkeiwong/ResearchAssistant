# M20 Live Discovery And Citation Frontier Subplan

Date: `2026-07-14`
Status: `MATERIAL_PLAN_REVIEW_AGREED_M20A_LOCAL_READY_M20B_DO_NOT_EXECUTE`
Milestone: `M20_live_discovery_and_citation_frontier`
Closes: `G3_live_citation_discovery`

## Phase Objective

Implement production topic-bootstrap and explicit-paper discovery capabilities
over the M19 fail-closed transport, then validate one separately approved,
predeclared metadata-only matrix with complete request, identity, frontier,
disposition, omission, resume, and invalidation evidence.

M20 must distinguish provider observations from identity authority and citation
navigation from source support. It does not retrieve source, PDF, or full text;
authenticate a human reviewer; establish literature completeness; or authorize
M21.

## Entry Conditions Inherited From M19

| Authority | Actual M19 value | M20 consequence |
| --- | --- | --- |
| Execution commit | `f06ceb72cd1bb0628b01f206f9e82697e23cb0c7` | Baseline for every M20 code delta |
| Code-authority ancestor | `bb4300c6bce20145a7c41620b0dffb703072e755` | M19 transport behavior must not regress |
| Live root | `docs/validation/literature_survey_m19_live_metadata_2026-07-14/` | Immutable input; never edit or reuse as output |
| M19 result | `docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_result_2026-07-13.md` | Must pass terminal review before M20 execution |
| Durable replay | SHA-256 `71f6766d5804c0392f2af0f3b1e897a3e8b3081d44037c64deb6bfe92ade9059` | All `14` M19 replay checks passed |
| Request ledger | SHA-256 `df51c0fd64bc407850c308d92a6658142734b5892efa8aff10c4a1405fd9b782` | Four exact closed rows; zero redirects/retries/invalid rows |
| Observed schemas | M19 request/route ledgers plus V2 `identity_resolution`, `relevance_ranking`, `candidate_ledger`, `citation_map`, `metadata_provenance`, and `workflow_state` | M20 schema adapters must replay actual bytes before extension |
| Provider observation | arXiv seed `1`; arXiv topic `10`; OpenAlex seed `0`; OpenAlex topic `10` | Literal OpenAlex free-text arXiv seed search is not an identity resolver |
| V2 state | `10` records, eligible metadata packet, `ready_for_prose=false` | Navigation-only baseline; no claim/source promotion |
| Live authority | M19 attempt budget `1/1` consumed | No M19 retry and no inherited M20 provider authority |

The M19 live root contains normalized records but not accepted provider body
bytes. Those bytes cannot be manufactured after the fact into a
recorded-response fixture. M20 catching fixtures must be sanitized, synthetic,
and visibly labeled, while M19 normalized artifacts remain independent
observed-schema evidence. Unlike M19, M20 must retain each future accepted
public-metadata response body exactly, within the approved byte caps, in its
immutable live root. Each body is hash-bound to one request row and reparsed
offline. Response headers, cookies, request headers, exception text,
credentials, proxy data, and transport diagnostics are not retained in the
body store.

## Skeptical Plan Audit

Pre-execution audit status: `PASS`. Material read-only review converged at
round 4 after repairs for accepted-body replay, deterministic outcome/cap
semantics, identity/frontier separation, and backward-attempt origin binding.
M20A local implementation may begin under the exact allowlist. M20B live use
remains blocked pending M20A evidence, code/packet review, and fresh exact human
approval.

- Baseline: M19 proves transport/ledger closure for four routes, not production
  bootstrap, identity quality, or frontier coverage.
- Proxy discipline: availability, record counts, relevance scores, citation
  counts, latency, and bytes are explanatory only.
- Identity risk: the OpenAlex seed result of zero is evidence that the current
  free-text query does not resolve this seed; M20 must not reinterpret a topic
  result as the seed.
- Provider-route risk: repository code does not contain a checked official
  contract for an OpenAlex external arXiv-ID route. M20 must not guess one.
- Comparison fairness: the OpenAlex case below is derived from M19 output and
  is explicitly transport/frontier coverage, not an unbiased relevance case.
- Stop logic: candidate, provider, or frontier failure preserves an honest
  disposition and continues the predeclared matrix unless the harness,
  boundary, authority, or evidence is invalid.
- Environment: local work is CPU-only and no-network; any provider run requires
  trusted/escalated execution and a fresh exact approval.
- Artifact fitness: ledgers must reconstruct every dispatched request and every
  frontier attempt; packet counts alone cannot pass M20. Selected identity and
  frontier authority require exact offline parser replay from the retained
  accepted body bytes. Transport-only closure cannot hand content-derived
  authority to M21.

## Research Intent Ledger

| Field | M20 contract |
| --- | --- |
| Main question | Can real bounded topic and explicit-paper metadata discovery create honest bootstrap and citation-frontier authority or exact closed stops? |
| Candidate/mechanism | Production `MissionBootstrapCapability` and frontier observation capability over a generalized M19 supervisor/transport with complete ledgers. |
| Expected failure mode | A topic result is silently promoted to seed identity, an OpenAlex mismatch is merged, or a missing/capped frontier disappears. |
| Promotion criterion | Every predeclared case has exact request, identity, attempt, target-disposition, omission, resume, and invalidation closure; explicit seeds remain lineage-valid; topic ambiguity remains visible. |
| Promotion veto | Call before persisted confirmation; unapproved route; missing request/attempt/disposition; silent conflict merge; stale authority; fabricated selection; outside write; false completeness or support. |
| Continuation veto | Wrong execution bytes, invalid transport/harness, corrupt ledger, unrepresentable identity/disposition, absent exact live approval, criteria change after results, or five-round material nonconvergence. |
| Repair trigger | No-network test failure, schema drift, identity conflict, partial outage, missing disposition, resume/invalidation mismatch, or material review finding. |
| Explanatory only | Counts, scores, ordering, citation totals, overlap, latency, bytes, provider yield, and metadata contents. |
| Must not be concluded | Completeness, paper importance, provider reliability, source support, claim correctness, human review, product readiness, or statistically supported provider ranking. |

## Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Can bounded real topic/paper discovery produce lineage-valid authority or exact honest stops with fully closed frontiers? |
| Baseline/comparator | M17 bootstrap outcome/store contracts, M16 frontier ledger contracts, and the actual M19 transport/replay result. |
| Primary criterion | All predeclared cases close every request and frontier attempt; every accepted body is hash-bound and reparsed exactly; selected explicit-paper authority binds exact replayed identifiers; topic ambiguity is not auto-selected; replay and resume/invalidation pass. |
| Hard vetoes | Unconfirmed or unapproved request; route/cap drift; hidden retry/redirect; fabricated identity; missing attempt/target; stale/corrupt result accepted; outside write; source access; false completeness/support. |
| Explanatory diagnostics | Retrieval volume, ranks, overlap, citations, latency, bytes, and per-provider yield. |
| Not concluded | Literature completeness, identity truth for unresolved rows, relevance/importance, provider reliability, source safety, claim support, scientific correctness, product or default readiness. |
| Preserving artifacts | Provider-contract snapshot, code/test manifest, no-network fixtures, frozen route/case/outcome packet, run manifests, bounded accepted body bytes and hashes, request/identity/frontier/omission ledgers, parser replay, result, terminal review, and refreshed M21 plan. |

## Default And Assumption Audit

| Choice | Provenance | Justification | Failure mode | Earliest diagnostic | Status |
| --- | --- | --- | --- | --- | --- |
| arXiv and OpenAlex only | M19 reviewed boundary and mission confirmation | Reuses the only hardened public metadata providers | Scope expands through hidden hosts or redirects | Exact opener/route allowlist tests | Baseline |
| M19 transport guards | M19 terminal hardening evidence | Already fail closed on route, proxy, redirect, retry, bytes, process, IPC, and writes | Generalization weakens a guard | Run all `26 + 30` M19 focused tests first | Reviewed baseline |
| Topic cap `10/provider` | M19 live route | Small diagnostic surface | Cap truncates relevant candidates | Persist cap state and continuation risk | Convenience cap, not a default |
| Explicit seed cap `5` | M19 live route | Allows ambiguity visibility | Multiple results are silently picked | Exact candidate/ambiguity tests | Convenience cap |
| Frontier cap `10/direction/case`, depth `1` | Smallest bounded M20 ladder | Tests real frontier shape without crawl | Volume is mistaken for coverage | Deterministic lexical target selection plus explicit remainder dispositions | Hypothesis |
| `30s` socket, `367s` attempt | M19 timeout plus five-route allowance | Bounded supervisor behavior | Slow provider consumes matrix | Fake-clock/watchdog tests | Convenience bound |
| Zero redirects/retries | M19 contract | Preserves exact request accounting | Transient failure looks final | Honest unavailable disposition | Reviewed baseline |
| M19-derived `W4387130479` case | First OpenAlex topic record in immutable M19 evidence | Provides a known-format explicit OpenAlex ID for transport/frontier coverage | Post-result selection is misrepresented as relevance evidence | Label case `derived_engineering_coverage` everywhere | Diagnostic only |
| Exact accepted body retention | Terminal M19/M20 review finding | Content-derived authority must be reproducible from the bytes actually parsed | Parser output cannot be independently reconstructed | Hash-bind and reparse every accepted body offline | Required for M21 handoff |

No M20 choice becomes a product default. If official provider documentation
contradicts any route or field assumption, patch this plan and route manifest
before implementation or live use.

## Exact Phase Structure

### M20A - Provider Contract And Local Adapter Hardening

Objective: freeze official route/schema semantics and implement no-network
production capability contracts without any provider call.

1. Save a dated, hashed local snapshot or verbatim bounded extract of official
   arXiv and OpenAlex API documentation for only the routes/fields below. If no
   checked local copy exists, obtaining it is a separate external-network
   boundary and must be explicitly authorized; do not infer semantics from
   memory.
2. Implement a generalized fail-closed discovery transport by extending the
   M19 primitive. Unexpected parser/programmer errors remain boundary errors,
   never ordinary provider unavailability.
3. Implement a production bootstrap capability that emits only the M17 closed
   outcomes: `selected`, `empty`, `ambiguous`, `unavailable`, or `capped`.
   Topic search with multiple viable candidates must be `ambiguous`; heuristic
   order alone cannot select.
4. Implement frontier request/observation adapters whose outputs validate the
   existing M16 attempt/disposition cardinality contract. Projection and real
   provider observation must remain separate mechanism kinds.
5. Add synthetic sanitized response fixtures and exhaustive no-network tests.
6. Freeze separate canonical identity/bootstrap and per-frontier-attempt
   automata plus their cross-product as canonical JSON and hash them into the
   M20B approval packet. The automata must define candidate validity, identity
   equivalence/conflict, partial-provider precedence, role-scoped cap
   precedence, and every request-state-to-outcome mapping below.
7. Implement bounded accepted-body retention with exclusive regular-file
   creation, request-binding name, size and SHA-256 in the request ledger,
   inventory closure, and offline byte-for-byte parser replay. A missing,
   extra, mismatched, unparsable, or differently normalized body is a boundary
   or artifact failure, not provider unavailability.

M20A handoff: code and fixtures are tied to an identified successor commit;
all local catching/cumulative gates pass; official route contracts and all
defaults are hashed; material code/plan review agrees; and an exact live packet
is frozen. M20A does not itself authorize provider access.

### M20B - Exact Bounded Live Matrix

Objective: run the frozen five-request matrix once under separate approval and
classify boundary validity before contents.

The matrix must use fresh output roots and this order:

| Case | Input/role | Exact planned requests | Max normalized records | Required outcome semantics |
| --- | --- | --- | ---: | --- |
| `topic_bootstrap` | Topic `Neural Optimal Transport for generative modeling and inference` | arXiv `/api/query` topic search, then OpenAlex `/works` topic search | `10/provider` | no heuristic selection; use the frozen outcome automaton below |
| `explicit_arxiv_seed` | `arxiv:2201.12220v3` | arXiv `/api/query` exact `id_list` only | `5` | exact arXiv identity selected or exact closed failure; no invented OpenAlex alias |
| `openalex_frontier_coverage` | `openalex:W4387130479`, role `derived_engineering_coverage` | OpenAlex `/works/W4387130479` exact work, then OpenAlex `/works` with exact `filter=cites:W4387130479` | `1 + 10` | direct identity plus backward relations from `referenced_works`; forward query gets one closed attempt and dispositions |

All OpenAlex requests use the M19 `select` field set:
`id,display_name,authorships,publication_year,doi,cited_by_count,referenced_works,ids,type,publication_date`.
The forward query additionally uses `sort=cited_by_count:desc`. Exact encoded
queries, headers, bindings, route-manifest digest, execution commit, command,
and roots must be generated and reviewed after M20A; if official documentation
does not support a route exactly, remove or replace it through visible plan
repair before approval, never during the run.

### Frozen Outcome Automaton Contract

M20A must serialize the rules below as canonical JSON, test every row, and bind
its SHA-256 into the reviewed live packet. Implementation may not choose a
different rule after observing live data.

Candidate validity and identity equivalence:

1. A raw row is valid only when its exact provider schema parses under the
   official contract and the closed local schema; malformed or partial rows
   are excluded with a row disposition and cannot contribute aliases.
2. Strong aliases are exact normalized DOI, exact normalized OpenAlex work ID,
   and normalized arXiv version family. Rows sharing a strong alias form one
   component independent of provider/list order.
3. An arXiv version family is one identity; the highest observed version is
   canonical. Different arXiv families or different non-null DOIs in a
   component are conflicts. Material title, first-author, or unanchored year
   mismatch uses the existing `discovery_quality.py` conflict rules and cannot
   select.
4. Multiple raw rows collapsing to one non-conflicting component count as one
   candidate; every raw row still receives a duplicate/merged disposition and
   remains hash-replayable.
5. Topic search never establishes an exact user-supplied identifier. It may
   select only when exactly one non-conflicting component remains after the
   predeclared topic-validity predicate. That predicate is conservative: the
   normalized title must equal the normalized topic or satisfy the existing
   checked high-margin title rule (`>=0.96`, at least three informative query
   tokens, margin `>=0.08`). Any zero, multiple, conflicting, or weak candidate
   is not selected.
6. Explicit arXiv/OpenAlex cases require their exact normalized identifier or
   arXiv family in the replayed row. Title/citation/order similarity cannot
   substitute for an absent exact identifier.

The result schema has independent fields:

- `identity_outcome`: one of `selected`, `empty`, `ambiguous`, `unavailable`,
  `capped`, or `boundary_invalid`, computed only from requests assigned the
  `identity_or_bootstrap` role; and
- `frontier_outcomes`: one closed row per frontier attempt with an exact
  `origin_request_binding_sha256`. The backward attempt binds the direct-work
  request/body from which `referenced_works` is extracted; the forward attempt
  binds the forward-query request/body. Each row has
  `observed_results`, `empty_observed`, `provider_unavailable`, `capped`, or
  `not_observed`, `boundary_invalid`, or `not_dispatched_due_to_veto`, plus its
  exact target dispositions or one target-free attempt risk.

Forward-query rows never enter the direct-identity candidate set. Direct-work
rows may carry backward `referenced_works`, but the resulting backward attempt
does not change `identity_outcome`. Identity caps apply only to identity-role
responses; frontier caps apply only to their corresponding frontier attempt.
Any boundary-invalid state is additionally a global M20B veto and stops further
dispatch.

Identity/bootstrap automaton:

| Identity-role request/body state after boundary validation | `identity_outcome` |
| --- | --- |
| Any identity-role boundary-invalid request, missing body for an accepted request, body hash mismatch, parser/programmer error, or unclosed request | `boundary_invalid` |
| Identity-role response reports more results/continuation than the approved identity cap | `capped` |
| All required identity-role requests unavailable | `unavailable` |
| At least one required identity-role request available and every available request yields zero valid identity components | `empty` |
| Exactly one valid non-conflicting component satisfies the case predicate, no competing identity component/conflict/identity cap exists, and no unavailable provider is required to disambiguate it | `selected` |
| One required topic provider is unavailable while another produces a candidate, provider identity evidence conflicts, more than one valid component remains, or the topic predicate is weak | `ambiguous` |
| Malformed rows exist but the identity response envelope is parseable | Exclude and disposition those rows, then classify remaining valid identity components; if the envelope cannot be completely parsed, `boundary_invalid` |

For `explicit_arxiv_seed`, arXiv is the only identity-role request, so one exact
arXiv-family result may select. For `topic_bootstrap`, both topic requests are
identity-role requests; one provider unavailable with a candidate from the
other is always `ambiguous`, never selected. For
`openalex_frontier_coverage`, only `/works/W4387130479` is identity-role and it
selects only an exact `W4387130479` result; forward citing rows cannot satisfy
or compete with that identity predicate.

Per-frontier-attempt automaton:

| Frontier-role request/body state after boundary validation | Frontier attempt outcome |
| --- | --- |
| Boundary-invalid request, missing/mismatched accepted body, parser/programmer error, or unclosed request | `boundary_invalid` and global M20B veto |
| Available response proves more valid targets or unseen continuation than the frontier cap | `capped`; retain admitted and omitted/remainder dispositions |
| Request unavailable | `provider_unavailable` with exactly one target-free attempt risk |
| Available response has zero valid target IDs and no continuation | `empty_observed` with exactly one target-free attempt risk |
| Available response has one or more valid target IDs within cap | `observed_results`; every target has exactly one observation disposition |

The direct OpenAlex work's retained body supplies two separately replayed role
views: direct identity and backward `referenced_works`. Its backward attempt
binds the direct request binding even though there is no separate backward
request. The forward query creates a separate forward attempt bound to its own
request. Each attempt is classified independently; neither overwrites the
direct `identity_outcome`.

Backward-attempt derivation from the direct-work request/body:

| Direct-work request / identity state | Backward extraction state | Backward attempt outcome |
| --- | --- | --- |
| Direct request `boundary_invalid` | not evaluated | `not_dispatched_due_to_veto`; global veto already active |
| Direct request unavailable | no accepted body | `provider_unavailable` with one target-free risk bound to the direct request |
| Accepted body, any identity state | backward parser, body binding, or `referenced_works` schema invalid | `boundary_invalid`; global veto, even if identity fields had independently selected |
| `selected` | zero valid referenced-work IDs | `empty_observed` with one target-free risk |
| `selected` | `1..10` unique valid referenced-work IDs | `observed_results` with one disposition per ID |
| `selected` | more than `10` unique valid IDs or official continuation evidence | `capped` with admitted, omitted-by-cap, and remainder reconciliation |
| `empty`, `ambiguous`, or `capped` | parseable referenced-work field of any size | `not_observed` with one `origin_identity_not_selected` attempt risk; every visible ID is recorded as `not_admitted_identity_unresolved` and cannot become frontier authority |

Backward cap, empty, unavailable, or `not_observed` never changes
`identity_outcome`. Backward `boundary_invalid` never changes the already
computed identity field either, but it makes the global M20B result invalid and
prevents M21 handoff.

Required direct-identity by forward-query projection, serialized and tested
before packet freeze:

| Direct-work identity state | Forward-query state | Identity field | Forward field | Global action |
| --- | --- | --- | --- | --- |
| `boundary_invalid` | any / not dispatched | `boundary_invalid` | `not_dispatched_due_to_veto` | fail M20B; stop |
| `selected` | `boundary_invalid` | `selected` | `boundary_invalid` | fail M20B; stop |
| `selected` | `observed_results` | `selected` | `observed_results` | preserve both; continue replay |
| `selected` | `empty_observed` | `selected` | `empty_observed` | preserve target-free risk |
| `selected` | `provider_unavailable` | `selected` | `provider_unavailable` | preserve target-free risk |
| `selected` | `capped` | `selected` | `capped` | preserve admitted, omitted, and remainder rows |
| `empty` | any non-boundary state | `empty` | classified independently | no selected OpenAlex identity; forward rows remain navigation-only and cannot enter M21 candidate authority |
| `unavailable` | any non-boundary state | `unavailable` | classified independently | same: no selected identity; forward rows remain navigation-only |
| `capped` | any non-boundary state | `capped` | classified independently | same: no selected identity; direct identity is not promoted |
| `ambiguous` | any non-boundary state | `ambiguous` | classified independently | same: quarantine identity; forward rows remain navigation-only |

The future canonical automaton is three-axis, not the two-axis summary above.
It must enumerate every permitted tuple
`(identity_outcome, backward_frontier_outcome, forward_frontier_outcome)`
before packet freeze. The exact composition rules are:

1. Compute `identity_outcome` from only the direct identity-role view.
2. Compute the backward outcome from the table above using the same retained
   direct body and bind it to the direct request.
3. If either field is `boundary_invalid`, set forward to
   `not_dispatched_due_to_veto`; otherwise dispatch and classify the forward
   request independently.
4. If forward is `boundary_invalid`, preserve the already computed identity
   and backward fields but set global status `boundary_invalid`.
5. Otherwise global status is `closed`, and the tuple is preserved without
   precedence or overwriting between axes.
6. M21 candidate authority exists only when identity is `selected`, global
   status is `closed`, and accepted-body replay passes. Backward/forward fields
   remain navigation authority only within their recorded observed/capped
   scope. If identity is not selected, all backward/forward visible rows remain
   navigation-only and cannot create candidate authority.

The future canonical artifact must expand all summarized rows into the full
permitted Cartesian subset, reject every tuple inconsistent with the backward
derivation/dispatch rules, and exhaustively test every accepted and rejected
tuple. This includes selected identity crossed with backward
observed/empty/capped/boundary states and forward observed/empty/unavailable/
capped/boundary/not-dispatched states, plus every nonselected direct identity
state and its permitted backward/forward states.

### Frontier Truncation And Disposition Contract

- Preserve provider-reported list order and total/count/cursor metadata as
  descriptive provenance when the official schema supplies them; never treat
  that order as relevance or importance authority.
- Normalize every observed OpenAlex target ID, deduplicate exact IDs, then sort
  lexically by normalized ID for deterministic engineering selection. Admit
  the first `10` IDs for the direction at depth `1`.
- Every additional observed ID receives `omitted_by_cap` with the origin,
  direction, provider list index, normalized target ID, and retained body hash.
  It remains an omission risk and cannot silently disappear.
- If the official response reports total/cursor/continuation beyond returned
  IDs, write one `unobserved_provider_remainder` disposition with the reported
  count/token provenance. Never invent identities for unseen rows.
- Available zero results produce `empty_observed`; unavailable responses
  produce `provider_unavailable`; conflicting targets produce `quarantine`;
  malformed targets get an exact malformed disposition or make the request
  boundary-invalid under the automaton. Each attempt has observations or one
  target-free attempt risk, never both.
- Backward `referenced_works` and forward result targets use the same lexical
  rule. The ledger records total observed valid IDs, duplicate IDs, admitted
  IDs, omitted-by-cap IDs, malformed IDs, and any unobserved provider remainder
  so their cardinalities reconcile exactly.

Campaign caps: exactly `5` attempted requests maximum, zero retry, zero
redirect, `2,000,000` accepted bytes/request, `10,000,000` total accepted
bytes, `30` seconds/request, `367` seconds whole attempt, no proxy,
credentials, cache, source/PDF/full-text access, or writes outside the frozen
M20 live root. Exact accepted public-metadata body bytes are the sole retained
live response content; each is capped, hash-bound, never logged, and retained
only inside that root. A launched matrix consumes its one attempt regardless
of provider outcome; no automatic rerun.

M20B handoff: offline replay reparses the exact accepted bodies and reconstructs
routes, requests, normalized records, identity outcomes, attempts,
observations, dispositions, omission risks, resume, invalidation, environment,
inventory, and summaries. Provider/candidate failure does not invalidate M20
if the boundary and all ledgers are closed, but M21 receives only explicit
candidates whose content-derived authority replays exactly from retained
bodies. Without exact body replay, M20 can close transport only and cannot hand
selected identity or frontier authority to M21.

## Exact Edit And Write Allowlist

M20 planning/review may edit only this subplan, its compact review artifacts,
and the north-star control records. M20A implementation, after plan agreement,
is limited to:

- `src/research_assistant/survey/discovery_capability.py` (new);
- focused changes in `src/research_assistant/survey/bootstrap.py`,
  `src/research_assistant/survey/build.py`,
  `src/research_assistant/survey/frontier_expansion.py`, and
  `src/research_assistant/survey/orchestrate.py`;
- `scripts/literature_survey_m20_live_discovery_supervisor.py` (new);
- `tests/unit/test_literature_survey_m20_discovery.py` (new);
- `tests/scripts/test_literature_survey_m20_live_discovery_supervisor.py` (new);
- `tests/fixtures/literature_survey_m20/` (new, synthetic sanitized fixtures);
- `docs/validation/literature_survey_m20_local_hardening_2026-07-14/` (new);
- `docs/plans/literature_survey_north_star_m20_*` and
  `docs/reviews/literature_survey_m20_*`; and
- the four north-star master/ledger/runbook/handoff controls after a gate.

Any CLI change, new dependency, other provider/host, source/download module,
different live case, or write root requires visible plan repair and focused
rereview. Protected dirty files listed in the M19 handoff remain untouched.

## Required Artifacts

- Dated official-provider contract snapshot/extract and hashes.
- M20A implementation/test manifest and identified successor commit.
- Synthetic fixture manifest with explicit non-live provenance.
- Canonical outcome-automaton and frontier-truncation manifests, their hashes,
  and exhaustive truth-table tests.
- Closed request, identity, bootstrap, frontier-attempt, observation,
  disposition, omission-risk, inventory, environment, and command-exit schemas.
- Per-request retained accepted body files, size/hash/request bindings, and
  offline parser/normalization replay report.
- No-network catching/cumulative test records and isolated-wheel equality.
- Exact M20B approval packet with command, commit, five routes, caps, roots,
  preflight, one-attempt rule, and explicit nonclaims.
- Fresh human authorization for only that packet.
- Immutable per-case live artifacts plus separate result/replay root.
- M20 result with decision table, inference-status table, post-run red team,
  terminal review, and refreshed reviewed M21 subplan.

## Required Checks, Tests, And Reviews

1. Replay the actual M19 route/request/V2 artifacts and the durable `14`-check
   closeout before M20 edits.
2. Run all M19 transport (`26`) and supervisor (`30`) tests after every
   transport/supervisor change.
3. Test exact route canonicalization, query keys/values, header denial,
   proxy/redirect/retry denial, byte/request/time/process/IPC/write caps, and
   fail-closed parser/programmer errors.
4. Test M17 bootstrap outcomes, confirmation-before-call, crash states,
   idempotent resume, stale/foreign/corrupt authority, and no automatic retry
   after indeterminate call.
5. Test exact DOI/arXiv/OpenAlex/title normalization, provider conflict,
   version-family rules, zero/multiple matches, and no topic-result seed
   promotion.
6. Exhaustively test the frozen request-state outcome table, including
   one-provider outage, cross-provider conflict, cap precedence, malformed or
   partial bodies, multiple rows collapsing to one identity, exact version
   family, weak/multiple topic candidates, and boundary-invalid precedence.
7. Test every frontier attempt has either observations or exactly one attempt
   risk; every observation has one compatible disposition; deterministic
   lexical truncation reconciles admitted, omitted-by-cap, duplicate,
   malformed, and unobserved-remainder counts; empty/unavailable outcomes
   remain visible.
8. Replay synthetic responses deterministically, including malformed,
   oversized, partial, conflicting, capped, empty, unavailable, write-failure,
   killed-worker, and manifest-last cases.
9. Test retained-body exclusive creation, cap, digest, inventory, request
   binding, no-log duplication, tamper/missing/extra rejection, and exact parser
   and normalized-output replay.
10. Run affected Phase 7 identity, Phase 8 frontier, M17 bootstrap, M19, full
   CLI, cumulative M16-M20, exact-script, static-network, and artifact
   reconciliation gates from an isolated installed wheel with
   `CUDA_VISIBLE_DEVICES=-1`.
11. Obtain one material plan review before M20A, one material code/packet review
   before M20B, and one terminal result review. Repair material findings within
   the allowlist; stop after five rounds on the same blocker.
12. Before M20B, verify exact successor commit/tree/wheel/member bytes,
    protected hashes, absent output root, no other M20 process, and fresh exact
    human approval. Run trusted/escalated because it uses external providers.
13. After M20B, replay accepted bodies locally without network, write the result, refresh M21
    from actual selected candidates and unresolved rights/source questions,
    review M21, and update controls.

## Forbidden Claims And Actions

- M20A authorizes only the reviewed local code/test/evidence allowlist with no
  network. `DO_NOT_EXECUTE_M20B`: do not fetch provider documentation, use DNS,
  call a provider, or launch the live matrix before the later reviewed packet
  and fresh exact approval.
- Never reuse the consumed M19 approval or rerun M19.
- Do not guess provider API semantics, silently change routes after results,
  or treat search results as exact identifier authority.
- Do not discard an accepted body used for selected identity/frontier
  authority, retain headers/credentials/exception text, or expose retained
  bodies outside the immutable M20 evidence root.
- Do not auto-select topic candidates from provider order, score, citation
  count, title plausibility, or the M19-derived OpenAlex case.
- Do not hide failed, empty, unavailable, ambiguous, capped, conflicting, or
  partial requests/frontiers.
- Do not treat metadata relations as verified citations or technical support.
- Do not access source, PDF, full text, arbitrary URLs, credentials,
  private/paid services, caches, or unlisted hosts.
- Do not rank providers/candidates statistically, change product defaults,
  mutate unrelated dirty work, push, release, or claim north-star completion.

## Exact Next-Phase Handoff Conditions

M21 may be refreshed only after M20A and M20B both close; every accepted body
hash and parser outcome, request,
identity attempt, frontier attempt, target observation, disposition, cap, and
omission risk replays exactly; at least one explicit real candidate has
lineage-valid selected authority; unresolved topic ambiguity and provider
outage remain visible; execution bytes are tied to an identified installed
commit; cumulative gates and terminal review pass; and M21 is refreshed with
the exact selected identifiers, domains, artifact types, rights questions,
caps, retention/privacy rules, parser boundaries, and separate source-access
approval requirement.

If no explicit candidate is selected, M20 writes
`BLOCKED_NO_SELECTED_REAL_CANDIDATE_AFTER_FROZEN_MATRIX` and M21 does not
start. Topic-bootstrap ambiguity alone is not that blocker when an exact
explicit-seed candidate remains valid.

## Stop Conditions

Stop before live execution for missing/contradicted official route semantics,
failed local catching/cumulative gates, wrong code authority, overlapping
protected work, corrupt M19 input, unrepresentable identity/disposition state,
unreviewed scope expansion, absent exact approval, or five-round material
nonconvergence.

During the frozen live matrix, stop further dispatch only for a true boundary,
harness, process, artifact, or authority invalidity. An empty, unavailable,
ambiguous, capped, conflicting, or irrelevant candidate/provider result is a
candidate outcome: record it and continue the remaining predeclared cases when
safe. Any launched matrix consumes the one-attempt budget; do not repair and
rerun live under the same approval.

## Exact Current Handoff

Begin M20A with an offline inventory of already-local provider documentation
and an exact implementation baseline check. If the required official route
contract is not already local, stop only that documentation-dependent slice
and request authority for a bounded documentation fetch; do not guess. No M20B
provider action is authorized.
