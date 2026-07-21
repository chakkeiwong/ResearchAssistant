# Literature Survey Operator Guide

The active workflow is a local, auditable evidence workflow. It preserves
mission identity, source and omission limitations, and concise qualitative
assessments. It does not automatically produce a complete or publication-ready
survey.

## Choose The Input Mode

Topic-only mode preserves an empty original seed list:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --out /tmp/ra-survey-topic
```

The first run should return `status=blocked_at_gate` with
`next_action.action_id=confirm_public_discovery`. The confirmation covers only
the active credential-free arXiv scope. It does not authorize credentials,
private or paid sources, PDF fallback, unbounded crawling, claim promotion, or
public release.

The installed default has no live topic-bootstrap adapter. A confirmed resume
therefore closes with `terminal_blocked_bootstrap_unavailable`, zero effective
seeds, and no provider call. This is a valid honest stop.

Explicit-seed mode accepts an exact paper identifier:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --seed arxiv:2201.12220v3 \
  --out /tmp/ra-survey-seed \
  --run-safe-local
```

`--run-safe-local` builds the deterministic local evidence skeleton and stops
before public metadata or source transport. Inspect `mission_control.json`,
`next_action.json`, and `offline_skeleton/build_manifest.json`.

## Read The Terminal Correctly

- `blocked_at_gate` means the next boundary is explicit and no false progress
  was claimed.
- `terminal_blocked_bootstrap_unavailable` means live topic selection is not
  implemented in the active installed default.
- `ASSESSED_TERMINAL_WITHIN_RECORDED_SCOPE` is an M22 validation state. It
  means the recorded source, omission, and qualitative evidence can be replayed
  coherently. It does not mean truth, completeness, reviewed prose, or expert
  consensus.
- A source-format gap means technical text was not inspected. Metadata or title
  context cannot replace it.
- Forward coverage `unavailable_out_of_scope` is a visible non-blocking
  limitation, not zero citations.

## Write A Qualitative Assessment

Use `ra survey qualitative-assessment` to record:

- one bounded summary;
- merits grounded in inspected evidence;
- concerns about assumptions, scope, failure modes, or overstatement;
- unresolved uncertainties;
- exact evidence paths and line/anchor identifiers; and
- the smallest next action.

Every assessment is written with `claim_support_allowed=false` and
`ready_for_prose=false`. Corrections are ordinary research edits: update the
assessment visibly, retain the evidence reference and reasoning, and rerun the
focused validation. No identity ceremony or approval token is required for a
local correction.

## Resume And Recovery

Resume only with the same topic, seed list, output root, and active discovery
budget:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --seed arxiv:2201.12220v3 \
  --out /tmp/ra-survey-seed \
  --run-safe-local \
  --resume
```

The state manager validates `GENESIS`, `CURRENT`, generation manifests,
artifact hashes, and mission identity before continuing. If the root is stale,
foreign, corrupt, or belongs to a historical provider budget, do not edit its
state files. Preserve it and start a fresh versioned root under the active
arXiv-only contract.

## Current Scientific Boundaries

- Forward-citation coverage is unavailable and non-blocking.
- Fifty identifier-bearing omission risks remain source-uninspected.
- The 195 identifier-free bibliography units do not establish 195 unique
  important papers.
- Official code and publication/retraction status are not checked for all
  assessed papers.
- Five omission-frontier sources have scoped technical inspections; title-only
  grouping for the remaining rows is provisional.
- No method ranking is statistically or scientifically established.

## Privacy And External Actions

Keep paper bodies, private notes, datasets, credentials, browser state, and
`local_research/` out of support bundles. The local operator commands above do
not authorize network dispatch, credential access, PDF fallback, Git push,
release, or public messaging. Request explicit human approval at the actual
external or irreversible boundary.
