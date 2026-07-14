# Literature Survey M16 Remaining-Phases Repair Execution Plan

Date: `2026-07-12`
Status: `PHASE9_OMISSION_LINEAGE_REPAIR_ROUND1_EXECUTION_AUTHORIZED`

## Role And Execution Contract

Codex in the current visible conversation is supervisor, executor, and final
engineering gate owner. Claude Opus at maximum effort is a read-only reviewer.
Claude may identify defects but cannot edit files, execute experiments, make
omission or source-safety decisions, attest that a person performed a review, or
authorize live access, scientific claims, product capability, Git integration,
credentials, funding, model files, or release.

This plan repairs and executes the remaining local M16 program continuously from
the Phase 7 transition gate through Phase 10 local closeout. Phase 11 remains a
separate optional human live-access boundary. A fixable plan, implementation,
test, or review failure enters the repair loop; it is not a valid reason to stop.

## Current Authority And Exact Baseline

- Phases 0-8 are formally `PASSED`.
- The authoritative Phase 8 close record is
  `docs/plans/literature_survey_m16_phase8_snowball_omission_result_2026-07-12.md`
  with SHA-256
  `58f6357853dd39256eac7df2de716df93dc61d1fb1fe99d837e6f3135e8ecf06`.
- The Phase 8 implementation review verdict is
  `docs/reviews/literature_survey_m16_phase8_implementation_review_verdict_2026-07-12.md`
  with SHA-256
  `988747603a5614f031f7c3127d751cf27d9ef2f76e3bfcfc32dbc98842eac175`.
- Authoritative Phase 8 totals are `112` Phase 8 unit, `452` Phase 2-8
  compatibility, `545` combined M16, `749` full unit, `124` full CLI, and `6`
  exact survey-script tests; the Phase 8 UX validation passed with zero issues.
- The worktree is heavily dirty and much of M16 is untracked. Phase 0 hashes and
  per-phase manifests, not a clean Git-tree assumption, are the local baseline.
- The Phase 9 subplan is the active repaired candidate. Phase 10 remains a
  placeholder until refreshed from the actual Phase 9 close record.

Authoritative Phase 7 implementation hashes to preserve until a reviewed phase
explicitly authorizes a change:

| Artifact | SHA-256 |
| --- | --- |
| `src/research_assistant/survey/discovery_quality.py` | `e77da75af28a95a3534873636b783ede873452c639d71c351903bf087e202015` |
| `src/research_assistant/survey/build.py` | `a143bb46891f34f04c3a6bc485290ee0c9f8c18084f2f8257e4bb0c5158b0c2e` |
| `src/research_assistant/survey/source_intake.py` | `fc7c1981e2e9373d5ed2e4f2859c644b544812a6cb1bc964acc4cd1964c421e1` |
| `src/research_assistant/survey/supervisor.py` | `4a5eac36ebe0651958551d4109f4792df19ffe20f37ef17fa0bffb9de7afa7b7` |
| `src/research_assistant/survey/orchestrate.py` | `8d38875fab6d202b77d5c93ef4ad453ba8f37050d414b0378bda455f609fd039` |
| `tests/unit/test_literature_survey_m16_phase7.py` | `4c12c3a63bbb1632fad7be81a23576cd1b5fdcaf36da86bfd803bd15b0426370` |

## Program Goal

Close the remaining engineering gaps so the bounded command can advance one
mission through deterministic discovery, fixture-only frontier accounting,
exact human-gated review artifacts, conservative claim/source semantics, and a
lineage-valid hostile-review terminal state, or stop at an exact honest blocker.

Local completion means the hash-attested dirty workspace satisfies the declared
offline state machine. It does not mean the work is reproducible from Git
history. Git staging or committing is a later separate user-authorized action.

## Program Evidence Contract

| Field | Contract |
| --- | --- |
| Engineering question | Can the current M16 implementation deterministically represent bounded snowball observations, invalidate stale omission review, enforce source/claim evidence roles, and reach correct positive and adversarial offline terminal states? |
| Exact comparator | Passed Phase 7 V2 metadata/source-intake authority plus the current Phase 2-5 selected-artifact, review, reviewed-packet, hostile-review, and supervisor behavior. |
| Primary pass criterion | Phase 8-10 positive fixtures produce exact lineage-valid artifacts and every declared adversarial fixture stops at its exact veto before forbidden capability or readiness. |
| Hard vetoes | False readiness; invented access/provenance; stale or foreign review reuse; unbounded traversal; open risk ignored; model-only scientific authorization; metadata/availability promoted to technical support; unsafe source used by a dependent claim; live/provider/source/model/GPU action; outside write; protected user-file change. |
| Continuation vetoes | Unpreservable overlap with unknown user work; required weakening of Phase 1-7 authority; need for live/network/credential/private/paid/package/GPU/model/destructive action; repeatedly invalid environment; or five nonconvergent material review rounds for the same blocker. |
| Explanatory only | Candidate/frontier counts, traversal order, depth, citation counts, venue metadata, runtime, and broad-suite duration. |
| Not concluded | Literature or survey completeness, identity truth, ranking superiority, source safety in fact, truth of a reviewed claim, scientific correctness, human-review authenticity, prose quality, live reliability, Git reproducibility, product readiness, or release readiness. |
| Result artifacts | Refreshed subplans, phase results, manifests, JUnit/JSON/log artifacts, compact review packets/verdicts, execution ledger, reset memo, and final handoff. |

## Research Intent And Evidence Roles

| Field | Value |
| --- | --- |
| Main question | Whether the evidence state machine preserves observation, review, and support boundaries through local end-to-end execution. |
| Mechanism under test | Immutable V2 metadata authority, bounded frontier projection, selected artifact-set invalidation, exact decision coverage, source-status binding, claim-type/support-class compatibility, and hostile review. |
| Expected failure mode | A plausible current file or free-text review row is accepted even though its observation, source version, reviewer authority, or selected artifact lineage changed. |
| Promotion criterion | Exact fixture predicates and adversarial invariants, not counts or descriptive metadata. |
| Promotion veto | Any forbidden evidence promotion or false readiness. |
| Continuation veto | Only a condition listed in the program evidence contract, not rejection of a current implementation candidate. |
| Repair trigger | Focused failure, material `REVISE`, missing schema field, weak authority binding, stale acceptance, cyclic reopening, or downstream mismatch. |
| What must not be concluded | Passing synthetic fixtures establishes real human review, source safety, claim truth, coverage, science, or production behavior. |

The six scholarly ledgers remain separate throughout:

1. source support;
2. citation and venue metadata;
3. backward snowball;
4. forward snowball;
5. claim support; and
6. omitted-paper and reviewer-risk register.

Citation/venue counts and metadata relations are navigation evidence only.
Technical support requires the support-class predicates in Phase 9. Every
selected included source must also appear in the exact support-allowed
dependency union; Phase 9 has no authority to silently exclude an unused source.

