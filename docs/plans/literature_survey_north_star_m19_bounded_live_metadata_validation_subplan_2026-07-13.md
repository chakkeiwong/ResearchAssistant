# M19 Bounded Live Metadata Validation Subplan

Date: `2026-07-14`
Status: `M19A_LOCAL_CLOSEOUT_CANDIDATE_PENDING_EXACT_LIVE_APPROVAL_DO_NOT_EXECUTE_LIVE`
Milestone: `M19_bounded_live_metadata_validation`
Closes: `G2_bounded_live_metadata`

## Phase Objective

Harden and validate one exact metadata-only OpenAlex/arXiv transport attempt
from the M18 code-authority commit, classifying boundary validity separately
from provider availability and result contents. The future attempt is
one-shot. It is not source, PDF/full-text, citation-frontier, reliability,
scientific, or product evidence.

This refreshed parent is planning authority only. It authorizes local
hardening design and tests after the child plan is written and reviewed. It
does not authorize any live request.

## M19A Actual Hardening Evidence

Terminal review rejected the initial M19A candidate because an unexpected
parser/programmer failure could collapse into provider unavailability. Repair
commit `bb4300c` closes that defect, and fresh isolated-wheel validation
passes. The live M19 attempt has not run.

| Item | Actual value |
| --- | --- |
| Product implementation commit | `23e218b563e2e554c02c1ac063fea1f73034edf4` |
| Reviewed harness commit | `945332f891e40cc02d53806bc3ca4b2157cc51e0` |
| Parser-boundary repair | `bb4300c6bce20145a7c41620b0dffb703072e755` |
| Lineage | `e7f1499 -> 23e218b -> 945332f -> bb4300c` |
| Environment | WSL2 x86_64, Python `3.11.14`, conda `tf-gpu`, CPU-only `CUDA_VISIBLE_DEVICES=-1` |
| Fresh local gates | `26 + 30 + 58 + 846 + 125` passed; zero failures/errors |
| Isolated installed wheel | SHA-256 `6605ddeb46b15c2e0f29b23466743cf2c48db6a72eb2434019b2add22d135888` |
| Superseding validation root | `docs/validation/literature_survey_m19_transport_hardening_round3_2026-07-14/` |
| Fake route manifest | SHA-256 `a02c39520bcec6fa01bc4a9ceda53b0a83243e282e76551f0f9c53297734ebe6` |
| Fake request ledger | Four closed deterministic no-network rows; SHA-256 `fee0ed267d3ba79295075b92c6a902cfdcf3e0daa48f12e30fc12cad6e9ee3f9` |
| M19A result | `docs/plans/literature_survey_north_star_m19_metadata_transport_hardening_result_2026-07-14.md` |
| Live status | `DO_NOT_EXECUTE_LIVE`; exact live root absent |

The frozen future route is four HTTPS `GET` requests in order: arXiv seed,
arXiv topic, OpenAlex seed, OpenAlex topic. It uses seed
`arxiv:2201.12220v3`, topic
`Neural Optimal Transport for generative modeling and inference`, provider
order `arxiv,openalex`, `max_records=10`, per-route caps `5/10/5/10`,
`2,000,000` accepted bytes/request, `8,000,000` accepted bytes total,
`30` seconds/request, `187` seconds whole attempt, zero redirects, zero
retries, explicit no-proxy transport, and no credentials. The exact decoded
queries and request-binding hashes are in the route manifest named above.

The original evidence root is rejected by terminal review; round 2 is a
preserved import-harness failure. Only round 3 is current promotion evidence.
The live command and closeout commit remain pending until terminal rereview
agrees and the docs/evidence-only M19A closeout child exists. This parent
remains non-executable meanwhile.

## Entry Conditions Inherited From M18

| Authority | Value | Status |
| --- | --- | --- |
| M18 code commit | `654e6e1a1213bc03b7693ff1a8aea945a5bf08ac` | Isolated candidate validation passed |
| M18 parent | `1b36af06efc7e1c2c086934cd8800691ae8a6da7` | Exact single parent |
| M18 tree | `074de2d38287af139d767c67680868bf8d055f03` | Frozen candidate tree |
| M18 payload | `0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318` | `1,684/1,684` replay passed |
| M18 stage record | `8db52bdf4d7f87d7cadedd711646b1661c7a189ce308f4f9a239c524d6294aa4` | `1,725` committed paths |
| M18 wheel | `891e1e152d4d53fec3287b8209514b47383d9d2d85a02671b9e4358b343dcee2` | Offline build/install passed |
| M18 environment | WSL2 x86_64, Python `3.11.14`, Git `2.34.1` | CPU-only, `CUDA_VISIBLE_DEVICES=-1` |
| M18 terminal review | `docs/reviews/literature_survey_m18_terminal_review_verdict_round3_2026-07-14.md` | Fresh Codex read-only `AGREE` |
| M18 closeout commit | `e7f1499e135757c0460c040f3fa317e6bdd56dc9` | Exact docs/evidence-only direct child of candidate |
| M18 closeout replay | `/tmp/ra_m18_closeout_record.json` | Passed; SHA-256 `4de376567d321f3b91956292b2db2bbf3936197b335d5af36be5703971ac0019` |

