# Installation

This release target is for one researcher using one private local workspace. It does not require a server, SSO, shared database, or live LLM provider.

Use Python 3.11.x. The package metadata intentionally rejects Python 3.10 and
Python 3.12+; backward and forward minor-version compatibility are not release
requirements for v0.1.

## Local Install From A Wheel

The recommended release path is a wheel built by the maintainer:

```bash
python -m pip install research_assistant-0.1.0-py3-none-any.whl
ra version
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor
```

The maintainer builds the wheel and manifest with:

```bash
scripts/build_release_artifacts.sh
```

The release artifact manifest is written to `dist/release_artifacts_manifest.json` and includes SHA256 hashes. Build outputs are regenerated for release and are not committed to Git.

## Developer Install From A Checkout

```bash
python -m pip install .
ra --help
ra version
```

For active development:

```bash
python -m pip install -e .
```

## Clean Install Smoke

```bash
scripts/run_clean_install_smoke.sh
```

This creates a temporary virtual environment, installs the package, and runs the demo lifecycle from the installed `ra` console script.

For literature-survey acceptance, the package can be built and installed
offline because the base project declares no runtime Python dependencies:

```bash
python -m build --wheel --no-isolation
python -m venv /tmp/ra-survey-venv
/tmp/ra-survey-venv/bin/python -m pip install --no-index --no-deps \
  dist/research_assistant-0.1.0-py3-none-any.whl
cd /tmp
env -u PYTHONPATH CUDA_VISIBLE_DEVICES=-1 \
  /tmp/ra-survey-venv/bin/ra survey run-public-source-workflow --help
```

Running from outside the checkout with `PYTHONPATH` unset verifies that the
installed wheel, rather than source-worktree imports, supplies the command.

Optional parser tools such as `pdftotext`, `markitdown`, `marker_single`, and `magic-pdf` are detected by `ra doctor`. They are reported as optional unless a workflow explicitly depends on them.

## First Workspace

```bash
ra init
ra workspace validate
ra privacy status
```

Local files are written under `local_research/` and `.research-assistant/` in the selected root. Use `--root /path/to/workspace` to keep a workspace outside the source checkout.

For support and safe diagnostic sharing, see `docs/support.md`.

The current survey default is credential-free arXiv-only. OpenAlex, provider
keys, PDF fallback, and public release are not installation prerequisites.
