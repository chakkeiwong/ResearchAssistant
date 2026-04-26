# Installation

This release target is for one colleague using one private local workspace. It does not require a server, SSO, shared database, or live LLM provider.

## Developer Install

```bash
python -m pip install -e .
ra --help
ra version
```

## User Install From A Checkout

```bash
python -m pip install .
ra --help
ra init
ra doctor
```

## Install From A Wheel

After a maintainer builds release artifacts:

```bash
scripts/build_release_artifacts.sh
python -m pip install dist/research_assistant-0.1.0-py3-none-any.whl
ra version
```

The release artifact manifest is written to `dist/release_artifacts_manifest.json` and includes SHA256 hashes.

## Clean Install Smoke

```bash
scripts/run_clean_install_smoke.sh
```

This creates a temporary virtual environment, installs the package, and runs the demo lifecycle from the installed `ra` console script.

Optional parser tools such as `pdftotext`, `markitdown`, `marker_single`, and `magic-pdf` are detected by `ra doctor`. They are reported as optional unless a workflow explicitly depends on them.

## First Workspace

```bash
ra init
ra workspace validate
ra privacy status
```

Local files are written under `local_research/` and `.research-assistant/` in the selected root. Use `--root /path/to/workspace` to keep a workspace outside the source checkout.
