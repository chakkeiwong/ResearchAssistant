# M19 Bounded Live Metadata Validation Subplan

Date: `2026-07-13`
Status: `REFRESH_AND_REVIEW_REQUIRED_DO_NOT_EXECUTE`
Milestone: `M19_bounded_live_metadata_validation`
Closes: `G2_bounded_live_metadata`

## Phase Objective

Harden and validate one exact, metadata-only OpenAlex/arXiv transport attempt
from the M18 clean commit, classifying boundary validity separately from
provider availability or result contents. The attempt is one-shot and is not
source, PDF/full-text, citation-frontier, or reliability evidence.

## Entry Conditions Inherited From M18

- M18 identifies a commit whose isolated checkout passes the cumulative local
  gate matrix.
- The M18 result, clean-checkout manifest, and final review are frozen and
  agreed.
- No later dirty-tree change is treated as live-run authority.
- The old M16 Phase 11 plan remains historical and previously nonconverged; it
  is not executable authority by itself.
- No live action is authorized until the refresh and approval gates below pass.

## Mandatory Refresh Gate

The execution-ready revision must bind the actual M18 commit and add a
dedicated transport/supervisor-hardening subplan. It must freeze:

- exact HTTPS `GET` hosts, path templates, query keys/values, user agent, and
  provider schema/version assumptions;
- DNS/proxy/redirect/retry/TLS behavior and closed failure classifications;
- total/per-provider request, byte, response, time, process, IPC, environment,
  cache, artifact, and write-root caps;
- exact no-network preflight tests and sanitized recorded-response fixtures;
- exact one-shot command, environment, output/log roots, hashes, timeout, and
  non-rerun rule; and
- an approval packet asking for fresh authorization of only that frozen
  attempt.

The hardening child plan/code/tests and refreshed parent plan must each receive
fresh read-only agreement. Only then may Codex request exact live approval.

## Research Intent Ledger

| Field | M19 contract |
| --- | --- |
| Main question | Does one frozen metadata transport attempt remain inside its exact boundary, and what closed provider outcome occurs? |
| Candidate/mechanism | Hardened one-shot OpenAlex/arXiv metadata transport from the M18 commit. |
| Expected failure mode | Redirect/proxy/retry/process behavior escapes caps or provider output cannot fit the closed schema. |
| Promotion criterion | Boundary-valid attempt yields a replay-valid available or honest unavailable/empty/provider-failed outcome. |
| Promotion veto | Unapproved request, endpoint, query, redirect, retry, bytes, time, process, IPC, artifact, or write behavior; ambiguous approval; schema corruption. |
| Continuation veto | Preflight/hash failure, unrepresentable boundary, absent approval, invalid harness, or five-round plan nonconvergence. |
| Repair trigger | No-network test failure, schema drift, boundary violation discovered before launch, or independent `REVISE`. |
| Explanatory only | Result counts, titles, scores, latency, bytes, and provider-specific availability. |
| Must not be concluded | Provider reliability, citation recall, source retrieval, claim support, completeness, product readiness. |

## Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Does the reviewed metadata transport stay inside the frozen boundary, and what happened in exactly one attempt? |
| Baseline/comparator | M18 clean-commit fixture-backed metadata behavior and sanitized no-network replay. |
| Primary pass criterion | Boundary validity passes and every provider/request outcome is closed, persisted, replay-valid, and honestly classified. |
| Hard vetoes | Any unapproved or unlogged network/process/write behavior; missing approval; wrong commit/hash; provider output outside schema; automatic rerun. |
| Explanatory diagnostics | Provider availability, counts, latency, bytes, response codes, and metadata contents. |
| Not concluded | Citation/frontier completeness, source access, provider reliability beyond the attempt, paper importance, claim support, human review, product readiness. |
| Preserving artifacts | Hardening plan/result, approval receipt, request ledger, run manifest, boundary report, provider outcome, logs, result review, and M20 handoff. |

## Exact Edit And Write Allowlist

This shell authorizes no edit or live write. The refreshed hardening and parent
plans must enumerate exact code/test/fixture/document paths and a new M19
validation root. The live process may write only the reviewed mission-local
output/log/ledger roots. Environment, home, cache, credential, repository
source, and outside paths are read/write-denied unless explicitly required and
reviewed; secrets must not be captured.

## Required Artifacts

- Refreshed M19 parent and dedicated hardening subplan/result.
- Frozen implementation/test manifest tied to the M18 commit or a separately
  integrated identified successor commit.
- No-network test and sanitized replay evidence.
- Compact final approval packet and exact user approval receipt.
- One-shot run manifest with commit, command, environment, CPU/GPU status,
  request caps, timestamps, wall time, output paths, plan, and result.
- Closed per-attempt request ledger and boundary-validity report.
- Provider outcome and replay artifact.
- Decision table, inference-status table, post-run red team, result, and review.
- Refreshed reviewed M20 subplan.

## Required Checks, Tests, And Reviews

1. Run skeptical audit and verify M18 commit/hash/clean-install authority.
2. Run no-network unit, redirect/proxy/retry, timeout, cap, IPC/process,
   symlink/nonregular, artifact, schema, and write-root negative tests.
3. Verify sanitized replay and exact provider parser outcomes.
4. Review and freeze hardening, code, tests, parent plan, and approval packet.
5. Obtain fresh exact user approval after all hashes/routes/caps are frozen.
6. Recheck hashes, absent output root, environment, and approval identity
   immediately before launch.
7. Run once. Never auto-rerun after success, empty, unavailable, provider
   failure, timeout, or boundary failure.
8. Classify boundary validity before interpreting provider outcome.
9. Replay recorded artifacts locally with `CUDA_VISIBLE_DEVICES=-1`; no later
   network call may be used to repair the record.
10. Write result and obtain a fresh material read-only review.

All local Python/tests are CPU-only. The single approved live command must also
intentionally hide GPU devices unless the refreshed plan proves a reason
otherwise and obtains separate GPU authority.

## Forbidden Claims And Actions

- Do not execute this shell, use stale Phase 11 approval, or infer live
  authority from Git approval.
- Do not access source/PDF/full text, citation-frontier routes, credentials,
  private/paid services, arbitrary URLs, or unlisted endpoints/queries.
- Do not follow unapproved redirects/proxies, retry automatically, or rerun the
  one-shot attempt.
- Do not rank providers or papers from one attempt or treat counts/metadata as
  technical support, reliability, completeness, or product evidence.
- Do not mutate Git, defaults, or unrelated files.

## Exact Next-Phase Handoff Conditions

M20 may enter refreshed planning only if M19 has a boundary-valid, replay-valid
closed result (available, empty, unavailable, or provider-failed), the exact
request ledger is complete, the M18/M19 commit authority remains intact, the
result review agrees, and M20 is refreshed with actual provider provenance,
schema observations, safe transport primitives, unresolved limitations,
predeclared route/case matrix, and a separate live approval request.

No source, broader citation, or production bootstrap authority is handed off.

## Stop Conditions

Stop for absent exact approval, failed preflight/hash, unsafe or
unrepresentable transport boundary, wrong commit, corrupt/incomplete request
ledger, need to change criteria after seeing provider output, or five-round
material plan/review nonconvergence. Provider empty/unavailable/rate-limited
outcomes are honest results, not continuation vetoes, if boundary validity and
artifact closure pass.

## End-Of-Phase Sequence

Run local replay/checks; write M19 result; refresh M20 using observed schemas
and exact authority; review M20 for consistency, correctness, feasibility,
artifact coverage, inherited conditions, and boundary safety; update ledger and
handoff.
