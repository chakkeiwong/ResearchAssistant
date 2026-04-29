# Vetted Validation Scripts

These scripts provide stable, reviewed command entry points for Claude Code and manual terminal use.

## Scripts

```text
scripts/run_tests.sh
scripts/run_parser_preflight.sh
scripts/run_clean_ingest_palazzo.sh
```

## Product release checklist

Before treating a local build as product-ready for v0.1, run:

```bash
scripts/run_tests.sh
scripts/run_parser_preflight.sh
scripts/run_clean_ingest_palazzo.sh
python tests/scripts/run_parser_benchmark.py
```

`scripts/run_clean_ingest_palazzo.sh` is now a deterministic pytest wrapper. It
does not require a private Palazzo PDF or any file under a maintainer's
`local_research/papers/raw/` directory.

The parser benchmark and smoke checks report fixture counts, aggregate scores,
missing PDFs, parser/tool availability, and whether fixture evidence is ready to
act as a release gate. These checks are availability and regression checks, not
scientific parser-certification evidence.

## Recommended Claude Code permissions

If a local Claude Code configuration needs explicit script allow-rules, use
repository-relative command patterns for your checkout rather than hard-coded
personal paths. For example:

```json
"Bash(scripts/run_tests.sh)",
"Bash(scripts/run_tests.sh *)",
"Bash(scripts/run_parser_preflight.sh)",
"Bash(scripts/run_parser_preflight.sh *)",
"Bash(scripts/run_clean_ingest_palazzo.sh)",
"Bash(scripts/run_clean_ingest_palazzo.sh *)"
```

## Why use scripts instead of long ad hoc commands?

- easier for Claude Code's permission system to classify
- easier to review manually
- safer than broad shell permissions
- repeatable validation workflows
- fewer accidental environment mistakes

## What each script does

### `run_tests.sh`
Runs deterministic unit and integration tests:

```bash
timeout "${TIMEOUT_SECONDS:-300}s" python -m pytest tests/unit tests/integration -q
```

### `run_parser_preflight.sh`
Runs parser availability diagnostics and reports each parser workflow's current
capability limits for section headings, equations, and citations:

```bash
ra parser-preflight
ra doctor --matrix
ra parser-tool-matrix
ra parser-benchmark-smoke
```

### `run_clean_ingest_palazzo.sh`
Runs the parser-consensus identity regression:

```bash
python -m pytest tests/integration/test_cli_commands.py::test_cli_ingest_palazzo_uses_parser_consensus -q
```

The test constructs a sanitized temporary fixture and monkeypatched parser
outputs. It verifies parser-consensus identity behavior without requiring a
private PDF.
