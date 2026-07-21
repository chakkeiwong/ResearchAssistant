# SurveyBench Stress Restricted Launcher Prompt Packet - 2026-07-03

## Task

You are given a topic and a seed paper. Use only the offline replay commands
below to build a citation map and survey-ready evidence packet.

Topic:

`Neural Optimal Transport for generative modeling and inference`

Seed:

`arxiv:2201.12220`

Task file:

`tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json`

## Allowed Commands

Use a fresh session directory inside the provided workspace.

```bash
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint search --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint paper --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint references --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint citations --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint adjacent --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint download-status --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint source-status --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint source-anchors --session <session-dir>
PYTHONPATH=src python -m research_assistant.cli surveybench replay-call --task tests/fixtures/surveybench/online_replay/neural_ot_seed_ambiguity_partial_frontier_replay/neural_ot_seed_ambiguity_partial_frontier_replay.task.json --endpoint evidence-context --session <session-dir>
```

## Required Output Files

Write these JSON files into one output directory before writing any prose:

- `candidate_ledger.json`
- `citation_map.json`
- `source_support.json`
- `claim_support.json`
- `omission_risk.json`
- `trial_record.json`

The evidence packet files must be based only on replay responses and the event
log in your session directory.

## Required Reasoning Discipline

- Build a typed citation map, not a prose-only answer.
- Resolve ambiguous seed candidates instead of assuming the first title match.
- Include backward lineage, forward citations, adjacent clusters, source
  status, download status, paper classifications, and omission risks.
- Mark source-blocked, metadata-only, quarantined, or partial-frontier papers
  explicitly.
- Record partial forward-frontier continuation risk when the replay surface
  exposes it.
- Technical claims must point to replay source anchors or be marked
  unsupported.
- Forbidden or unsupported claims must not be used as conclusions.

## Non-Claims

Completing this offline replay task does not prove real web coverage, Neural OT
survey completeness, scientific priority, mathematical correctness, production
download reliability, or release readiness.
