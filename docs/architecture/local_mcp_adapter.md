# Local MCP Adapter

## Purpose

The local MCP adapter exposes selected `research-assistant` workflows to local
assistant clients without changing the product into a hosted service.

The adapter is an integration layer over the existing local CLI/Python contract.
It is not a shared backend, public HTTP API, multi-user service, SSO/RBAC
system, production deployment, or hosted paper database.

## First Release Scope

- Transport: local stdio.
- Default mode: read-only.
- Workspace: one explicit local `research-assistant` root.
- Storage: existing file-based `local_research/` workspace.
- Dependency: optional MCP extra.
- Network/provider posture: no default live provider or LLM calls.

The first MCP tools may inspect local summaries, source records, review queues,
privacy status, parser-tool readiness, and claim-audit output. They must not
mutate review state, ingest papers, download files, restore backups, overwrite
records, delete files, or read arbitrary filesystem paths.

## Permission Modes

- `read_only`: default and first shipped mode.
- `arxiv_batch_intake`: bounded future mode for approved arXiv source/PDF
  intake into review locations.
- `review_write`: deferred until confirmation, audit, and conflict behavior is
  proven.
- `destructive`: out of scope.

## Batch ArXiv Intake

Large literature pulls should use batch-scoped grants rather than one prompt per
paper. A grant is local, expiring, and tied to:

- workspace root;
- explicit arXiv IDs or a future query scope;
- maximum paper count;
- allowed domains;
- destination;
- duplicate and overwrite policy;
- stable plan hash;
- audit and manifest paths.

Batch intake creates review material only. It must not mark records approved or
promote generated/parser-derived information into accepted technical audit
fields.

## Safety Requirements

- Resolve and validate workspace roots server-side.
- Reject path traversal and symlink escape.
- Keep writes inside approved workspace locations.
- Keep HTTP/server deployment out of this milestone.
- Keep destructive operations absent from MCP.
- Keep MCP optional in release reports; absence of the MCP extra is not an
  individual local release blocker.

## Relationship To ADR 0006

ADR 0006 defers web/server deployment until storage, identity/RBAC, operations,
and orchestration decisions are accepted. The local MCP adapter fits before
that line because it is a local stdio adapter over existing local contracts, not
a deployed service.
