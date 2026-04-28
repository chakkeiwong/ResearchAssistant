# Git Sharing Workflow

`research-assistant` is an individual local tool. Researchers share work by
exchanging Git repositories or workspace snapshots, not by editing one shared
live workspace.

## Before Sharing

Run:

```bash
ra repository-hygiene check
```

Only share files allowed by `docs/release/shareable_workspace_policy.json`.
Do not commit private PDFs, raw sources, local corpora, backup archives,
credentials, `.codex`, `.claude`, caches, `build/`, or `dist/`.

## Inspect Another Repository

Clone or check out the other repository into a separate directory. Validate it
before importing anything:

```bash
ra --root /path/to/other workspace validate
ra --root /path/to/other repository-hygiene check
```

## Dry-Run Merge

Always start with a dry run:

```bash
ra --root /path/to/mine workspace merge --source /path/to/other --target /path/to/mine
```

The report classifies files as copy candidates, already present, conflicts,
forbidden, rebuildable, or unsupported.

## Apply Safe Imports

Apply only after reviewing the dry-run report:

```bash
ra --root /path/to/mine workspace merge --source /path/to/other --target /path/to/mine --apply --confirm-merge
```

Apply mode copies only non-conflicting shareable artifacts, creates a backup,
and records provenance on imported JSON artifacts.

## Rebuild Derived Artifacts

After importing, rebuild local generated reports:

```bash
ra --root /path/to/mine workspace rebuild-derived
ra --root /path/to/mine workspace validate
ra --root /path/to/mine repository-hygiene check
```

Generated indexes, dashboards, readiness reports, and caches are not canonical
shared state.

## Conflict Policy

Conflicts involving accepted `technical_audit` fields, same artifact IDs with
different content, or same path with different content require human review.
The merge command must not silently approve or overwrite research conclusions.
