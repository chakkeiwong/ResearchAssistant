# Release Notes Template

## Version

`0.1.0`

## Date

YYYY-MM-DD

## Install Artifact

- Wheel:
- Source distribution:
- SHA256 hashes:

Primary local install path:

```bash
python -m pip install research_assistant-X.Y.Z-py3-none-any.whl
ra version
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor
```

## Supported Platforms

- Linux:
- WSL2:

## Validation Results

- `scripts/run_fast_tests.sh`:
- `scripts/run_bounded_tests.sh`:
- `scripts/run_release_smoke.sh`:
- `scripts/run_packaging_smoke.sh`:
- `scripts/run_clean_install_smoke.sh`:
- `ra repository-hygiene check --strict`:
- `ra individual-git-release validation-local`:
- `ra individual-git-release fixture-rehearsal`:
- `ra individual-git-release performance`:
- `ra individual-git-release validation-report`:
- `ra individual-git-release gate-build`:
- Release-owner tag/publication approval:

## Privacy

Default workflows are offline and provider-disabled. Validation evidence must
not include private titles, private paths, credentials, provider keys, tokens,
backup archives, or raw papers.

## Git Sharing

This release target is an individual local tool with Git-based sharing.
Validate a repository before sharing:

```bash
ra repository-hygiene check
```

Import from another checkout with dry-run first:

```bash
ra workspace merge --source /path/to/other/repo --target /path/to/mine
ra workspace merge --source /path/to/other/repo --target /path/to/mine --apply --confirm-merge
ra workspace rebuild-derived
```

Parser smoke is local diagnostic evidence, not scientific extraction-accuracy
certification. Shared database, service deployment, SSO/RBAC, real-time
collaboration, and hosted UI remain future work.

## Backup And Migration Notes

Create a backup before upgrading:

```bash
ra backup create
```

## Known Limitations

See `docs/known_limitations.md`.

## Support

See `docs/support.md`. Do not share private papers, `local_research/`, backup archives, credentials, provider keys, or private paper content in bug reports.
