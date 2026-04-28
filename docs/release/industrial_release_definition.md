# Individual Git Release Definition

## Current Release Target

The current target is an industrial-quality **individual local tool** with
Git-based sharing. A researcher works in a private local workspace. Sharing
happens by publishing, cloning, or importing Git repositories or workspace
snapshots.

This replaces the previous assumption that the next release must become a
multi-user department platform.

## Release Levels

### Limited Individual Pilot

- One researcher or close colleague.
- Local files are the working store.
- Wheel or source checkout install.
- Git sharing may be manual.
- External platform validation may be incomplete if limitations are explicit.

### Broad Individual Release

- Multiple researchers can install and use independent local workspaces.
- Requires clean install smoke, docs a new user can follow, backup/restore
  rehearsal, parser-tool degradation checks, privacy checks, bounded local
  performance, release notes, and support boundary.

### Git-Shared Research Release

- Researchers can exchange repositories or workspace snapshots.
- Requires repository hygiene checks, shareable workspace policy, merge dry-run,
  merge apply with backup/confirmation, provenance on imported artifacts, and
  post-merge rebuild/validation.

### Future Multi-User Platform

- Shared database, service deployment, SSO/RBAC, real-time collaboration,
  hosted UI, department operations, and production security review are deferred.
- These are future-product concerns, not blockers for the current individual
  Git-sharing release target.

## Storage Model

Local files are canonical. Git is the sharing, review, rollback, and backup
layer. Git is not treated as a transactional database.

Generated indexes, dashboards, readiness reports, and caches should be rebuilt
after checkout or merge. They are not authoritative shared state.

## Trust Boundary

Generated text, parser output, benchmark output, derivation worksheets,
experiment records, traceability reports, LLM outputs, merge reports, and
readiness reports are review material. They do not certify mathematical
correctness, parser accuracy, experiment reproducibility, or code correctness.

Merge/import must not silently overwrite accepted review conclusions or promote
generated content into accepted `technical_audit` facts.

## Current Decision

The project remains a limited individual pilot until the individual Git release
gate records clean repository hygiene, merge/import safety, final validation,
external validation where available, and release-owner tag/publication approval.
