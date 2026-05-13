# MCP PDF Batch Intake Design

## Purpose

PDF batch intake is intentionally not enabled yet. This document defines the
policy required before a local MCP tool may download PDFs in batches.

Source package intake is already grant-bound. PDF intake needs stricter limits
because PDFs are larger, duplicate detection is weaker, and failed downloads can
leave clutter.

## Design Goals

- Keep PDF intake local and inbox-only.
- Require a bounded local grant.
- Capture proposal metadata before or with each file.
- Enforce file count, byte, domain, destination, duplicate, and overwrite
  limits server-side.
- Produce manifest and audit records.
- Never mark downloaded PDFs approved.

## Non-Goals

- No direct write to `papers/raw/` as trusted corpus material.
- No automatic ingest after download.
- No review approval.
- No broad web crawling.
- No hosted/shared MCP PDF service.

## Required Grant Fields

A PDF batch grant must include:

- grant ID;
- workspace root;
- plan hash;
- explicit candidate list or pinned candidate file;
- maximum file count;
- maximum total bytes;
- per-file byte limit;
- destination: `local_research/inbox/`;
- allowed domains;
- duplicate policy;
- overwrite policy: `no_overwrite`;
- cleanup policy;
- expiration;
- audit path;
- manifest path.

## Initial Limits

Suggested conservative defaults:

- max files: 25;
- max total bytes: 250 MB;
- max per file: 25 MB;
- request timeout: 30 seconds per file;
- destination: inbox only;
- overwrite: disabled.

These limits should be configurable only downward for first release trials.

## Allowed Domains

Initial domains:

- `arxiv.org`;
- `export.arxiv.org`.

Additional open-access hosts require explicit policy review because redirects
and publisher URLs may have different terms, file sizes, and failure modes.

## Download Flow

1. Plan from explicit candidates.
2. Create local expiring grant.
3. For each candidate:
   - check duplicate status;
   - issue a bounded HEAD request when available;
   - verify content length against limits;
   - verify content type when available;
   - download to a temporary file under inbox;
   - compute checksum;
   - atomically move to final inbox path if no overwrite conflict;
   - write proposal metadata;
   - append audit event.
4. Write final manifest.

If HEAD is unavailable or content length is missing, the downloader must enforce
streaming byte limits and abort once limits are exceeded.

## Duplicate Behavior

Duplicate checks should use:

- arXiv ID;
- DOI if present;
- normalized title;
- existing inbox proposal metadata;
- existing summary records;
- existing raw PDF filenames.

Default behavior is `skip_existing`. A future `record_duplicate_proposal` mode
may write metadata without downloading a second file.

## Cleanup Behavior

- Temporary partial files must be removed after failed downloads.
- Manifest must record failure reason.
- Audit log must record start/failure/cleanup.
- Successful downloads must not be overwritten by reruns.

## Required Tests Before Enabling

- max file count rejection;
- total byte limit rejection;
- per-file byte limit rejection;
- streaming abort cleanup;
- duplicate skip;
- no overwrite;
- checksum recorded;
- proposal metadata written;
- manifest/audit written;
- no review approval;
- deterministic tests use monkeypatched network responses only.

## MCP Exposure Policy

Do not expose `ra_run_pdf_batch_intake` or similar MCP tools until:

- the above tests pass;
- docs describe byte limits and inbox-only behavior;
- release-report identifies PDF batch intake as experimental or disabled;
- one tiny live smoke is explicitly approved and recorded.

The current precondition checklist is maintained in
`docs/validation/local_mcp_write_surface_preconditions.md`.
