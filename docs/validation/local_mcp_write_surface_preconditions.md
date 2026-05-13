# Local MCP Write Surface Preconditions

This document gates two high-risk future surfaces:

- PDF batch download execution;
- review-write mutation through MCP.

Current status:

- PDF batch policy checks and grant-bound CLI PDF inbox execution exist.
- PDF batch execution remains absent from MCP.
- Review-write has a CLI-only prototype, but MCP review mutation is disabled.

Do not enable either surface until the relevant preconditions below are
implemented, tested, reviewed, and recorded in
`docs/validation/local_mcp_external_validation_records.md`.

## Shared Preconditions

- MCP remains local stdio.
- No hosted/shared MCP deployment is introduced.
- Every write has a bounded local grant or exact confirmation record.
- Generated outputs remain review material.
- No automatic approval of papers, claims, PDFs, parser outputs, or generated
  notes.
- Manifest/audit records summarize actions without requiring private content in
  committed docs.
- Release-report identifies the surface as disabled, experimental, or enabled
  with evidence.

## PDF Batch Execution Preconditions

Implementation requirements:

- downloader writes only to inbox;
- no direct write to trusted raw corpus;
- max file count enforced;
- max total bytes enforced;
- per-file byte limit enforced;
- allowed domains enforced;
- redirects handled or blocked explicitly;
- checksum captured for every successful file;
- no overwrite by default;
- duplicate behavior implemented and tested;
- temporary partial files cleaned after failure;
- manifest records attempted/fetched/skipped/failed;
- audit events record start/item/failure/cleanup/completion;
- failed downloads leave no clutter outside temporary paths;
- no paper is marked approved.

Tests required:

- max file count rejection;
- max total byte rejection;
- per-file byte rejection;
- missing/invalid content length with streaming limit;
- duplicate skip;
- no overwrite;
- checksum recorded;
- temporary cleanup on abort;
- manifest/audit created;
- no review approval.

Live evidence required:

- one tiny approved live smoke;
- sanitized result summary only;
- no raw PDFs committed;
- no local grants/audit logs/manifests committed.

Stop conditions:

- redirect to unapproved domain;
- missing cleanup;
- overwrite attempt;
- unclear failure reporting;
- any approval behavior.

## MCP Review-Write Preconditions

Implementation requirements:

- CLI proposal/apply flow remains stable under real use;
- undo or correction policy exists;
- exact MCP confirmation payload is designed and reviewed;
- confirmation binds:
  - workspace root;
  - operation;
  - paper or proposal ID;
  - target path;
  - old value;
  - new value;
  - previous file hash;
  - expiration;
  - risks;
  - confirmation ID;
- stale file conflict blocks;
- audit records old/new values and old/new file hashes;
- no bulk approval;
- no generic `confirm=true`;
- no promotion of generated/parser content to approved evidence;
- MCP tool name and help text clearly communicate mutation.

Tests required:

- proposal creation;
- successful apply;
- invalid status rejection;
- expired proposal rejection;
- stale file conflict;
- repeated proposal uniqueness;
- audit content;
- undo/correction workflow or documented manual correction path;
- MCP tool absence until final enablement;
- MCP tool exposure checklist once enabled.

Human review required:

- CLI UX review;
- audit event review;
- correction/undo review;
- one real user dry-run against demo data;
- explicit maintainer approval before MCP exposure.

Stop conditions:

- ambiguous confirmation;
- bulk approval pressure;
- missing old/new value;
- missing file hash;
- conflict not blocked;
- audit event incomplete;
- any automatic mathematical approval.