## Skeptical Pre-Execution Audit

The initial remaining-phase drafts fail execution audit for these material
reasons, and this plan corrects them before product edits:

1. Phase 8 projected existing citation-map members but did not define an
   observation authority, traversal state, access provenance, exact caps,
   per-candidate dispositions, or stale-review invalidation.
2. The public-source packet does not copy `metadata_provenance.json`. Phase 8
   must not invent access dates from packet creation time. The canonical path
   will replay the V2 metadata authority already embedded in the validated
   mission source-intake status and read only its exact hash-attested children.
3. Machine frontier dispositions and reviewed human omission decisions were
   conflated. They are separate authority layers below.
4. Phase 9 named six claim states while current review code treats three as
   positive support classes. The plan now separates supporting classes from
   context/blocker states and binds each supporting class to an allowed claim
   type.
5. `model_reviewed_passed` currently can contribute to readiness. Model review
   is advisory and cannot authorize scientific support. New readiness requires
   a declared human-reviewed decision; synthetic tests must label that fact and
   cannot claim a real person reviewed anything.
6. Current source-safety decisions contain free-text evidence but no exact
   status-observation artifact/version/hash binding. Phase 9 adds one.
7. Legacy offline replay can set `ready_for_prose` from packet shape. Phase 9
   removes this authority and Phase 10 tests every exposed path.
8. Phase 10 did not specify exact terminal codes, tripwires, commands, timeouts,
   or crash cases. This plan requires them before the E2E run.
9. Hash-attested workspace reproducibility is not Git-history reproducibility.
   Local closeout records `GIT_INTEGRATION_PENDING` unless separately authorized.
10. The first reviewed Phase 9 plan proposed a quarantine-closure join that is
    unreachable in canonical production state. Phase 8 quarantine observations
    are unresolved/conflicting targets outside the included available-source
    universe, while V3 source authority covers only included available records.
    The repaired Phase 9 removes closure/reclassification authority, retains
    quarantine as an open blocker, and requires exact selected-source/dependency
    equality until a future queue-backed human omission authority is designed.
11. The first frozen Phase 9 implementation review found that omission-set
    chain replay validates every retained historical set against the newly
    selected queue. That makes an intact queue-A decision set prevent a forced
    queue-B import, even though append-only history must retain stale authority.
    The repair separates historical self-replay against each set's committed
    artifact-set queue from current-head compatibility. It keeps corrupted
    history, missing predecessors, forks, pointer rollback, and noncurrent
    selected authority fail-closed, and requires queue-A to queue-B import plus
    corrupt-history catching tests before Phase 9 can close. Because the normal
    artifact-set validator deliberately replays V2 coverage against active
    source-intake inputs, Phase 9 may add a retained-set validation mode that
    skips only that external-current replay while preserving intrinsic artifact
    manifest, path, byte, schema, coverage, queue-semantic, mission, and genesis
    checks. It cannot authorize a retained set as current.
12. If a complete stale queue-A successor was renamed before its pointer update
    and queue B becomes current, a forced queue-B complete import may append
    after that one intrinsically valid immediate stale orphan and select only
    queue B. A current-lineage immediate orphan still recovers only on the exact
    same-byte retry and cannot be superseded. No-force stale supersession,
    deeper pointer divergence, fork, or corruption remains a hard failure. This
    is a narrow supersession rule, not authorization of the orphan or rollback
    acceptance as current evidence.

Pre-mortem:

- A frontier could look complete because all fixture rows were consumed while
  the provider was unavailable. Catching test: `empty_observed`, `not_observed`,
  `provider_unavailable`, `capped`, and `depth_excluded` are distinct and none
  authorizes completeness.
- Review could appear invalidated only because timestamps changed. Catching
  test: observation timestamps are source metadata inputs; derived artifact
  creation time is excluded from semantic identity.
- A source could be called safe because an allowed evidence-type string was
  supplied. Catching test: `checked_clear` requires an exact selected status
  observation whose paper/version/source/hash/date fields replay.
- An implementation benchmark could support a mathematical claim. Catching
  test: the claim-type/support-class compatibility matrix rejects it.
- A positive synthetic mission could be reported as real human-reviewed prose
  readiness. Catching test: validation result labels synthetic decisions and
  final nonclaims prohibit authenticity or scientific conclusions.
- Broad tests could obscure a focused regression or stall indefinitely.
  Catching action: focused gates first, bounded quiet logs, structured JUnit,
  and explicit incomplete evidence for any timed-out unrelated group.

Audit disposition: `PASSED_AFTER_REWRITE_PENDING_READ_ONLY_REVIEW`. No Phase 8
product or test file may be edited until this plan and the refreshed Phase 8
subplan converge.

## Common Visible Repair Loop

For every material plan and implementation gate:

```text
PRECHECK
  verify preceding close record, hashes, allowlist, and boundary
  restate exact evidence contract and run skeptical audit

EXECUTE_MINIMAL
  implement the smallest catching slice
  use fixture-only capabilities and preserve unrelated work

LOCAL_GATES
  run focused catching tests first
  run affected compatibility and boundary tests
  preserve bounded logs and structured outputs

ASSESS
  compare exact artifacts with primary criterion and hard vetoes
  write or refresh the phase result

NEXT_PLAN_GATE
  refresh the next subplan from actual hashes and artifacts
  audit consistency, correctness, feasibility, artifact coverage,
  scholarly-ledger coverage, and boundary safety

READ_ONLY_REVIEW
  submit compact self-contained packets to Claude Opus/max when policy permits
  otherwise use a fresh independent Codex read-only reviewer and record the
  downgraded provenance; accept only a usable material VERDICT: AGREE

REPAIR
  patch the same plan/code/result visibly for fixable findings
  rerun the smallest catching check plus affected boundaries
  repeat review, maximum five rounds for the same blocker

ADVANCE
  close the current phase only when its result and next plan both pass
```

If a Claude material review times out or returns no usable verdict, run a tiny
trusted `CLAUDE_PROBE_OK` probe. A healthy probe means the packet/prompt is too
broad and must be narrowed. Two failed trusted health probes permit a fresh
Codex read-only review with weaker provenance recorded. A policy rejection of
repository export is final for this program and must not be probed or retried;
it immediately selects fresh Codex fallback. A usable independent Codex
`VERDICT: AGREE` satisfies the local engineering review gate with downgraded
provenance, but is not represented as Claude or primary-model agreement and
cannot authorize any human, live, scientific, product, release, or Git boundary.

## Phase R0 - Control Reconciliation And Plan Gate

### Objective

Create one truthful control state and obtain plan agreement before product
edits.

### Required Artifacts

- This controlling repair plan and its compact review packet/verdict.
- Refreshed Phase 8 subplan with exact schemas, allowlist, commands, and handoff.
- Corrected master phase-index reference to the dated Phase 7 result.
- Master, runbook, ledger, stop-handoff, and reset-memo status set to
  `PHASE7_IMPLEMENTATION_PASSED_PHASE8_PLAN_REVIEW_ACTIVE` until review passes.
