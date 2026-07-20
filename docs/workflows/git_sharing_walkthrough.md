# Git Sharing Walkthrough

This walkthrough is for one researcher importing sanitized artifacts from
another researcher's Git checkout. It assumes local file storage and Git-based
sharing only.

## Install Or Check Out

From a wheel:

```bash
python -m pip install research_assistant-0.1.0-py3-none-any.whl
ra version
```

From a source checkout:

```bash
python -m pip install .
ra version
```

## Initialize Your Workspace

Use a private workspace path:

```bash
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor --matrix
ra --root ~/research-assistant-workspace privacy status
```

## Inspect A Small Workspace

The demo is safe synthetic data:

```bash
ra --root ~/research-assistant-demo demo setup
ra --root ~/research-assistant-demo demo run
ra --root ~/research-assistant-demo workspace validate
ra --root ~/research-assistant-demo release-report
```

## Check What Is Safe To Share

Before committing a research workspace, run:

```bash
ra --root ~/research-assistant-workspace repository-hygiene check --strict
```

Only commit shareable JSON artifacts described by
`docs/release/shareable_workspace_policy.json`. Do not commit private PDFs,
raw source trees, extracted paper text, backup archives, `.codex`, `.claude`,
caches, `build/`, `dist/`, credentials, provider keys, tokens, or private local
paths.

## Commit Shareable Artifacts

Review the hygiene report before `git add`. Generated indexes, readiness
reports, merge reports, validation evidence, and performance reports are
review material. Rebuild them after checkout rather than treating them as
accepted research conclusions.

## Clone Another Research Repository

Keep the other repository separate from your workspace:

```bash
git clone <repository-url> ~/other-research-assistant-workspace
ra --root ~/other-research-assistant-workspace workspace validate
ra --root ~/other-research-assistant-workspace repository-hygiene check
```

## Dry-Run The Merge

Start with a report:

```bash
ra --root ~/research-assistant-workspace workspace merge \
  --source ~/other-research-assistant-workspace \
  --target ~/research-assistant-workspace
```

Read the `files` rows. Safe imports are `copy_candidate`. Research conflicts,
forbidden files, same-path differences, and accepted `technical_audit`
differences require human review.

## Apply Safe Imports

Apply only after reviewing the dry-run:

```bash
ra --root ~/research-assistant-workspace workspace merge \
  --source ~/other-research-assistant-workspace \
  --target ~/research-assistant-workspace \
  --apply \
  --confirm-merge
```

Apply mode creates a backup first and records import provenance on copied JSON.
It refuses unresolved blockers or conflicts.

## Rebuild Derived Reports

After import:

```bash
ra --root ~/research-assistant-workspace workspace rebuild-derived
ra --root ~/research-assistant-workspace workspace validate
ra --root ~/research-assistant-workspace repository-hygiene check --strict
```

## Resolve Conflicts Manually

For accepted audit conflicts, compare both records, decide what you trust, and
edit your local accepted review fields explicitly. Do not let generated
proposals, parser output, benchmark output, or another repository's merge
artifact become accepted mathematical conclusions without review.

## Backup And Restore

Create a backup before major imports:

```bash
ra --root ~/research-assistant-workspace backup create
```

Restore starts as dry-run:

```bash
ra --root ~/restore-check backup restore --path /path/to/backup.tar.gz
```

Real restore requires `--no-dry-run --confirm-restore`; overwrites require
`--allow-overwrite`.

## Record Release Evidence

Local release maintainers can record sanitized evidence:

```bash
ra --root ~/research-assistant-workspace individual-git-release validation-local
ra --root ~/research-assistant-workspace individual-git-release fixture-rehearsal
ra --root ~/research-assistant-workspace individual-git-release performance --synthetic-count 100
ra --root ~/research-assistant-workspace individual-git-release validation-report
ra --root ~/research-assistant-workspace individual-git-release gate-build
```

This is a local Linux/WSL workflow. Tagging or publication remains blocked until
the release owner explicitly approves it; no external-user validation is
required for this product.
