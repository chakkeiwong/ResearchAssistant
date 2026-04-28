# Individual Git-Based Release Target

## Purpose

`research-assistant` is an industrial-quality **individual research tool**. It
is not currently a shared department server, database-backed collaboration
platform, production RBAC system, or real-time multi-user application.

The release target is a robust local application for one researcher at a time:

- a researcher installs the tool locally;
- the researcher keeps a private local workspace of papers, notes, extracted
  evidence, derivation worksheets, experiments, traceability records, and review
  artifacts;
- all default workflows run offline and store artifacts as local files;
- researchers share work by publishing or exchanging Git repositories or
  workspace snapshots;
- another researcher can check out or import that repository, validate it,
  rebuild generated indexes, and merge selected artifacts into their own
  workspace.

This document is the primary release target for the next release line. Previous
multi-user industrial-platform plans remain useful long-term background, but
they are **not** the primary release goal.

## Product Positioning

The tool should feel like a careful local research assistant for mathematical
finance, economics, computational statistics, machine learning, applied
mathematics, and adjacent technical research.

The release is successful when an individual researcher can:

- install the package or check out the repository;
- initialize a local workspace;
- ingest or register papers without leaking private content;
- inspect source-linked evidence;
- create review notes, derivation worksheets, experiment records, synthesis
  proposals, benchmark runs, and traceability records;
- keep generated/proposed material separate from accepted review conclusions;
- validate, back up, restore, and export the workspace;
- commit a clean Git repository containing only shareable files;
- check out another researcher's repository and import or merge selected
  artifacts safely.

The release is not successful if it requires a database administrator, service
operator, SSO policy owner, shared server deployment, or live provider
credentials.

## Storage Model

The working store is the local filesystem.

Canonical artifacts should be ordinary files:

- JSON for machine-readable records;
- Markdown for human-readable release, support, proposal, and workflow docs;
- one artifact per file where practical;
- deterministic formatting and stable IDs;
- generated indexes and readiness reports that can be rebuilt.

Git is the sharing, versioning, review, rollback, and backup layer. It is not a
transactional database.

The release should support these Git workflows:

- a researcher commits their shareable workspace artifacts to their own Git
  repository;
- another researcher checks out that repository read-only for inspection;
- another researcher imports selected artifacts into their own workspace;
- generated indexes, caches, dashboards, and readiness reports are rebuilt
  after checkout or merge;
- conflicts are reported as research conflicts requiring human resolution, not
  silently overwritten.

## Repository Boundaries

The default repository must never include private or generated local state:

- private PDFs, TeX sources, datasets, paper snapshots, or corpora;
- `local_research/papers/raw/`;
- backup archives;
- credentials, provider keys, tokens, cookies, shell history, or plain secrets;
- `.codex`, `.claude`, caches, bytecode, `build/`, or `dist/`;
- generated indexes that the project marks rebuildable;
- private paper titles or local paths in validation records intended for
  sharing.

Shareable artifacts must carry enough metadata to be useful after checkout:

- schema version;
- stable artifact ID;
- provenance;
- review status;
- generated-vs-approved status;
- limitations;
- source or paper references that do not leak private file paths.

## Trust Boundary

Generated text, parser output, benchmark output, derivation worksheets,
experiment records, traceability reports, LLM outputs, and readiness reports are
review material. They do not certify mathematical correctness, parser accuracy,
experiment reproducibility, or code correctness.

Accepted human review conclusions must remain explicit. A merge/import workflow
must not silently overwrite accepted `technical_audit` fields or promote another
researcher's generated artifacts into local approved conclusions.

## Sharing Model

The only supported sharing model for the next release is Git-based exchange.

Supported:

- clone another research repository;
- inspect it locally;
- validate shareable files;
- import or merge selected records;
- rebuild indexes and readiness reports;
- preserve provenance showing which repository or commit an imported artifact
  came from.

Not supported:

- two people editing the same live workspace at the same time;
- shared database writes;
- server-side locking;
- central RBAC;
- real-time comments or assignments;
- production audit-log service.

