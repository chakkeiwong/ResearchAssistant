# SurveyBench Agent Trial Prompt Packet - 2026-06-28

## Purpose

Evaluate whether an agent can produce machine-checkable citation-map artifacts
before writing literature-survey prose.

This is an offline synthetic fixture trial. It is not a live literature search,
not a Neural Optimal Transport survey, and not evidence of real paper coverage.

## Agent Task

Given the task file:

```bash
tests/fixtures/surveybench/tasks/neural_ot_seed_synthetic.task.json
```

produce the required SurveyBench output JSON files in an output directory:

- `expected_citation_map.json`
- `expected_candidate_ledger.json`
- `expected_source_support.json`
- `expected_claim_support.json`
- `expected_omission_risk.json`

The output must be citation-map artifacts first. Do not write survey prose
until the JSON artifacts score as `passed`.

## Allowed Inputs

- task JSON;
- fixture discovery JSON;
- fixture citation graph JSON;
- anchor inventory JSON;
- local synthetic source fixture under `tests/fixtures/surveybench/`.

## Forbidden Actions

- live web search;
- API metadata lookup;
- paper downloads;
- private file access;
- using Claude or another model as execution authority;
- writing prose instead of producing JSON artifacts.

## Required Command

Score the output directory with the working-tree CLI:

```bash
PYTHONPATH=src python -m research_assistant.cli surveybench run \
  --task tests/fixtures/surveybench/tasks/neural_ot_seed_synthetic.task.json \
  --actual-dir <OUTPUT_DIR> \
  --output <REPORT_JSON>
```

The trial passes only if:

- the command exits with status `0`;
- `<REPORT_JSON>` has `schema_version: ra-surveybench-report-v1`;
- `<REPORT_JSON>` has `status: passed`;
- no `vetoes` or `errors` are present.

## Expected Handoff

Record:

- output directory path;
- report JSON path;
- command actually run;
- exit status;
- whether citation-map JSON was produced before prose;
- any tool ambiguity, missing hint, or boundary-risk observed.
