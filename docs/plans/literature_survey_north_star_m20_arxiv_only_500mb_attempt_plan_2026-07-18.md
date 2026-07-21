# M20 ArXiv-Only 500 MB Attempt Plan

Date: `2026-07-18`
Status: `SKEPTICAL_AUDIT_PASS_SINGLE_AUTHORIZED_LIVE_ATTEMPT_PENDING`
Migration: `docs/plans/literature_survey_north_star_m20_arxiv_only_governance_migration_2026-07-18.md`

## Objective And Authority

Execute the user-authorized single arXiv-only M20 attempt for exact seed
`2201.12220v3`. The public source response cap and final validation-root
retention cap are each `500,000,000` bytes. No credentials, retries, reruns,
PDF fallback, extra routes, M21, push, release, or completion claim are
authorized.

## Revised Scientific Evidence Contract

- Primary pass: exact retained seed identity; one accepted source body; safe
  in-memory archive inspection; at least one canonical backward candidate;
  complete candidate-classification and omission-risk ledgers; forward coverage
  explicitly unavailable/non-blocking; total root at most `500,000,000` bytes;
  raw-source confinement; exact preserved dirty-worktree execution sources;
  deterministic offline replay.
- Hard veto: identity mismatch, non-HTTPS/disallowed redirect, non-source
  content type, response/root cap breach, unsafe path/type, archive/member/
  expansion cap breach, empty backward layer, malformed identifier, raw-source
  escape, or replay mismatch.
- Explanatory only: source size, member inventory, bibliography-unit counts,
  identifier yield, titles, and elapsed time.
- Nonclaims: forward coverage, completeness, candidate relevance, technical
  claim support, retraction/version safety, scientific correctness, M21 or
  north-star completion.

## Resource Bounds

| Resource | Bound |
| --- | --- |
| compressed source response | `500,000,000` bytes |
| final evidence root | `500,000,000` bytes |
| reserved derived-evidence space | `50,000,000` bytes inside the root cap |
| archive members | `4,096` |
| declared total archive expansion | `1,000,000,000` bytes |
| one relevant `.tex/.bib/.bbl` member | `50,000,000` bytes |
| all relevant text members | `200,000,000` bytes |
| canonical backward candidates | `5,000` |
| redirects | at most one, within `arxiv.org`/`export.arxiv.org` |
| attempts/retries | one invocation, zero retries |

Large irrelevant regular members are counted toward expansion but are not read
into memory. Links, devices, unsafe paths, duplicate relevant paths, and all
non-regular non-directory members fail closed.

The transport may receive at most `500,000,000` bytes, but a body larger than
the remaining root capacity after the `50,000,000` byte derived-evidence
reserve is removed and classified as `evidence_root_cap_exceeded`. This is the
necessary intersection of the independently authorized source and total-root
caps, not an implicit increase to either cap.

## Candidate Classification

Every extracted candidate receives:

- `source_role=backward_reference_candidate`;
- `scholarly_classification=NOT_CHECKED`;
- `support_status=SOURCE_GAP_BLOCKER`;
- `action=inspect_primary_source`.

This is an honest classification state, not a claim of relevance. Technical
taxonomy such as foundational/direct/competitor is deferred until primary
technical material is inspected.

## Default And Assumption Audit

| Choice | Provenance/status | Failure mode | Early diagnostic |
| --- | --- | --- | --- |
| exact seed/version | retained M19 identity | wrong source version | local identity preflight |
| 500 MB response/root caps | explicit user authority | disk/memory pressure or root cannot contain derived evidence | preflight free-space check; bounded streaming; root accounting |
| 1 GB expansion cap | local safety hypothesis | legitimate archive exceeds it or compressed bomb consumes resources | tar member metadata sum before relevant reads |
| 50/200 MB relevant-text caps | local parsing hypothesis | unusually large TeX/BibTeX rejected | member metadata checks before reads |
| identifier-only extraction | bounded parser | identifier-free relevant references omitted | bibliography-unit yield and omission ledger |
| `NOT_CHECKED` classification | scholarly policy | little immediate prioritization | explicit M21 primary-source triage handoff |
| forward unavailable | explicit user override | reviewers infer complete frontier | non-blocking unavailable ledger and completeness nonclaim |

