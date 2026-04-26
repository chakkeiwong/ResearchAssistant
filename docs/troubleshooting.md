# Troubleshooting

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

Restore is dry-run only in this release slice, so it reports files that would be overwritten without changing them.

## Parser Problems

```bash
ra parser-preflight
ra doctor
```

Missing optional tools are visible diagnostics. They are not treated as hard failures for local metadata, derivation, experiment, backup, or demo workflows.

## Timeout Diagnostics

```bash
ra bounded-workflow diagnostic --workflow parser-run --timeout-seconds 300
```

This writes a local diagnostic artifact under `local_research/jobs/` so a stuck workflow has a recoverable trace instead of a silent hang.
