# Platform Support

## Validated During Rollout

- 2026-04-27: Linux/WSL2, `x86_64`, Python 3.11.15, POSIX shell scripts available. Local platform probe returned `status: ok` and `support_tier: tier_1_linux_wsl`.
- 2026-04-28: individual Git release local validation evidence format, fixture merge rehearsal, strict repository hygiene, and synthetic Git workspace performance were added. This is local-machine evidence unless a record explicitly says `scope: real_external` or `scope: external_machine`.
- 2026-04-29: explicit-wheel clean install smoke passed on Linux/WSL2 with Python 3.11.15 for wheel SHA256 `d7c61cc8d4a79826a08754aee923be16065d3744bdcb316b797e74ffd71f03d6`.

## Tier 1

Linux or Linux through WSL with Python 3.10 or newer. Release shell scripts require a POSIX shell.

## Tier 2

macOS with Python 3.10 or newer. Optional parser tools may require platform-specific installation steps. This remains a pilot target until a macOS clean-install smoke is recorded.

## Tier 3

Windows through WSL. Native Windows is untested for the shell-script release workflow and should not be advertised as supported.

## Validation

Run:

```bash
ra platform-status
scripts/run_clean_install_smoke.sh
env WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh
ra individual-git-release validation-record --validation-type macos --result passed --scope external_machine --platform "macOS <version>" --python-version "<python>" --install-method "<wheel or source>" --command-summary "clean install smoke completed"
```

The `.sh` scripts require a POSIX shell.
