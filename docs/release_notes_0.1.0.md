# Release Notes 0.1.0

Date: 2026-04-27

## Release Scope

This is a limited pilot release candidate for colleagues who want a private local research-assistant workspace. It is not a shared department server, shared database, live collaboration system, or default live LLM/provider release.

The candidate should remain pilot-scoped until a real colleague onboarding trial, macOS validation, and missing-parser-tool validation are recorded.

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

Current local rollout artifact:

- Wheel: `research_assistant-0.1.0-py3-none-any.whl`
- SHA256: `0f08de5c7e689d732ad911d5902d9285817e6d6072cefa2b4f203d2f180f27ce`

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
scripts/run_packaging_smoke.sh
scripts/build_release_artifacts.sh
scripts/run_clean_install_smoke.sh
scripts/run_release_smoke.sh
ra --root /tmp/research-assistant-final-release release-report
```

The exact command results for the current candidate are recorded in `docs/plans/reset_memo_2026-04-26.md`.

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
- A real colleague onboarding trial and macOS validation remain required before broad non-pilot rollout.
- Medium-corpus performance is measured with synthetic records and does not certify real personal libraries.

See `docs/known_limitations.md` and `docs/support.md`.
