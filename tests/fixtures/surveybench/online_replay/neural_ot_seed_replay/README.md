# Neural OT Online-Replay Fixture

This fixture simulates an online literature-survey workflow for:

`Neural Optimal Transport for generative modeling and inference`

It is offline and deterministic. It does not make live web, API, or download
calls.

## Agent-Visible Files

- `neural_ot_seed_replay.task.json`
- `responses/*.json`

These files simulate search, paper lookup, references, citations, adjacent
results, source/download status, source anchors, and evidence context. They do
not contain scorer-only answer packets.

## Scorer-Only Files

- `scorer_packet/*.json`

These files are reserved for later scoring phases. Agents running the replay
task must not inspect them.

## What Is Simulated

- seed lookup for a Neural Optimal Transport seed paper;
- backward lineage through a bibliography/reference surface;
- forward citations through a citing-work surface;
- adjacent-topic candidates;
- duplicate metadata;
- noisy/false-positive adjacent results;
- sparse exact metadata and a simulated rate-limit source status;
- source/download statuses;
- sanitized source anchors and evidence context.

## What Is Not Concluded

This fixture does not establish real Neural OT coverage, real citation counts,
scientific priority, source correctness for public papers, live search quality,
or survey completeness.

