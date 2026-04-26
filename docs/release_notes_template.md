# Release Notes Template

## Version

`0.1.0`

## Date

YYYY-MM-DD

## Install Artifact

- Wheel:
- Source distribution:
- SHA256 hashes:

Primary colleague install path:

```bash
python -m pip install research_assistant-X.Y.Z-py3-none-any.whl
ra version
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor
```

## Supported Platforms

- Linux:
- macOS:
- WSL:

## Validation Results

- `scripts/run_fast_tests.sh`:
- `scripts/run_bounded_tests.sh`:
- `scripts/run_release_smoke.sh`:
- `scripts/run_packaging_smoke.sh`:
- `scripts/run_clean_install_smoke.sh`:

## Privacy

Default workflows are offline and provider-disabled.

## Backup And Migration Notes

Create a backup before upgrading:

```bash
ra backup create
```

## Known Limitations

See `docs/known_limitations.md`.

## Support

See `docs/support.md`. Do not share private papers, `local_research/`, backup archives, credentials, provider keys, or private paper content in bug reports.