- Pre-edit manifest with current hashes of every proposed Phase 8 file and all
  protected dirty files.

### Required Checks

- Every required subplan field is present.
- All referenced paths exist or are explicitly declared future artifacts.
- Phase 7 authoritative hashes and test totals reconcile.
- `git diff --check` passes.
- Compact Claude plan review checks baseline, schema, invalidation, stop
  conditions, artifact coverage, evidence roles, feasibility, and boundaries.

### Exit And Handoff

After primary plan agreement, change Phase 7 result/subplan to `PASSED`, append
the formal transition record, and begin Phase 8. A fixable plan finding loops in
R0. Only a declared continuation veto stops.

## Phase 8 - Fixture-Only Frontier Authority And Omission Closure

### Phase Objective

Replace projection-only snowball ledgers with deterministic, versioned,
fixture-only backward/forward observation and traversal authority. Every
material frontier outcome must produce either a retained candidate or an exact
omission risk before review-queue construction. Empty, unavailable, capped, and
unobserved frontiers remain distinguishable and never imply completeness.

### Entry Conditions

- R0 and the refreshed Phase 8 plan passed primary read-only review.
- Phase 7 is formally `PASSED` and its V2 authority hashes reconcile.
- The canonical mission source-intake status replays the complete V2 metadata
  authority with exact `artifact_rows`, including `identity_resolution.json`,
  `relevance_ranking.json`, `citation_map.json`, and
  `metadata_provenance.json`.
- Phase 2 selected-artifact lineage and Phase 3 exact decision coverage remain
  authoritative.

### Canonical Input And Provenance Contract

The canonical supervisor calls coverage construction with a validated V2
metadata context derived from `validate_mission_source_intake`, never a raw
caller-supplied path. The context contains:

- mission ID, fingerprint, and anchor generation;
- metadata-authority SHA-256 and exact sorted artifact rows;
- exact metadata root;
- replayed metadata access timestamp and provider statuses;
- canonical V2 candidate, identity, relevance, citation, and provenance
  payloads.

Every referenced child must be the exact regular non-symlink child named in the
metadata authority and must match its path/hash/size row. Phase 8 reads no live
provider, source, PDF, or full-text endpoint. The standalone legacy coverage
composer remains conservative: without validated V2 context it can project
legacy ledgers but cannot emit a V2 frontier-complete status.

Phase 7 provider statuses and query provenance are authoritative only for the
exact route they record. In particular, a `seed_resolution` or `topic_search`
route is not evidence that a backward-reference or forward-citation query was
attempted for any origin paper. A query-backed frontier attempt may be
`empty_observed` only when the V2 authority contains an exact direction-,
origin-, provider-, and query-kind-specific transcript for that attempt. The
initial recorded-relation projections may be `observed_results` only when exact
relation edges exist; otherwise they emit `not_observed`. Phase 8 must not
relabel a generic route as a frontier query attempt. Embedded
`referenced_works` may produce target-bearing candidate observations only under
the exact metadata-record provenance that carried those identifiers; they do
not synthesize a separate successful query attempt or establish that the
origin's complete reference list was observed.

The required attempt universe is generated exactly once from a closed traversal
policy and recorded in both ledgers:

1. depth-one origins are the exact sorted non-null `selected_paper_id` values in
   the replayed seed-resolution rows;
2. for depth greater than one, origins are the exact sorted stable-paper-ID
   targets whose prior-depth disposition is `include`; no unresolved,
   quarantined, capped, omitted, or merely inspected target becomes an origin;
3. every origin is crossed with both configured directions through one closed
   mechanism each: backward `recorded_reference_projection` and forward
   `recorded_reverse_reference_projection`, both carried by exact OpenAlex
   identifier relations in the replayed V2 identity/citation authority;
4. each `(origin, direction, depth, mechanism, provider)` tuple occurs exactly
   once, even when no matching relation exists; and
5. traversal stops only at the exact persisted depth/node/observation caps, with
   all excluded target observations retained as `depth_excluded` or `capped`.

For the two projection mechanisms, exact recorded relation edges may yield
`observed_results`; absence of edges always yields `not_observed`, never
`empty_observed` or `provider_unavailable`. A projection reuses the exact
carrier-record query provenance only as provenance for a target observation,
not as evidence of a citation-query attempt. `empty_observed` and
`provider_unavailable` are reserved for a future exact direction-specific query
observation authority. Such authority is outside the initial Phase 8 input
surface; if later added, it must be an immutable mission/metadata-authority-bound
envelope included in artifact-set identity, invalidation, crash tests, and the
reviewed allowlist before it can affect canonical output.

### Closed Frontier Schemas

Add versioned backward/forward ledger V2 schemas. Each ledger records exactly:

- schema, status, topic, direction, and observation-authority digest;
- source metadata root and access timestamp;
- provider-status projection and traversal policy;
- ordered observations, candidate dispositions, and summary counts;
- evidence policy, next actions, and nonclaims.

The schema separates frontier/query attempts from candidate observations. A
frontier attempt may legitimately return no target; a candidate observation
always names a target. No sentinel or invented paper identity is permitted.

Each frontier-attempt row records exactly:

- deterministic `frontier_attempt_id`;
- direction and origin stable paper ID;
- provider and closed `mechanism_kind`;
- nullable `query_kind` and `matched_query_provenance`, both null for the two
  initial projection mechanisms;
- exact sorted `carrier_query_provenance` routes for recorded-relation
  projections, never interpreted as a frontier query transcript;
- source artifact role/digest and observed-at metadata timestamp;
- requested depth and cap;
- attempt status and exact reason;
- ordered candidate-observation IDs, which may be empty;
- `derived_attempt_risk_id`, which is `null` for `observed_results` and an exact
  risk ID for every other attempt status; and
- `claim_support_allowed=false` and
  `literature_completeness_allowed=false`.

Closed frontier-attempt statuses are:

- `observed_results`;
- `empty_observed`;
- `not_observed`;
- `provider_unavailable`; and
- `malformed_blocked`.

`empty_observed` requires an exact successful recorded attempt with zero
candidate observations. `not_observed` means no authorized attempt exists.
Neither status means the literature frontier is empty in fact. Unavailable and
malformed attempts remain blockers.

The two initial projection mechanism kinds are not query kinds. The only future
query kinds eligible to establish a successful query attempt are closed,
direction-specific kinds declared by a selected observation authority:
`backward_reference_observation` and `forward_citation_observation`. Existing
Phase 7 `seed_resolution` and `topic_search` routes are ineligible for that
purpose. Unknown or generic query kinds fail closed rather than being inferred
from relation names or returned records.

Attempt validation is total:

