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

Optional parser tools such as `pdftotext`, `markitdown`, `marker_single`, and `magic-pdf` are detected by `ra doctor`. They are reported as optional unless a workflow explicitly depends on them.

## First Workspace

```bash
ra init
ra workspace validate
ra privacy status
```

Local files are written under `local_research/` and `.research-assistant/` in the selected root. Use `--root /path/to/workspace` to keep a workspace outside the source checkout.
