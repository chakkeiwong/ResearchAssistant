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

The parser benchmark output includes a `report` block with fixture counts, aggregate scores, missing PDFs, and whether the benchmark corpus is ready to act as a release gate.

## Recommended Claude Code permissions

Add these to `~/.claude/settings.json` under `permissions.allow`:

```json
"Bash(/home/chakwong/research-assistant/scripts/run_tests.sh)",
"Bash(/home/chakwong/research-assistant/scripts/run_tests.sh *)",
"Bash(/home/chakwong/research-assistant/scripts/run_parser_preflight.sh)",
"Bash(/home/chakwong/research-assistant/scripts/run_parser_preflight.sh *)",
"Bash(/home/chakwong/research-assistant/scripts/run_clean_ingest_palazzo.sh)",
"Bash(/home/chakwong/research-assistant/scripts/run_clean_ingest_palazzo.sh *)"
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
python -m pytest tests/unit tests/integration -q
```

### `run_parser_preflight.sh`
Runs parser availability diagnostics and reports each parser's current capability limits for section headings, equations, and citations:

```bash
ra parser-preflight
```

### `run_clean_ingest_palazzo.sh`
Creates a fresh temporary research store and re-runs the local PDF ingest validation for the Palazzo paper.
This is the main regression check for parser-first local PDF ingest behavior.