| Attempt status | Candidate-observation IDs | Derived attempt-risk IDs | Required route evidence |
| --- | --- | --- | --- |
| `observed_results` | Nonempty, unique, sorted, and exact children of this attempt | Empty; candidate rows fully account for the attempt and every non-`include` candidate derives its own risk | Exact recorded relation projection with null query route, or future exact matched direction/origin query transcript |
| `empty_observed` | Empty | Exactly one `blocked_source_or_frontier` risk | Future selected observation authority with an exact successful direction/origin query and recorded zero results; forbidden for projection mechanisms |
| `not_observed` | Empty | Exactly one `blocked_source_or_frontier` risk | Required projection tuple has no exact relation, or a future query tuple has no selected observation; `matched_query_provenance=null` |
| `provider_unavailable` | Empty | Exactly one `blocked_source_or_frontier` risk | Future selected observation authority with an exact direction/origin provider-status route showing unavailable/failed outcome; forbidden for generic Phase 7 status |
| `malformed_blocked` | Empty | Exactly one `blocked_source_or_frontier` risk | Exact provider-status or input-artifact route plus bounded parse/schema error code |

Attempt counts, ID unions, direction/origin/provider/mechanism/query fields, and
derived risk cardinality must replay exactly. Projection attempts require null
query fields and nonempty carrier provenance only when observations exist;
query-backed attempts require a direction-specific query kind and forbid
carrier provenance. A candidate observation may belong to exactly one canonical
attempt after duplicate relation normalization. Unknown, duplicate,
cross-attempt, or status-incompatible IDs fail closed.

An `observed_results` attempt never derives an additional attempt-level risk,
even when none of its candidates is retained. In that case every candidate is
accounted for by its exact non-`include` candidate risk. Attempt-level risks are
reserved for target-free attempt statuses, preventing duplicate risk authority.

Each candidate-observation row records exactly:

- deterministic `observation_id`;
- direction;
- origin stable paper ID;
- target stable paper ID or normalized unresolved external ID;
- relation and provider;
- mechanism kind, nullable query kind/matched query route, and exact carrier
  query-provenance routes under the same projection-versus-query rules as its
  parent attempt;
- source artifact role/digest;
- observed-at metadata timestamp;
- depth and deterministic traversal order;
- cap/depth state;
- candidate-observation status;
- classification/relevance signals;
- frontier disposition and reason;
- `claim_support_allowed=false` and
  `literature_completeness_allowed=false`.

Closed candidate-observation statuses are:

- `observed`;
- `capped`;
- `depth_excluded`;
- `identity_conflict`;
- `source_blocked`.

Closed machine dispositions are:

- `include`;
- `inspect_next`;
- `omit_with_reason`;
- `quarantine`; and
- `blocked_source_or_frontier`.

Candidate status and disposition compatibility is total:

| Candidate-observation status | Allowed machine disposition(s) | All other combinations |
| --- | --- | --- |
| `observed` | `include`, `inspect_next`, or `omit_with_reason`, selected by the exact recorded classification predicate | forbidden |
| `capped` | `inspect_next` | forbidden |
| `depth_excluded` | `inspect_next` | forbidden |
| `identity_conflict` | `quarantine` | forbidden |
| `source_blocked` | `quarantine` | forbidden |

`blocked_source_or_frontier` is an attempt-derived risk disposition only; it is
forbidden on a target-bearing candidate observation. `include` produces no
omission risk. Every other candidate disposition produces exactly one risk whose
source observation ID and machine disposition match exactly.

Machine dispositions are not reviewed omission decisions. Exact mapping:

| Machine disposition | Queue/review consequence |
| --- | --- |
| `include` | Candidate retained; no closure implied. |
| `inspect_next` | Exact open risk requiring `must_inspect`. |
| `omit_with_reason` | Exact risk closable only by reviewed `acceptable_omission` or `out_of_scope`. |
| `quarantine` | Exact open risk, normally `blocked_pending_source`; Phase 9 may diagnose source status but cannot close or reclassify it. |
| `blocked_source_or_frontier` | Exact open risk unless reviewed closed for the current recorded scope; never completeness. |

Every candidate observation has exactly one disposition. A target-free frontier
attempt deterministically derives one `blocked_source_or_frontier` risk instead
of inventing a candidate disposition.
Risk authority is one-to-one: every non-`include` candidate observation derives
one unique risk ID, and every target-free attempt derives one different unique
risk ID. No two attempts or observations may share a risk, and no risk may name
more than one source attempt/observation. Human reviewers may choose identical
decision text for related risks, but each current queue item still requires its
own exact decision row. Tests reject shared, duplicated, missing, cross-source,
or recomputed risk IDs.

### Total Omission Transition Matrix

The selected risk records its machine disposition. Review validation applies
this total transition table; a `forbidden` cell is rejected rather than silently
normalized to another decision.

| Machine disposition | `acceptable_omission` | `must_inspect` | `expand_scope` | `blocked_pending_source` | `out_of_scope` |
| --- | --- | --- | --- | --- | --- |
| `include` | forbidden: no omission risk exists | forbidden | forbidden | forbidden | forbidden |
| `inspect_next` | forbidden until new observation changes the disposition | valid, open | valid, open and regeneration required | forbidden until a source-blocked observation changes the disposition | forbidden until new reviewed classification changes the disposition |
| `omit_with_reason` | valid, closed for current recorded scope | valid, open | valid, open and regeneration required | valid, open | valid, closed for current recorded scope |
| `quarantine` | forbidden | forbidden | valid, open and regeneration required | valid, open pending a future separately reviewed queue-backed authority | forbidden |
| `blocked_source_or_frontier` | valid only with exact recorded-scope boundary rationale; closed for that scope | valid, open | valid, open and regeneration required | valid, open | valid only with exact scope basis; closed for that scope |

Closed means `reviewed_closed_for_current_scope`, always with
`literature_completeness_allowed=false`. Open means readiness remains false and
an exact next action is required. A closed blocked-frontier decision produces a
hostile-review warning and never changes the underlying attempt status.

`expand_scope` is a decision, not new observation authority. It never invokes a
provider or clears the current risk. The selected set remains blocking until
separately authorized fixture/recorded observations are supplied, coverage is
recomputed, and a new artifact set is selected. Selection of that set makes the
old `expand_scope` decision and all sibling sidecars stale. Recomputing with
identical inputs cannot satisfy `expand_scope` and remains open. Tests cover
every matrix cell, both closure predicates, and the old-to-new set transition.

Phase 8 stores omission decisions as immutable complete decision sets below
`reviewed_omissions/decision_sets/od-<semantic-sha256>/`, with a manifest written
last and one atomic `reviewed_omissions/DECISION_CURRENT` pointer. The set digest
binds the selected artifact-set ID, queue semantic hash, exact full decision
envelope, and decision bytes. Every selected set must exactly cover the current
omission-risk queue; partial row replacement is forbidden. Multiple historical
sets may coexist, but only the exact pointer target is current. Conflicting set
bytes, multiple/invalid pointer targets, partial staging, symlinks, unexpected
children, or pointer crash residue fail closed. Phase 8 tests manifest and
pointer crash points, same-set replay, full-set replacement, and stale sibling
rejection.

