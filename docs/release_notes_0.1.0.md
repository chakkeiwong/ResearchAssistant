# Release Notes 0.1.0

Date: 2026-04-28

## Release Scope

This is a limited pilot release candidate for researchers who want a private local `research-assistant` workspace with Git-based sharing. It is not a shared department server, shared database, live collaboration system, hosted UI, SSO/RBAC system, or default live LLM/provider release.

The candidate should remain pilot-scoped until real colleague onboarding, macOS validation, real minimal-parser-tool validation, release-owner tag approval, and publication approval are recorded.

## Primary Install Path

Recommended colleague path:

```bash
python -m pip install research_assistant-0.1.0-py3-none-any.whl
ra version
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor
```

Developer fallback:

```bash
python -m pip install .
```

The maintainer should build artifacts with:

```bash
scripts/build_release_artifacts.sh
```

The artifact manifest is regenerated at `dist/release_artifacts_manifest.json` and includes SHA256 hashes. Build outputs under `dist/` are not committed to Git.

Current local rollout artifact from the 2026-04-29 build:

- Wheel: `research_assistant-0.1.0-py3-none-any.whl`
- SHA256: `981298e1b0d7610a5e8be2c7a1a353717291d4c309fdfb016db438ab2dfd568c`

## Supported Platforms

- Validated locally on Linux/WSL2 with Python 3.11.15 on 2026-04-27.
- Plain Linux with Python 3.10 or newer is the intended Tier 1 target but should still run the release gate on the target machine.
- macOS with Python 3.10 or newer is a pilot target until a colleague machine completes clean-install smoke.
- Windows through WSL is the supported Windows path. Native Windows shell-script workflow is unvalidated.

## Validation Summary

Release gate commands for this candidate:

```bash
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
PYTHONPATH=src python -m pytest tests/integration/test_individual_release_cli.py -q
ra --root /tmp/research-assistant-final-release individual-git-release validation-substitutes
ra --root /tmp/research-assistant-final-release individual-git-release fixture-rehearsal
ra --root /tmp/research-assistant-final-release individual-git-release performance --synthetic-count 100
ra --root /tmp/research-assistant-final-release repository-hygiene check --strict
ra --root /tmp/research-assistant-final-release individual-git-release validation-report
ra --root /tmp/research-assistant-final-release individual-git-release gate-build
scripts/run_packaging_smoke.sh
scripts/build_release_artifacts.sh
WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl scripts/run_clean_install_smoke.sh
scripts/run_release_smoke.sh
ra --root /tmp/research-assistant-final-release release-report
```

The exact command results for the current candidate are recorded in `docs/plans/reset_memo_2026-04-26.md`.

Local evidence now includes a validation schema under `local_research/governance/individual_git_release/validation/`, deterministic Git-sharing fixture rehearsal, strict repository hygiene, explicit-wheel clean install smoke, and synthetic representative workspace performance through `synthetic_git_1000`. Real external validation and release-owner approval remain blocked/manual when unavailable.

## Git Sharing

Researchers share by exchanging Git repositories or workspace snapshots. The workflow is:

```bash
ra repository-hygiene check --strict
ra workspace merge --source /path/to/other/repo --target /path/to/my/repo
ra workspace merge --source /path/to/other/repo --target /path/to/my/repo --apply --confirm-merge
ra workspace rebuild-derived
```

See `docs/workflows/git_sharing_walkthrough.md`.

## Privacy

Default workflows are offline and provider-disabled. The demo, release-report, parser diagnostics, backup/restore checks, and synthetic performance smoke do not require sending papers or notes to external providers.

## Backup And Restore

Create a backup before relying on a workspace or changing install versions:

```bash
ra --root ~/research-assistant-workspace backup create
```

Restore defaults to dry-run. A real restore requires `--no-dry-run --confirm-restore`; overwriting existing files additionally requires `--allow-overwrite` and creates a safety backup by default.

## Known Limitations

- Generated derivations, experiments, synthesis, traceability, governance, and readiness reports are review material, not mathematical approval.
- Parser quality depends on local optional tools and source/PDF quality.
- Parser-tool availability and degradation are checked, but parser scientific accuracy is not certified.
- A real colleague onboarding trial and macOS validation remain required before broad non-pilot rollout.
- Minimal parser-tool validation on a real minimal machine remains required before broad non-pilot rollout.
- Git-sharing merge/import performance has been measured through `synthetic_git_1000` and does not certify real personal libraries.
- Tagging and artifact publication require explicit release-owner approval.

See `docs/known_limitations.md` and `docs/support.md`.
