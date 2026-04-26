# Troubleshooting

For help requests, share diagnostics rather than research data. The support checklist is in `docs/support.md`.

## Check The Install

```bash
ra version
ra doctor
```

`ra doctor` reports Python version, workspace status, configured timeout, offline/provider status, and optional parser tools.

## Workspace Problems

```bash
ra workspace validate
ra workspace repair
ra workspace migrate
```

Repair and migration default to dry-run style reporting. They should explain planned actions before changing data.

## Backup Problems

```bash
ra backup create
ra backup inspect --path local_research/exports/backups/backup.tar.gz
ra backup restore --path local_research/exports/backups/backup.tar.gz
```

Restore defaults to dry-run, so it reports files that would be overwritten without changing them.

## Parser Problems

```bash
ra parser-preflight
ra doctor
ra doctor --matrix
ra parser-tool-matrix
ra parser-benchmark-smoke
```

Missing optional tools are visible diagnostics. They are not treated as hard failures for local metadata, derivation, experiment, backup, or demo workflows.

## Timeout Diagnostics

```bash
ra bounded-workflow diagnostic --workflow parser-run --timeout-seconds 300
```

This writes a local diagnostic artifact under `local_research/jobs/` so a stuck workflow has a recoverable trace instead of a silent hang.

## Restore Problems

```bash
ra backup restore --path backup.tar.gz
ra --root /tmp/restored-workspace backup restore --path backup.tar.gz --no-dry-run --confirm-restore
```

Restore defaults to dry-run. Existing files require `--allow-overwrite`, and overwrite restores create a safety backup by default.

## Corruption Checks

```bash
ra config validate
ra workspace validate
ra backup inspect --path backup.tar.gz
```

Expected corruption modes should return JSON with `status`, `issues`, and suggested next steps rather than raw tracebacks.