The old M16 Phase 11 plan is historical and previously nonconverged. It is not
executable authority. No later dirty worktree byte may silently replace the
identified M18 code authority.

## Observed Transport Surface And Gaps

The M18 candidate currently exposes metadata transport primarily through:

- `src/research_assistant/survey/build.py`:
  `PUBLIC_METADATA_MAX_RECORDS=25`, `PUBLIC_METADATA_TIMEOUT_SECONDS=30`,
  `OPENALEX_WORKS_ENDPOINT=https://api.openalex.org/works`,
  `ARXIV_QUERY_ENDPOINT=https://export.arxiv.org/api/query`,
  `_fetch_public_json`, `_openalex_metadata_search`,
  `_openalex_cited_by`, and `_arxiv_metadata_query`;
- `src/research_assistant/survey/orchestrate.py`: confirmed
  `run-public-source-workflow` metadata orchestration; and
- `src/research_assistant/cli.py`: `survey build --mode public-metadata` and
  `survey run-public-source-workflow` command surfaces.

The current `urllib.request.urlopen` calls check a host before opening and cap
arXiv body reads, but they do not yet establish the M19 boundary. In
particular, redirect destinations, environment proxies, retry behavior, TLS
and DNS classification, OpenAlex response byte limits, request counting,
closed request ledgers, subprocess/IPC constraints, and exact write-root
enforcement require a dedicated design and catching tests. Broad exception
conversion to `unavailable` is insufficient because it can hide a boundary
violation.

## Research Intent Ledger

| Field | M19 contract |
| --- | --- |
| Main question | Does one frozen metadata transport attempt remain inside its exact boundary, and what closed provider outcome occurs? |
| Candidate/mechanism | A reviewed transport/supervisor wrapper around the M18 OpenAlex/arXiv metadata functions. |
| Expected failure mode | Redirect/proxy/retry/process behavior escapes caps, a response exceeds byte/schema bounds, or a boundary defect is collapsed into ordinary provider unavailability. |
| Promotion criterion | One exactly approved, boundary-valid attempt yields a replay-valid available, empty, unavailable, or provider-failed outcome. |
| Promotion veto | Unapproved request, endpoint, query, redirect, retry, bytes, time, process, IPC, artifact, environment, or write behavior; ambiguous approval; corrupt ledger/schema. |
| Continuation veto | Invalid harness, unrepresentable boundary, wrong code authority, absent exact live approval, corrupt artifact, exhausted one-attempt budget, or five-round material nonconvergence. |
| Repair trigger | No-network test failure, schema drift, boundary defect before launch, or material read-only `REVISE`. |
| Explanatory only | Result counts, titles, scores, latency, response bytes, and provider availability. |
| Must not be concluded | Provider reliability, citation recall, source retrieval, claim support, completeness, scientific correctness, or product readiness. |

## Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Does the reviewed metadata transport stay inside the frozen boundary, and what happened in exactly one attempt? |
| Baseline/comparator | M18 clean-commit fixture-backed metadata behavior plus sanitized no-network replay. |
| Primary pass criterion | Boundary validity passes and every attempted or denied provider request has a closed, persisted, replay-valid disposition. |
| Hard vetoes | Any unapproved/unlogged network, redirect, proxy, retry, process, IPC, environment, cache, or write behavior; missing approval; wrong commit/hash; response outside cap/schema; automatic rerun. |
| Explanatory diagnostics | Provider availability, counts, latency, bytes, response codes, and normalized metadata contents. |
| Not concluded | Citation/frontier completeness, source access, provider reliability beyond the attempt, paper importance, claim support, human review, product readiness. |
| Preserving artifacts | Child hardening plan/result, frozen implementation manifest, approval packet/receipt, request ledger, run manifest, boundary report, provider outcome, replay, decision table, red team, result review, and M20 handoff. |

## Default And Assumption Audit

| Choice | Provenance | Justification | Failure mode | Early diagnostic | Status |
| --- | --- | --- | --- | --- | --- |
| Providers OpenAlex and arXiv | M18 CLI/defaults | They are the implemented public metadata adapters | Scope silently expands to other hosts/routes | Exact host/path/query allowlist tests | Baseline hypothesis |
| `25` metadata records | M18 constant and mission confirmation | Existing local contract | Per-query calls exceed total campaign records or requests | Counter-based no-network fixtures | Reviewed inherited cap, not live-ready |
| `30` second timeout | M18 constant | Existing behavior | Sequential calls exceed total wall budget | Fake-clock and watchdog tests | Convenience baseline |
| `urllib.request` | M18 implementation | Small standard-library surface | Redirect/proxy handlers broaden effective routes | Custom opener/handler negative matrix | Requires hardening |
| Normalized rows only | M18 provenance contract | Minimizes retention | Missing response evidence makes boundary replay ambiguous | Hash-bound request/disposition ledger plus capped sanitized metadata | Required, design pending |
| One live attempt, no rerun | Master program | Prevents result-conditioned retries | Infrastructure failure consumes the only attempt | Exhaustive no-network preflight and explicit stop | Required |

