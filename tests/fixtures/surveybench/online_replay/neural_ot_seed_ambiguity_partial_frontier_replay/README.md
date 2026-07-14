# Neural OT Ambiguity And Partial-Frontier Replay Fixture

This fixture simulates an offline literature-survey workflow for:

`Neural Optimal Transport for generative modeling and inference`

It is deterministic and makes no live web, API, or download calls.

## Agent-Visible Files

- `neural_ot_seed_ambiguity_partial_frontier_replay.task.json`
- `responses/*.json`

These files simulate search, paper lookup, references, citations, adjacent
results, source/download status, source anchors, and evidence context.

## Reserved Scoring Files

Evaluator-side reference packets are outside the agent-visible task and
response interface. Agents running the replay task must not inspect evaluator
reference material.

## What Is Simulated

- ambiguous seed lookup for a Neural Optimal Transport paper;
- canonical seed selection with a visible rejected version/title variant;
- backward lineage through a bibliography/reference surface;
- forward citation expansion with a visible partial frontier;
- adjacent-topic candidates;
- noisy/false-positive adjacent results;
- metadata-only and blocked source/download states;
- sanitized source anchors and evidence context.

## What Is Not Concluded

This fixture does not establish real Neural OT coverage, real citation counts,
scientific priority, source correctness for public papers, live search quality,
or survey completeness.
