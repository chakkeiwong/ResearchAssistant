# Quickstart

Working from a source checkout? Use `scripts/ra-dev` as the no-install form of
`ra`; it sets `PYTHONPATH=src` automatically.

## Try The Demo

```bash
ra --root /tmp/research-assistant-demo demo setup
ra --root /tmp/research-assistant-demo demo run
ra --root /tmp/research-assistant-demo release-report
ra --root /tmp/research-assistant-demo backup create
```

Source-checkout equivalent:

```bash
scripts/ra-dev --root /tmp/research-assistant-demo demo setup
scripts/ra-dev --root /tmp/research-assistant-demo demo run
scripts/ra-dev --root /tmp/research-assistant-demo release-report
scripts/ra-dev --root /tmp/research-assistant-demo backup create
```

The demo creates a fixture paper, a derivation worksheet, experiment evidence, a traceability report, governance/model-policy records, readiness output, and a backup archive. It uses local deterministic data only.

## Start Your Own Workspace

```bash
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor
ra --root ~/research-assistant-workspace privacy status
```

Then ingest or inspect papers:

```bash
ra --root ~/research-assistant-workspace ingest --pdf ~/papers/example.pdf --query "paper title"
ra --root ~/research-assistant-workspace find --query "transport maps"
ra --root ~/research-assistant-workspace show --paper-id paper_example
```

Generated derivations, synthesis, graph reports, benchmark reports, and readiness records are review material. They do not certify mathematical correctness.

## Start A Literature Survey Mission

Topic-only start:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --out /tmp/ra-survey-topic
```

This records an empty original seed list and stops at the public-discovery
confirmation. To record the confirmation and observe the currently unavailable
live topic-bootstrap boundary:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --out /tmp/ra-survey-topic \
  --resume \
  --confirm-public-discovery
```

The expected local default outcome is
`terminal_blocked_bootstrap_unavailable`. That is an honest terminal, not a
request for a credential and not evidence of live topic-discovery quality.

Explicit arXiv seed with local-only evidence skeleton:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --seed arxiv:2201.12220v3 \
  --out /tmp/ra-survey-seed \
  --run-safe-local
```

Resume an unchanged explicit-seed mission with the same topic, seed, output
root, and `--run-safe-local` plus `--resume`. If those identity fields or the
active discovery budget change, resume fails closed; start a fresh versioned
mission root under the new contract.

Record a bounded qualitative note:

```bash
ra survey qualitative-assessment \
  --subject-id arxiv:2201.12220v3 \
  --assessment-type paper \
  --summary "A direct neural OT method with scoped theoretical and empirical evidence." \
  --merit "The method targets transport maps and plans directly." \
  --concern "A saddle-point solution is not automatically an optimal stochastic map." \
  --uncertainty "Forward-citation coverage is unavailable." \
  --evidence-ref "path/to/checked/source.tex:153" \
  --next-action "Inspect the exact theorem and limitation passages before drafting a claim." \
  --out /tmp/ra-survey-seed/assessment.json
```

See `docs/literature_survey_operator_guide.md` before interpreting mission
states or writing survey prose.

## Share Through Git

Before committing a workspace for another researcher to inspect, run:

```bash
ra --root ~/research-assistant-workspace repository-hygiene check --strict
```

To import from another checked-out repository, start with a dry run:

```bash
ra --root ~/research-assistant-workspace workspace merge --source /path/to/other/repo --target ~/research-assistant-workspace
```

Apply only after reviewing the report:

```bash
ra --root ~/research-assistant-workspace workspace merge --source /path/to/other/repo --target ~/research-assistant-workspace --apply --confirm-merge
ra --root ~/research-assistant-workspace workspace rebuild-derived
```

See `docs/workflows/git_sharing_workflow.md` for the short policy and
`docs/workflows/git_sharing_walkthrough.md` for the full first-time path.

## Get Help Safely

If something fails, run diagnostics on the demo or an empty workspace first and share only non-private output. See `docs/support.md` for the support checklist and private-data boundary.