A Phase 8 quarantine risk permits only `blocked_pending_source` (or open
`expand_scope`) in the current program. The later reachability audit found no
canonical join from these unresolved/conflicting frontier targets to the
included available-source V3 authority. Phase 9 therefore preserves the
selected immutable omission set and rejects any replacement
`acceptable_omission`, `out_of_scope`, `pending_exact_source_join`, or
closure-shaped source-reference fields. A future repair may change this matrix
only after adding and reviewing separate queue-backed human omission and, where
needed, scope-reclassification authority.

### Deterministic Traversal Contract

- Traverse breadth-first by depth, then origin stable ID, relation, provider,
  target stable/external ID, and observation ID.
- Backward and forward depth are exactly the persisted coverage policy, initially
  one; Boolean, negative, missing, or noninteger caps/depth fail closed.
- Apply global node cap and per-direction observation cap before enqueuing the
  next depth. Every excluded row remains visible as `capped` or
  `depth_excluded`.
- Exact duplicate observations collapse after canonical normalization while
  retaining the complete sorted provenance route set.
- Conflicting rows never merge silently and produce `identity_conflict`.
- Input permutation, duplicate provider order, and artifact creation time do not
  alter semantic bytes or selected artifact-set identity.
- Access timestamp is copied from replayed V2 metadata provenance and is part of
  semantic authority; coverage artifact creation time is not.

### Invalidation Contract

Any change to observation bytes, access timestamp, provider/query route, edge,
identity, cap, depth, traversal policy, classification, disposition, or risk
mapping changes coverage semantics and selects a new immutable artifact set.
All prior queue decisions, reviewed sidecars, merge, reviewed packet, hostile
review, and readiness artifacts then fail selected-lineage validation. An
unchanged replay selects the same set and performs zero writes to that set.

Phase 9 safety outcomes do not mutate Phase 8 coverage or omission authority in
place. A true scope expansion regenerates coverage and review authority; an
ordinary safety decision cannot close an unchanged quarantine risk.

### Required Product And Evidence Artifacts

- New pure `src/research_assistant/survey/frontier_expansion.py`.
- Narrow V2 changes to `coverage_ledgers.py`, `artifact_lineage.py`, and
  `orchestrate.py`.
- Narrow Phase 8 transition enforcement in `omission_review.py`,
  `review_decisions.py`, and `reviewed_merge.py`; these files may change only for
  the total machine-disposition/decision matrix, open/closed derivation, exact
  risk join, and stale selected-set rejection.
- Narrow downstream validation changes only where V2 coverage schemas require
  them in `reviewed_packet.py` and `hostile_review.py`.
- `tests/unit/test_literature_survey_m16_phase8.py` plus focused compatibility
  additions.
- `docs/validation/literature_survey_m16_phase8_2026-07-12/` containing pre-edit,
  change/run manifests, JUnit, static audits, tripwire results, and reconciliation.
- Phase 8 result, compact implementation review, refreshed Phase 9 subplan, and
  Phase 9 plan review.

### Required Checks

1. Positive backward/forward fixtures preserve the exact Phase 7 closed roles
   (`seed`, `direct_method`, `adjacent_method`, `major_citing_work`, and
   `backward_lineage_candidate`) and relation directions. Titles/scenarios may
   represent foundational, competitor, correction, or recent works, but those
   words are not synthesized as authority labels. This is fixture behavior, not
   real recall evidence.
2. Every closed frontier-attempt status, candidate-observation status, machine
   disposition, status/disposition cell, attempt-cardinality row, and omission-
   transition matrix cell has a catching test.
3. Empty, unavailable, capped, depth-excluded, conflict, and malformed cases
   remain visible and cannot imply completeness.
4. Exact negatives prove that Phase 7 `seed_resolution` and `topic_search`
   routes cannot become successful backward/forward attempts; missing
   direction/origin-specific routes produce `not_observed`, while embedded
   reference identifiers retain their real carrier provenance without
   synthesizing a query attempt.
5. Exact attempt-universe tests cover all required origin/direction/depth/
   mechanism/provider tuples once, recursive included-origin derivation, and
   exclusion of unresolved/quarantined/capped/omitted targets.
6. Every non-`include` observation and target-free attempt has its own risk;
   shared/many-to-one or cross-source risk IDs are rejected.
7. Permutation, duplicate, replay, cap, and depth tests are byte-deterministic.
8. Changed observations or policy stale every old reviewed artifact; unchanged
   replay retains the same selected set.
9. Exact queue-risk joins reject missing, duplicate, unknown, stale, or foreign
   decisions.
10. Tampered, moved, symlinked, noncanonical, invalid UTF-8/JSON, wrong-schema,
   and unexpected metadata/coverage children fail closed.
11. Network/provider/source/model tripwires prove zero calls.
12. All six scholarly ledgers remain separate and preserve their nonclaims.
13. Focused Phase 8, Phase 2-7 compatibility, combined M16, full unit, full CLI,
    exact scripts, UX, compilation, JSON/JUnit, writer-table, protected hashes,
    provider-transport AST audit, diff hygiene, and NUL-safe reconciliation pass.

Every Python/test command sets `CUDA_VISIBLE_DEVICES=-1` before import.

### Phase 8 Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Can bounded recorded backward/forward observations produce deterministic selected coverage and exact omission risks without inventing completeness? |
| Baseline | Current projection-only V1 ledgers derived from `citation_map.json`. |
| Primary criterion | Exact positive and adversarial fixture artifacts satisfy schema, traversal, disposition, risk, invalidation, and downstream gates. |
| Hard vetoes | Invented provenance/date; unbounded or unstable traversal; omitted observation; empty/unavailable called complete; stale decision accepted; live call; false evidence/readiness. |
| Explanatory only | Counts, depth, order, citation metadata, and runtime. |
| Not concluded | Real coverage, recall, omission correctness, source safety, claim support, science, or live reliability. |

### Phase 8 Handoff

Phase 8 closes only after local gates, a primary implementation agreement, its
result, and a reviewed refreshed Phase 9 subplan pass. Phase 9 receives the
selected coverage/queue artifact set, exact open or current-scope-closed risks,
stable paper identities, source-intake records, six separate ledgers, and no
claim of source safety, support, completeness, or human judgment.

## Phase 9 - Source-Safety And Claim-Evidence Authority

### Phase Objective

Bind source-safety decisions to exact status observations, bind supported claims
to allowed claim types and current evidence, prevent model-only scientific
authorization, and remove all legacy offline-replay prose-readiness authority.

### Entry Conditions

- Phase 8 result and implementation review pass.
- The refreshed Phase 9 subplan is reviewed against actual Phase 8 hashes.
- The selected coverage and queue validate under the active mission lineage.
- Phase 6 current source records and Phase 4 reviewed-packet replay remain
  authoritative.

### Reviewer-Authority Contract

