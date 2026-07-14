# SurveyBench Online-Replay Agent Trial Prompt Packet - 2026-06-29

## Task

You are given a topic and a seed paper. Use only the offline replay commands
below to build a citation map and survey-ready evidence packet.

Topic:

`Neural Optimal Transport for generative modeling and inference`

Seed:

`arxiv:2201.12220v3`

Task file:

`tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json`

## Allowed Commands

Use a fresh session directory.

```bash
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint search --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint paper --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint references --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint citations --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint adjacent --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint download-status --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint source-status --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint source-anchors --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/neural_ot_seed_replay.task.json --endpoint evidence-context --session <session-dir>
```

## Required Output Files

Write these JSON files into one output directory before writing any prose:

- `candidate_ledger.json`
- `citation_map.json`
- `source_support.json`
- `claim_support.json`
- `omission_risk.json`

The output must be based on replay responses and the event log. Do not use live
web search, raw PDFs, private files, or unstated sources.

## Required Reasoning Discipline

- Build a typed citation map, not a flat list.
- Include backward lineage, forward citations, adjacent clusters, source status,
  download status, classifications, and omission risks.
- Mark source-blocked or metadata-only papers as such.
- Technical claims must point to replay source anchors or be marked unsupported.
- Forbidden or unsupported claims must not be used as conclusions.
- Prose-only answers fail this task.

## Non-Claims

Passing this replay task does not prove real web coverage, Neural OT survey
completeness, scientific priority, mathematical correctness, production
download reliability, or release readiness.

