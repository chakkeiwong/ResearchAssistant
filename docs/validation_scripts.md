# Vetted Validation Scripts

These scripts provide stable, reviewed command entry points for Claude Code and manual terminal use.

## Scripts

```text
scripts/run_tests.sh
scripts/run_static_checks.sh
scripts/run_coverage.sh
scripts/run_external_tool_tests.sh
scripts/run_release_candidate_gate.py
scripts/run_parser_preflight.sh
scripts/run_clean_ingest_palazzo.sh
```

## Product release checklist

Before treating a local build as product-ready for v0.1, run:

```bash
scripts/run_tests.sh
scripts/run_static_checks.sh
scripts/run_parser_preflight.sh
scripts/run_clean_ingest_palazzo.sh
CUDA_VISIBLE_DEVICES=-1 scripts/run_external_tool_tests.sh
python scripts/run_release_candidate_gate.py
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
timeout "${TIMEOUT_SECONDS:-1800}s" python -m pytest tests/unit tests/integration tests/scripts -q
```

This is the active offline unit, integration, regression, and script-test gate.
Historical provider fixtures outside the arXiv-only product contract are
reported as explicit skips rather than treated as current compatibility tests.
The runner sets `CUDA_VISIBLE_DEVICES=-1` before Python import because the
offline regression suite is deliberately CPU-only.

### `run_static_checks.sh`

Runs Python compilation, shell syntax, diff hygiene, Ruff, and focused mypy.
Ruff and mypy run when the Python 3.11 development extra is installed and are
always installed in CI.

### `run_coverage.sh`

Runs the active suite with branch coverage. The report is diagnostic until the
project records and reviews a minimum threshold.

### `run_external_tool_tests.sh`

Runs the installed-parser benchmark under deliberate CPU-only isolation with
`CUDA_VISIBLE_DEVICES=-1`. This is a separate environment gate because optional
parser tools are not base dependencies.

### `run_release_candidate_gate.py`

Runs the bounded release checks and writes source-bound evidence to
`dist/release_gate_evidence.json`. Evidence from failed commands, a non-3.11
runtime, malformed JSON, or changed source is rejected by `ra release-report`.

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
python -m pytest tests/integration/test_cli_library_commands.py::test_cli_ingest_palazzo_uses_parser_consensus -q
```

The test constructs a sanitized temporary fixture and monkeypatched parser
outputs. It verifies parser-consensus identity behavior without requiring a
private PDF.