New reviewed claim decisions use one of:

- `human_reviewed_passed`: may authorize the recorded support predicate;
- `model_reviewed_advisory`: cannot set `claim_support_allowed`; or
- `rejected_or_blocked`: cannot support prose.

Legacy `reviewed_passed` and `model_reviewed_passed` remain readable only where
needed to report incompatibility; they cannot authorize a new canonical ready
packet. The system records a reviewer label but cannot authenticate that a
person performed the review. Tests use explicitly synthetic fixture labels and
must not claim actual human authorization.

New reviewed source-safety decisions independently use one of:

- `human_reviewed_status`: may derive `checked_clear` only from an exact
  `checked_clear_for_recorded_checks` status observation;
- `model_reviewed_advisory`: cannot derive `checked_clear` or
  `claim_support_allowed`;
- `legacy_ambiguous_review`: readable only to report incompatibility and cannot
  clear a source; or
- `rejected_or_blocked`: cannot clear a source.

Claim and source-status reviewers are separate recorded roles. A human-shaped
claim decision cannot upgrade a model-only, legacy, missing, or unauthenticated
source decision. The system records declared role/label/time and exact decision
bytes but cannot authenticate human identity. Synthetic Phase 9/10 fixtures
declare themselves synthetic even when exercising `human_reviewed_status`;
passing proves only the state transition.

### Claim-Type And Support-State Matrix

Supporting classes:

| Support class | Allowed claim type | Required exact evidence |
| --- | --- | --- |
| `primary_technical_support` | `paper_technical` | Current paper IDs, current reconstructed technical anchors, checked-clear dependent source status, exact reviewed decision. |
| `project_derivation` | `project_mathematical_derivation` | Mission-contained derivation path/hash/ID and exact review; no claim that tooling alone proves it. |
| `implementation_evidence` | `implementation_behavior` | Mission-contained code/test/result artifact path/hash and exact review. |

Nonsupporting states are `survey_context_only`, `source_gap_blocker`, and
`quarantined`. They remain visible in claim-support/evidence-classification
ledgers but always have `claim_support_allowed=false`. Context cannot support a
technical claim; source gaps and quarantine block dependent claims.

### Source-Status Observation Authority

The source-safety importer is the sole Phase 9 producer of immutable,
fixture-only status-observation and reviewed-source-decision sets. The reviewed
source envelope contains an exact `observation_set` plus a complete exact
decision envelope. Before accepting decisions, the importer:

1. validates the active mission, selected artifact-set ID, queue semantic hash,
   current source-record digests, and closed observation schemas;
2. canonicalizes the observation set and computes
   `ss-<sha256(schema + mission/fingerprint/anchor + selected artifact set +
   queue bindings + source-intake bindings + source-record digests + exact
   observations + fixture/nonclaim fields + predecessor observation-set
   ID/manifest hash)>`, with remaining identity details controlled by the
   reviewed Phase 9 subplan;
3. writes a manifest-last immutable set below the canonical mission
   `reviewed_source_safety/observation_sets/` root and atomically selects it with
   `reviewed_source_safety/OBSERVATION_CURRENT`; and
4. canonicalizes the complete source-decision set and computes
   `sd-<sha256(schema + mission/fingerprint/anchor + selected artifact set +
   queue bindings + selected observation-set ID/manifest hash + complete
   decision envelope and normalized-decision hashes + predecessor decision-set
   ID/manifest hash)>`, with remaining identity details controlled by the
   reviewed Phase 9 subplan;
5. writes it manifest-last below
   `reviewed_source_safety/decision_sets/<sd-id>/`, including
   `reviewed_source_safety.json`, and atomically selects it with
   `reviewed_source_safety/DECISION_CURRENT`; and
6. binds every decision row to the selected status-set ID/manifest hash and exact
   observation IDs/digests.

Standalone or noncanonical imports may validate but cannot become canonical
mission readiness authority. Both current pointers contain exact set ID and
manifest hash. Every selected decision set exactly covers the current source-
safety queue; partial row replacement is forbidden. Historical observation and
decision sets may coexist, but only the exact pointer targets are current.
Existing identical sets replay byte-for-byte. Partial, conflicting, symlinked,
unexpected, wrong-parent, multiple-target, or pointer-mismatch residue fails
closed without overwrite. Phase 9 adds crash hooks/tests for observation and
decision staging, manifest commit, pointer replacement, stale sibling selection,
and recovery validation.

Each versioned fixture-only status-observation row covers exactly one current
immutable `source_safety` queue item and contains:

- stable paper ID and exact DOI/arXiv/OpenAlex aliases;
- observed source/publication version;
- non-null current source-record path/hash/size;
- status source and evidence class;
- source-provided access timestamp;
- exact checks performed;
- outcome and notices;
- observation digest and nonclaims.

Closed outcomes are `checked_clear_for_recorded_checks`, `retracted`,
`withdrawn`, `expression_of_concern`, `major_erratum_or_corrigendum`,
`version_conflict` and `quarantined`.

Unavailable Phase 6 outcomes have no immutable source-safety queue item and
cannot enter V3 through an invented target. They remain exact source-intake/
workflow/omission blockers and cannot be closed in Phase 9. Merge writes and
binds `reviewed_source_outcome_blockers.json`; any current unavailable outcome
produces blocker code `unavailable_source_outcome`, merge status
`reviewed_evidence_blocked_unavailable_source_outcome`, and a program-wide
packet/hostile/readiness veto. The Phase 9 subplan defines the exact artifact
schema and replay contract.

A reviewed source decision must reference the exact observation digest and
paper/version identity. `checked_clear` is derived only from
`checked_clear_for_recorded_checks`; it means no declared blocker was found in
that observation, not universal safety. Free-text evidence type/source alone is
insufficient.

Changing any observation, status source/date/check, paper/version/source-record
digest, selected artifact set, or reviewed source decision selects a different
status or decision set. Old source decisions, claim-evidence joins,
reviewed merge, reviewed final packet, hostile review, and readiness then fail
current status-set/decision-set validation. Claim decisions bind declared source
dependencies but are not rewritten; the current merge re-evaluates them against
the newly selected status and source-decision sets and refuses stale or unsafe
dependencies.

### Dependency-Scoped Safety And Omission Join

- The exact Claim V3 envelope, conditional row keys, immutable selected output,
  set tree, sidecar/manifest/pointer schemas, identity projection, and
  predecessor/head rules are defined by the Phase 9 subplan. Every
  supporting claim decision includes an exact sorted
  `source_dependencies` list, including an explicit empty list, plus a
  dependency-manifest root and graph digest. Each dependency names stable/source
  paper IDs, exact identifier/version/source-record hash, and dependency role,
  but not a transient source selector. Current observation/decision selectors
  are re-joined by merge.
