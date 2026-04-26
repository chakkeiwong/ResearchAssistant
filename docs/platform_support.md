# Platform Support

## Tier 1

Linux with Python 3.10 or newer.

## Tier 2

macOS with Python 3.10 or newer. Optional parser tools may require platform-specific installation steps.

## Tier 3

Windows through WSL. Native Windows is untested for the shell-script release workflow.

## Validation

Run:

```bash
ra platform-status
scripts/run_clean_install_smoke.sh
```

The `.sh` scripts require a POSIX shell.