## Required Artifacts Before Any Live Action

1. A dedicated M19 transport/supervisor-hardening child subplan under
   `docs/plans` with exact code/test/fixture/edit allowlists, threat model,
   proportional controls, evidence contract, request budget, stop conditions,
   and result path.
2. A separately identified implementation commit or exact descendant of the
   M18 closeout that contains only the reviewed M19 hardening delta.
3. Sanitized recorded-response fixtures and no-network negative evidence.
4. A frozen route/cap manifest covering method, scheme, host, port, path,
   canonical query keys/values, headers, redirect/proxy/retry policy, TLS/DNS
   disposition, response bytes, request count, total wall time, process/IPC,
   environment/cache, and mission-local write roots.
5. A compact approval packet naming the exact commit, command, routes, caps,
   output root, log root, and one-attempt rule.
6. Fresh read-only agreement on the child plan, implementation/tests, this
   parent, and approval packet.
7. Fresh user authorization for only the frozen live attempt.

## Required Local Checks Before Approval Request

Run CPU-only, no-network catching tests for:

- exact HTTPS `GET` allowlist and canonical query construction;
- redirect denial, including cross-host/scheme/port and redirect loops;
- environment proxy suppression or exact reviewed proxy policy;
- zero automatic retry and exact request counting;
- DNS, TLS, timeout, HTTP, parse, truncation, and provider failure classes;
- OpenAlex and arXiv response byte caps and normalized schema caps;
- total wall watchdog, subprocess/IPC denial, and thread/task accounting;
- output-root confinement, no symlink/nonregular target, no ambient cache or
  credential read, manifest-last artifact durability, and complete ledgers;
- available, empty, unavailable, rate-limited, malformed, oversized, partial,
  and write-failure recorded-response replay; and
- confirmation/mission-lineage binding without adding provider-shaped product
  prompts.

The skeptical pre-execution audit must explicitly recheck wrong baseline,
proxy metrics, stop conditions, route fairness, inherited defaults, environment
differences, and whether each artifact answers boundary validity rather than
merely provider availability.

## Live Attempt Contract

The exact command, query inputs, request count, bytes, time, output root, and
hashes remain intentionally unset until the child plan and implementation
converge. The future budget is one live attempt. Any HTTP outcome, including
empty, unavailable, rate-limited, timeout, or provider failure, consumes the
attempt. There is no automatic repair or rerun using live access.

Classify boundary validity before interpreting provider contents. A provider
failure with a complete boundary-valid ledger can pass the engineering
question while providing no evidence of provider quality.

## Forbidden Claims And Actions

- `DO_NOT_EXECUTE_LIVE`: do not call OpenAlex, arXiv, DNS, an HTTP proxy, or
  any other endpoint from this plan revision.
- Do not infer live authority from M18, the product's persisted discovery
  confirmation, an old Phase 11 approval, or this refreshed planning record.
- Do not access source/PDF/full text, broader citation-frontier routes,
  credentials, private/paid services, arbitrary URLs, or unlisted endpoints.
- Do not follow unapproved redirects/proxies, retry, or rerun the one-shot
  attempt.
- Do not collapse a boundary violation into `unavailable`.
- Do not rank providers/papers or treat counts/metadata as technical support,
  reliability, completeness, scientific, or product evidence.
- Do not mutate unrelated dirty files, push, release, or change defaults.

## Exact Next-Phase Handoff Conditions

M20 may enter refreshed planning only if M19 has a boundary-valid,
replay-valid closed result; the exact request ledger is complete; the M18/M19
commit lineage remains intact; terminal M19 review agrees; and M20 is refreshed
with actual provider provenance, observed schemas, safe transport primitives,
unresolved limitations, a predeclared route/case matrix, and a separate live
approval request. No source or production-bootstrap authority is handed off.

## Stop Conditions

Stop for absent exact approval, failed preflight/hash, unsafe or
unrepresentable transport boundary, wrong commit, corrupt/incomplete request
ledger, need to change criteria after provider output, exhausted one-attempt
budget, or five-round material plan/review nonconvergence. Provider empty,
unavailable, or rate-limited outcomes are honest results rather than
continuation vetoes when boundary validity and artifact closure pass.

## Exact Next Safe Action

Obtain terminal read-only rereview of the repaired M19A implementation and result. If it
agrees, commit only the closeout docs/evidence as a direct child of `bb4300c`,
freeze the compact live packet against that actual child, and request fresh
user approval. Do not execute the live command before that exact approval.

## End-Of-Phase Sequence

After a future authorized attempt, run local replay/checks, write the M19
result, refresh M20 from observed schemas and exact authority, review M20 for
consistency/correctness/feasibility/artifact coverage/boundary safety, update
the program controls, and stop at the next ungranted boundary.