- `primary_technical_support` direct dependencies must equal its cited paper-ID
  set. `project_derivation` and `implementation_evidence` use a canonical local
  evidence manifest containing direct paper dependencies and referenced local-
  evidence manifest IDs. The validator computes the complete transitive paper
  dependency closure, rejects cycles, duplicates, missing/foreign manifests,
  undeclared direct edges, and any mismatch with the claim decision's declared
  closure.
- An explicitly empty dependency closure is allowed only when both the local
  evidence manifest and reviewed claim decision declare it. This is a checked
  declaration, not proof that the artifact has no hidden intellectual source;
  the nonclaim remains explicit.
- Every paper in the complete declared dependency closure must be current and
  have an allowed source decision. Every `paper_technical` dependency requires
  human-shaped checked-clear status for the recorded checks.
- Context-only claim rows may remain visible in a blocked packet, but a source
  used only for context cannot participate in a Phase 9 ready mission because
  no separate reviewed non-support source-accounting authority exists.
- Quarantined/retracted/conflicting papers may appear only in quarantine or
  exclusion explanations and cannot support claims.
- Every selected included-source tuple must equal one tuple in the union of
  dependencies declared by support-allowed claims. A checked-clear but unused
  included source emits `unused_included_source`; a used tuple absent from
  selected source authority emits `missing_selected_source_dependency`.
- A `quarantine` frontier disposition remains open throughout Phase 9. No Phase
  9 source decision, title/alias match, or raw omission decision can close or
  reclassify it.

The previously planned quarantine closure was found unreachable. Phase 8 emits
quarantine for unresolved/identity-conflict frontier targets outside the
included available-source authority; V3 source decisions cover only included
available records. Phase 9 therefore writes a source-accounting diagnostic,
not a closure artifact. It binds current candidate observations, source records
and versions, source observation/decision selectors, claim selector, omission
selector, exact dependency union, unused sources, missing dependencies, and open
quarantine risks. Selector or byte changes invalidate all descendants.

Any future unused-source exclusion requires a separate immutable human omission
adjudication bound to the exact candidate observation, stable/source identity,
version, selected source decision, and current selectors. Any future
`out_of_scope` reclassification also requires explicit human scope authority
that preserves the immutable Phase 8 inclusion record. Neither authority is
introduced or inferred in Phase 9.

### Legacy Offline Replay Migration

`ra survey build --mode offline-replay` becomes diagnostic-only. Packet-shape
completeness may emit `offline_replay_fixture_complete` but always has
`ready_for_writer=false` and `ready_for_prose=false`, with a next action pointing
to the canonical selected-artifact/review/hostile path. Every helper, validation
script, and test expecting `offline_replay_ready_for_prose` is audited and
repaired without weakening canonical hostile-review readiness.

### Required Artifacts And Allowlist

- New pure `src/research_assistant/survey/evidence_semantics.py` if separation is
  clearer than embedding the validators.
- Narrow changes to `source_safety_review.py`, `claim_review.py`,
  `omission_review.py`, `review_decisions.py`, `artifact_lineage.py`,
  `reviewed_merge.py`,
  `reviewed_packet.py`, `hostile_review.py`, and `orchestrate.py`.
- Narrow offline-replay-only changes to `build.py` and affected helper/script
  tests.
- `tests/unit/test_literature_survey_m16_phase9.py` and focused compatibility
  additions.
- `docs/validation/literature_survey_m16_phase9_2026-07-12/`, Phase 9 result,
  implementation review, refreshed Phase 10 subplan, and plan review.
- Pre-implementation quarantine and complete positive-terminal reachability
  audits proving the old closure is unreachable and the conservative positive
  fixture satisfies every terminal predicate before product edits.

No file outside the refreshed Phase 9 allowlist may be edited. A discovered
dependency first repairs the subplan and passes focused review.

### Required Checks

1. Model-only, legacy ambiguous, unauthenticated, missing, duplicate, and stale
   claim-review authority cannot authorize support.
2. Model-only, legacy ambiguous, missing, duplicate, stale, wrong-paper, and
   wrong-version source-review authority cannot derive `checked_clear`; a
   human-shaped claim decision composed with any such source decision remains
   blocked.
3. Every claim type/support class valid and invalid combination is tested.
4. Metadata, abstract, introduction, conclusion, citation/venue, source
   availability, and unreviewed parsed text never support technical claims.
5. Primary anchors replay from current source bytes; stale paper/anchor/version
   bindings fail.
6. Project derivation and implementation evidence enforce path containment,
   regular files, hashes, and correct claim type.
7. Every source-status outcome has positive and adversarial tests; free text,
   missing dates, wrong versions, stale hashes, and foreign observations fail.
   Source decision IDs must exactly equal the validated observation/queue
   universe; missing, duplicate, extra, or observation-free rows cannot shrink
   source accounting.
8. Claim-dependent unsafe sources block; every unused included source also
   blocks because no exact queue-backed exclusion authority exists in Phase 9.
9. Empty, direct, transitive, duplicate, cyclic, missing, foreign, hidden-from-
   decision, and mismatched dependency-manifest cases are caught; every declared
   dependency is checked against the current selected status set.
10. Every selected-source/dependency accounting row and forbidden combination
    is tested; quarantine replacement/closure inputs are rejected and the exact
    open-risk diagnostic never implies completeness.
    The pre-implementation positive-terminal reachability audit must show zero
    unavailable/open/quarantine predicates and exact source/dependency equality.
11. Changed observation/status-set/source-decision-set/omission-decision-set
    invalidates merge, packet, hostile review, and readiness; identical replay
    retains authority. Pointer, manifest, partial-replacement, crash, and stale-
    sibling cases fail closed.
12. After a selected upstream artifact queue changes, a forced complete
    omission import appends queue-B authority to intact queue-A history. Every
    historical set replays against the exact artifact-set queue committed in
    its manifest; only the selected/head set may authorize the current queue.
    Same-byte reuse and orphan-head recovery also require current lineage.
    Corrupt historical bytes, missing predecessors, forks, and stale selectors
    remain hard failures.
    A unique immediate intrinsically valid stale orphan may be superseded only
    by a forced append bound to the new current queue; it is never selected.
13. Offline replay never sets prose/writer readiness.
14. Zero live/provider/source/model/GPU calls and zero outside writes.
15. Focused, compatibility, combined M16, full unit/CLI/scripts/UX/static and
    repository hygiene gates pass under CPU-only execution.

### Phase 9 Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Does the workflow keep observation, availability, source status, reviewed evidence, and claim support distinct through hostile review? |
| Baseline | Conservative components with free-text source clearance, model-pass readiness possibility, broad support-class scope, and legacy replay readiness. |
| Primary criterion | Every forbidden promotion fails and valid synthetic fixtures require exact allowed review, evidence, source, claim-type, and selected-lineage bindings. |
| Hard vetoes | Model-only support authorization; wrong claim class/type; unsafe dependent source; stale/free-text clearance; fixture-shape readiness. |
| Explanatory only | Counts of anchors, observations, decisions, notices, and runtime. |
| Not concluded | Real human review, claim truth, source safety in fact, scientific correctness, or completeness. |

