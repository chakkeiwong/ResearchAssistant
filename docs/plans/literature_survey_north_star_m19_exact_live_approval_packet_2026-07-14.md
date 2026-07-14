# M19 Exact One-Shot Live Metadata Approval Packet

Date: `2026-07-14`
Status: `DRAFT_PENDING_M19A_CLOSEOUT_COMMIT_DO_NOT_EXECUTE_LIVE`

## Boundary

This packet will request authority for exactly one metadata-only attempt after
terminal review and the M19A docs/evidence closeout commit exist. It does not
authorize source/PDF/full text, citation-frontier expansion, credentials,
private/paid services, GPU use, retries, reruns, push, release, or scientific
and product claims.

## Frozen Inputs And Limits

| Field | Exact value |
| --- | --- |
| Execution commit | `PENDING_M19A_CLOSEOUT_COMMIT` |
| Required code ancestor | `bb4300c6bce20145a7c41620b0dffb703072e755` |
| Topic | `Neural Optimal Transport for generative modeling and inference` |
| Seed | `arxiv:2201.12220v3` |
| Providers | `arxiv`, then `openalex` |
| Maximum normalized records | `10` |
| Request count | Exactly `4` |
| Per-request accepted body | `2,000,000` bytes |
| Aggregate accepted body | `8,000,000` bytes |
| Request timeout | `30` seconds |
| Whole attempt | `187` seconds |
| Redirects | `0` |
| Retries/reruns | `0` |
| Proxy | Explicitly disabled; proxy environment removed from worker |
| Credentials | Forbidden |
| Live output root | `docs/validation/literature_survey_m19_live_metadata_2026-07-14` and it must be absent |

The four ordered routes and decoded queries are exactly those in
`docs/validation/literature_survey_m19_transport_hardening_round3_2026-07-14/fake_run/route_manifest.json`,
whose current SHA-256 is
`a02c39520bcec6fa01bc4a9ceda53b0a83243e282e76551f0f9c53297734ebe6`.
Before approval is requested, this packet will copy the four rows visibly and
bind the post-closeout route-manifest hash for the execution commit.

## Pending Exact Command

The executable command is intentionally not asserted while the execution
commit is pending. After the docs/evidence closeout, it will be frozen to one
CPU-only invocation of
`scripts/literature_survey_m19_live_metadata_supervisor.py` using the repaired
isolated installed-wheel environment, with proxy, credential, `PYTHONPATH`,
and bytecode-cache variables removed. A preflight will require exact HEAD,
code/test hashes, the absent output root, and the committed M19A closeout.

## One-Attempt Rule

Any launched result consumes the attempt: success, empty response, timeout,
DNS/TLS/HTTP/provider failure, boundary failure, worker failure, or partial
artifact. There is no automatic retry or result-conditioned repair. A failed
candidate does not authorize broader routes or M20.

## Approval State

No approval is requested from this draft. It must first be finalized against
the actual closeout commit and reviewed for command feasibility, hash
consistency, artifact coverage, and boundary safety. Until then:

`DO_NOT_EXECUTE_LIVE`