## Pre-Mortem

- A 500 MB download could leave no space for evidence. The runner checks free
  disk and enforces the final root cap on every retained artifact.
- A compressed archive could expand pathologically. Expansion is bounded from
  member metadata before relevant contents are read.
- A source body could be HTML. Content-type and archive/text parsing veto it.
- Dirty-worktree code could change after the run. The runner preserves exact
  plan, migration, runner, and worker bytes and binds their hashes in the run
  manifest.
- Non-empty identifiers could be misrepresented as relevant literature. All
  candidates remain `NOT_CHECKED` and blocked from claim support.
- M20 closure could be mistaken for complete discovery. Forward coverage and
  identifier-free reference recall remain explicit omissions.

## Skeptical Audit

- Wrong baseline: repaired. The active question no longer requires a provider
  that is outside project scope.
- Proxy promotion: blocked. Download success or candidate count alone cannot
  pass; safety, classifications, omissions, confinement, and replay are needed.
- Missing stop conditions: route, disk, response/root, archive, member,
  expansion, empty-yield, privacy, and replay failures are explicit.
- Environment mismatch: CPU-only; no GPU/model/credential applies.
- Artifact adequacy: retained source and replay answer backward candidate
  capability, but not relevance, forward coverage, or completeness.
- Hidden defaults: archive/text/candidate caps and identifier-only recall are
  explicit hypotheses with diagnostics and nonclaims.

Audit verdict: `PASS`. The historical parser's 20 MB package and 2 MB
all-member limits did not fit the authorized route and could reject irrelevant
figures. The separate arXiv-only worker/runner now streams the source to disk,
counts irrelevant members toward expansion without loading their contents,
enforces archive/text/candidate caps, removes any unaccepted body, preserves
the exact dirty-worktree plan/migration/runner/worker bytes, and replays the
accepted source offline. The local evidence below passed before launch.

## Local Launch-Readiness Record

Date: `2026-07-18`
Environment: deliberate CPU-only execution with `CUDA_VISIBLE_DEVICES=-1`.

- focused arXiv-only tests: `15 passed`;
- arXiv-only plus related historical M20 regression slice: `115 passed`;
- `py_compile` for worker, runner, and focused test: passed;
- canonical milestone JSON parse: passed;
- active source scan: no provider name, API-key interface, authorization
  header, or cookie; one network-opening call exists and is the arXiv source
  route; `credential_interface=false` is retained as explicit evidence;
- retained M19 identity path and fresh-root parent preflight: passed;
- scoped `git diff --check`: passed.

Skeptical audit disposition:

- wrong baseline: repaired by the governance migration; exact M19 seed identity
  and local adversarial archive fixtures are the baseline;
- proxy promotion: candidate count alone cannot pass and every candidate stays
  `NOT_CHECKED`/`SOURCE_GAP_BLOCKER`;
- missing stop conditions: none identified after response/root/archive/member/
  path/type/empty-layer/raw-confinement/replay veto checks;
- unfair comparison: not applicable; no provider or candidate ranking occurs;
- hidden assumptions: identifier-only recall and all numeric caps remain
  explicit hypotheses and limitations;
- stale context: active master, milestone JSON, runbook, execution ledger,
  stop/handoff, and reset memo now select this migration and preserve prior
  provider lanes as history;
- environment mismatch: CPU-only, no GPU/model/credential dependency;
- artifact fitness: exact source bytes, exact executed dirty-worktree sources,
  six ledgers, terminal result, inventory, and offline replay answer the revised
  question without supporting forward-coverage or completeness claims.

Launch is permitted exactly once under the existing user authorization. This
verdict does not authorize a retry, rerun, extra route, M21 execution, Git
integration, push, release, or mission-completion claim.

## Stop And Handoff

Any live failure is terminal; do not repair and retry. A pass enters terminal
review and revised M20 closure reconciliation. M21 begins only after the
revised contract is proven and the program/handoff artifacts are updated.