### Phase 9 Handoff

Phase 9 closes only after local gates, a usable material read-only implementation
agreement under the Claude-or-downgraded-Codex rule above, its result, and the
reviewed refreshed Phase 10 subplan pass. Phase 10 receives the
fully integrated local state machine, explicit synthetic fixture-review policy,
exact negative-case table, and no live or scientific authority.

## Phase 10 - Offline End-To-End Validation And Local Closeout

### Phase Objective

Run exact positive and adversarial offline missions through the public CLI and
canonical supervisor, prove idempotent local terminal behavior, and close the
hash-attested local program without claiming Git, live, human, or scientific
evidence.

### Entry Conditions

- Phases 0-9 and their next-plan review gates are `PASSED`.
- Phase 10 subplan names exact commands, selectors, timeouts, output paths,
  expected state/error codes, and authoritative artifacts from the current code.
- All Phase 8/9 tripwires and protected hashes pass.

### Positive Mission Contract

One deterministic fixture-only mission must run twice. The first run reaches
the canonical hostile-review terminal state using explicitly synthetic
human-review-shaped decisions. The second run must reuse the same immutable
metadata, source, coverage, queue, reviewed packet, hostile-review, and terminal
bytes where timestamps are not semantically authoritative, perform no forbidden
capability call, and produce the same selected artifact-set ID. The result must
say that this tests state-machine behavior and does not attest real human review.

### Exact Negative Mission Matrix

The refreshed subplan maps each case to an exact expected terminal code and
forbidden artifact/call set:

- missing confirmation;
- changed topic, seed, budget, or provider scope;
- ambiguous/conflicting/unresolved seed;
- stale, foreign, partial, mixed, or tampered metadata authority;
- duplicate, partial, unknown, wrong-type, model-only, or stale decision;
- changed frontier after review;
- open inspection, source, quarantine, or workflow risk;
- metadata/context/implementation evidence promoted to a technical claim;
- retracted, withdrawn, concerned, erratum, quarantined, or version-conflicting
  source used by a dependent claim;
- legacy offline replay attempting readiness;
- corrupt, malformed, noncanonical, invalid UTF-8, symlinked, nonregular,
  unexpected, or moved artifact;
- interrupted mission generation, V2 metadata commit, source-intake commit,
  artifact-set staging, CURRENT selection, reviewed packet, or hostile review;
- cap, timeout, outside-write, provider, network, source, model, or GPU tripwire.

### Commands And Artifacts

All commands are finalized in the refreshed Phase 10 subplan and use:

```bash
CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src:. pytest ...
```

Full output is redirected to declared logs; JUnit/JSON summaries are
authoritative. Required gates include focused Phase 8/9/10, combined M16,
full unit, full CLI, exact scripts, UX, compilation, JSON/JUnit parsing,
writer-table coverage, provider-transport AST audit, protected hashes,
`git diff --check`, and NUL-safe Phase 0 reconciliation. A broader non-CLI
integration group has a predeclared timeout. Relevant failure is a hard veto;
an unrelated timeout is recorded as incomplete evidence, never a full pass.

Required artifacts:

- `docs/validation/literature_survey_m16_phase10_2026-07-12/` with positive and
  negative missions, structured E2E summary, manifests, logs, JUnit, static
  audits, reconciliation, and tripwire results;
- Phase 10 decision table, inference-status table, run manifest, and post-run
  red-team note;
- compact final implementation/evidence review;
- Phase 10 result and reconciled master/runbook/ledger/reset memo/handoff;
- refreshed Phase 11 plan marked `HUMAN_APPROVAL_REQUIRED_DO_NOT_EXECUTE`.

### Phase 10 Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Does the integrated offline workflow reach the exact intended terminal state for valid and adversarial missions without forbidden action? |
| Baseline | Passed component/compatibility phases; no prior Phase 8-10 E2E authority. |
| Primary criterion | Positive double-run is lineage-valid and idempotent; every negative stops at its predeclared veto; all scoped gates pass. |
| Hard vetoes | False readiness, wrong blocker, unsafe call/write, stale reuse, non-idempotence, corrupt authority accepted, missing required negative case, or changed pass criterion. |
| Explanatory only | Runtime, counts, transition count, and broad-suite duration. |
| Not concluded | Real human review, live reliability, completeness, science, prose quality, Git reproducibility, product or release readiness. |

### Local Completion And Git Boundary

If all Phase 10 gates converge, M16 status is
`PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`. This truthfully closes the
offline engineering question in the hash-attested workspace. It does not claim
the untracked implementation can be reconstructed from Git history.

After local closeout, prepare a proposed Git integration manifest only. Do not
stage or commit without separate user authorization. Git integration and Phase
11 live validation are independent optional next actions.

## Phase 11 - Separate Optional Human Boundary

Phase 11 is not executed by this repair plan. Before requesting approval its
subplan must name exact topic, seed, providers/domains, record/query/source/byte
caps, timeouts, retries, redirects, output root, and metadata-only versus
source/PDF/full-text scope. The safest first request is metadata-only. Existing
Claude and offline-execution approvals do not authorize live access.

## Exact Stop Conditions

Stop, write a blocker result/handoff, and request direction only if:

- an unexplained user edit overlaps an authorized file and cannot be preserved;
- current Phase 7 or preceding-phase authority/hashes cannot be validated;
- correct execution needs live/network/provider/source/PDF/full-text,
  credentials, private/paid data, package installation, GPU/model files,
  destructive action, Git staging/commit, a product default, or an actual
  scientific/human-review authorization;
- the required evidence distinction cannot be represented without weakening a
  Phase 1-7 boundary;
- a required local check repeatedly fails because of an unresolved environment
  defect rather than a repairable implementation defect; or
- the same material review blocker fails to converge after five rounds.

These are repair triggers, not stops:

- a fixture candidate is rejected, ambiguous, unavailable, capped, unsafe, or
  unsupported;
- a new catching test exposes a schema, lineage, crash, or compatibility defect;
- a focused or broad test fails because of an in-scope implementation issue;
- Claude returns `REVISE` on a fixable issue;
- a broad Claude prompt times out while a tiny trusted probe succeeds; or
- a current candidate fails a promotion veto while a planned repair directly
  addresses it.

## Completion Checklist

This repair plan is complete only when:

- Phase 7 is formally closed after Phase 8 plan agreement;
- Phase 8 frontier/omission authority and Phase 9 evidence authority pass their
  local gates and the material Claude-or-downgraded-independent-Codex review
  gates defined above;
- Phase 10 positive/adversarial offline evidence passes;
- master, runbook, ledger, stop handoff, reset memo, phase results, and paths are
  mutually consistent;
- protected user files and forbidden capability tripwires remain unchanged;
- local status is reported directly as either
  `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING` or a precise valid blocker;
  and
- Phase 11 remains unexecuted without exact human live approval.