Git merge conflicts are acceptable. The tool should reduce them with stable
IDs, deterministic formatting, and one-record-per-file design, then provide a
domain-aware merge report for research artifacts.

## Required Merge/Import Capability

The release needs a workspace merge/import command before Git-based sharing is
comfortable.

The command should start with a dry-run mode, for example:

```bash
ra workspace merge --source /path/to/other/repo --target /path/to/my/repo --dry-run
```

It should later support an explicit apply mode, for example:

```bash
ra workspace merge --source /path/to/other/repo --target /path/to/my/repo --apply
```

The merge workflow must:

- validate source and target workspaces;
- reject or warn on forbidden private files;
- copy non-conflicting shareable artifacts;
- skip generated indexes, caches, dashboards, and readiness reports that should
  be rebuilt;
- detect same-ID/different-content conflicts;
- detect same-paper/different-summary or accepted-audit conflicts;
- preserve imported provenance;
- produce a machine-readable merge report;
- require explicit human resolution for conflicts involving accepted review
  conclusions.

## Release Levels

### Limited Individual Pilot

One developer or close colleague runs the tool locally. The release may rely on
source checkout or a wheel. External platform validation can be incomplete, but
limitations must be explicit.

### Broad Individual Release

Multiple individual researchers can install and use the tool independently.
This level requires:

- clean install smoke from the released artifact;
- Linux/WSL validation and at least one additional target-platform validation
  when available;
- docs that a new user can follow;
- backup/restore rehearsal;
- privacy and forbidden-file checks;
- parser-tool degradation checks;
- bounded performance on representative individual corpus sizes;
- release notes, tag policy, support boundary, and known limitations.

### Git-Shared Research Release

Researchers can exchange Git repositories or workspace snapshots and merge
selected artifacts safely. This level requires everything in the broad
individual release plus:

- shareable workspace contract;
- repository hygiene check;
- workspace merge/import dry-run;
- conflict taxonomy;
- merge apply mode with backup and explicit confirmation;
- provenance for imported artifacts;
- post-merge rebuild and validation workflow.

### Future Multi-User Platform

A shared database, service API, SSO/RBAC, real-time collaboration, hosted UI,
department operations, and production security review are deferred. They may be
considered after the individual and Git-shared release tracks are reliable.

Future multi-user work must be treated as a new product line, not an implicit
requirement for the current release.

## Release Gates

The release gate should move away from blocking on production database, SSO,
service deployment, or multi-user collaboration. Those are future-product
blockers, not blockers for the current release target.

The current release should block on:

- installability;
- workspace validation;
- privacy and forbidden-file hygiene;
- backup/restore safety;
- parser-tool degradation behavior;
- generated-vs-approved trust boundary;
- Git shareability;
- workspace merge/import safety;
- release notes and support docs;
- bounded local performance;
- external validation records where available;
- final clean Git state before tagging or publishing.

## Documentation Scope

Release-facing docs must describe:

- recommended install path;
- local workspace layout;
- what is safe to commit;
- what must never be committed;
- how to validate a checked-out workspace;
- how to import from another researcher's repository;
- how to resolve merge conflicts;
- how to rebuild generated indexes;
- how to back up and restore;
- parser limitations;
- live-provider disabled default;
- support boundary and known limitations.

Docs should not promise:

- production multi-user operation;
- database-backed collaboration;
- central authentication or authorization;
- mathematical correctness;
- parser accuracy certification;
- live LLM/provider behavior by default.

## Definition Of Done

The individual Git-based release is done when:

- `ra release-report` and the revised release gate reflect the individual/Git
  target;
- source and target workspace validation are deterministic;
- repository hygiene checks catch private/generated files before release;
- workspace merge/import dry-run reports copied, skipped, conflicting, and
  forbidden records;
- merge apply mode is backed up, explicit, and covered by tests;
- generated indexes can be rebuilt after checkout/import;
- docs explain the Git sharing workflow end to end;
- release notes clearly state this is an individual local tool;
- final validation passes on bounded deterministic tests;
- tag/publication happens only after explicit release-owner approval.
