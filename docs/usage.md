# Usage

`research-assistant` is currently an individual local research tool with
Git-based sharing. It is not a shared database, hosted service, SSO/RBAC system,
real-time collaboration tool, or hosted UI.

## Local MCP Adapter

The next integration target is a local stdio MCP adapter. It remains an
individual-machine adapter over the existing workspace, not a hosted service.
The default MCP mode is read-only; write-capable arXiv batch intake requires a
bounded local grant and audit trail.

See `docs/architecture/local_mcp_adapter.md` and `docs/mcp.md`.

## Source Checkout Helpers

When working from a source checkout, use the repo-local helpers instead of
typing `PYTHONPATH=src python -m ...` repeatedly:

```bash
scripts/ra-dev version
scripts/ra-dev --root /tmp/research-assistant-demo demo setup
scripts/ra-dev --root /tmp/research-assistant-demo release-report
scripts/ra-mcp-dev --root /tmp/research-assistant-demo
```

For agents or maintainers running common checks:

```bash
scripts/ra-agent release-report
scripts/ra-agent release-report --root /tmp/research-assistant-demo
scripts/ra-agent mcp-status
scripts/ra-agent review-write-status
scripts/ra-agent fast-tests
scripts/ra-agent focused-tests
scripts/ra-agent diff-check
```

These helpers only remove source-checkout friction. They do not turn live
network actions, review mutation, PDF downloads, restore, merge apply, or
destructive operations into silent actions. Those still require explicit user
approval, explicit CLI confirmation, or a bounded local grant.

## Core Local Workflow

```bash
ra init
ra doctor --matrix
ra privacy status
ra demo setup
ra demo run
ra release-report
```

Use `--root <path>` to run commands against a specific workspace.

## Paper And Source Inspection

```bash
ra ingest --arxiv-id 2401.00001 --query "paper title or identifying query"
ra source-fetch --arxiv-id 2401.00001
ra source-show --paper-id paper_example
ra source-sections --paper-id paper_example
ra source-equations --paper-id paper_example
ra source-theorems --paper-id paper_example
ra source-citations --paper-id paper_example
ra source-bibliography --paper-id paper_example
ra source-macros --paper-id paper_example
```

arXiv LaTeX source is the preferred audit substrate when available. PDF parser
output remains fallback and cross-check material.

When to use `source-fetch` first:
- when the paper is already known and available on arXiv;
- when you need to verify mathematical derivations or exact equation wording;
- when you want section structure, citation keys, or theorem/equation blocks
  from source rather than from parser heuristics;
- when you are auditing a chapter, derivation note, or code path against what a
  paper explicitly claims.

For mathematical review, source-first inspection is usually the higher-trust
workflow. PDF parsing remains useful as fallback and cross-check material, not
as a replacement for source when source is available.

## PDF Parser Diagnostics

```bash
ra parser-tool-matrix
ra parser-benchmark-smoke
ra parse-pdf --pdf /path/to/paper.pdf
```

These commands report local tool availability, fixture-smoke behavior, parser
disagreements, and capability limits. Parser scientific accuracy is not
certified; review parsed evidence before relying on it.

## Review And Export

```bash
ra find --query "transport maps"
ra show --paper-id paper_example
ra review-list
ra review-show --paper-id paper_example
ra review-mark --paper-id paper_example --status approved
ra export-context --review-status approved --output /tmp/paper_context.json
```

Human review decisions are explicit. Machine extraction and generated proposals
do not automatically become accepted `technical_audit` conclusions.

## Topic-Only Literature Discovery

For the retrieval-only multi-provider seed queue:

```bash
scripts/ra-dev survey seed-papers \
  --topic "Causal inference with instrumental variables" \
  --out /tmp/ra-seed-papers \
  --confirm-public-discovery
```

The output distinguishes selected candidates, identity conflicts, capped
frontiers, empty providers, and unavailable providers. It does not prove
centrality. Pass chosen `selected_paper_ids` as repeated `--seed` values to
`run-public-source-workflow` before making scholarly claims. `central-papers`
currently runs its own discovery and does not import `seed_report.json`.
Google Scholar is not queried automatically.

For a controlled compound topic, retain scope and terminology in the campaign
contract instead of relying on silent synonym invention:

```bash
scripts/ra-dev survey seed-papers \
  --topic "Reinforcement learning for recommender systems in financial products and credit cards" \
  --required-facet "reinforcement learning" \
  --required-facet "recommender systems" \
  --required-facet "financial products and credit cards" \
  --alias "contextual bandits" \
  --exclude "portfolio optimization" \
  --scope-note "Sequential personalization of financial-product and card recommendations." \
  --out /tmp/ra-seed-papers \
  --confirm-public-discovery
```

The selector fills required facet slots first, then role slots for
`FOUNDATIONAL`, `DIRECT_METHOD`, `SURVEY_OR_TUTORIAL`, `COMPETITOR`, and other
metadata-only hypotheses. Abstract and concept matches remain separate from
title matches. Citation counts, recency, provider agreement, and optional
venue metrics only prioritize the inspection queue.

After replay validation, hand the selected identities to the explicit-seed
workflow without manual copying:

```bash
scripts/ra-dev survey continue-seeds \
  --seed-campaign /tmp/ra-seed-papers \
  --out /tmp/ra-seed-inspection
```

`seed_handoff.json` binds the seed campaign, report, manifest, exact selected
IDs, and child mission artifacts. A venue-enriched campaign must be resumed or
continued with the same canonical `--venue-metrics-registry` file. The handoff
transfers metadata nominations only; source, safety, technical, snowball, and
human-review gates remain downstream.

The offline raw-provider benchmark is `scripts/run_seed_papers_benchmark.py`.
It is a six-case regression gate, not an externally curated recall estimate.
The separately authorized `scripts/run_seed_papers_live_smoke.py` command
records exact hosts, budgets, response-schema status, provider gaps, and
nonclaims. It tests transport health, not retrieval recall.

```bash
scripts/ra-dev survey run-public-source-workflow \
  --topic "Causal inference with instrumental variables" \
  --seed doi:10.1000/causal-iv \
  --out /tmp/ra-seed-inspection \
  --run-safe-local
```

For the single-command bounded central-paper campaign:

```bash
scripts/ra-dev survey central-papers \
  --topic "Particle filtering for nonlinear state-space models" \
  --out /tmp/ra-central-papers \
  --confirm-public-discovery
```

The output contains immutable campaign/capability contracts, chained
`rounds/` checkpoints, six files under `ledgers/`, centrality evidence and
assessment, `snowball_decision.json`, `campaign_report.json`, and a terminal
hash manifest. `--resume` requires the identical topic and capability. Offline
tests may pass `--observation-bundle`; the strict schema rejects topic-fit,
role, verdict, and evaluator-label fields.

Read the result as a bounded disposition report. `BLOCKED` preserves a
candidate whose source, identity, safety, or provider evidence is missing.
`VALIDATED_CENTRAL` means the recorded evidence passed the hard-veto assessor;
it does not establish literature completeness, scientific correctness, or
publication readiness.

Topic-only missions use a bounded, provider-scoped seed-discovery capability.
The public path always uses the generic strategy. Specialized profiles such as
RL/finance are regression fixtures and are never selected from topic wording.
Use a fresh output root for every live attempt. A venue registry is optional
enrichment; omitting it records venue metrics as unavailable:

```bash
CUDA_VISIBLE_DEVICES=-1 scripts/ra-dev survey run-public-source-workflow \
  --topic "Reinforcement learning for recommender systems in financial products and credit cards" \
  --out /tmp/rl-finance-survey-attempt-1 \
  --run-safe-local \
  --confirm-public-discovery
```

Add `--venue-metrics-registry /absolute/path/to/venue_metrics.json` when a
licensed local registry is available.

If supplied, the registry must use the schema validated by `venue_metrics.py`.
Obtain licensed impact-factor values through the institution and do not
redistribute them with the repository. Citation and venue values are priority
signals only, never technical evidence or a completeness gate.

For a repeatable local process plan, first provide a canonical campaign
snapshot and run:

```bash
scripts/ra-dev survey process-plan \
  --snapshot /path/to/campaign_snapshot.json \
  --out /tmp/topic-process-plan
```

The snapshot supplies its own ordered `coverage_requirements`. The planner has
no domain-specific default matrix. RL/finance snapshots are regression examples
only; any topic may provide a validated coverage contract using the same
schema.

This writes coverage, availability, and next-action JSON without network,
source, PDF, credential, or human-review actions. Open must-cite risks are
prioritized, followed by unresolved coverage requirements in their declared
order; unavailable papers remain in the access/omission queue.

Inspect the bootstrap outcome's aggregate consumption, per-stratum status,
identity conflicts, and capped frontiers. Use `--resume` only with the unchanged
topic, strategy digest, budget, registry digest, and output root. A changed
strategy or budget requires a fresh mission. Across retry roots, maintain one
campaign tally; a fresh root does not reset the research campaign ceiling.
The bootstrap nominates candidates; it does not validate that they are
genuinely central to the topic.

Once candidate identities have checked source anchors, source-safety status,
roles, and independent snowball or survey evidence, run the local evidence
gate:

```bash
scripts/ra-dev survey assess-centrality \
  --topic-contract /path/to/topic_contract.json \
  --evidence /path/to/centrality_evidence.json \
  --out /path/to/mission/centrality
scripts/ra-dev survey mission-plan --mission-root /path/to/mission
```

The standalone assessor is topic-generic and deterministic. It does not fetch
or inspect papers; use `central-papers` when bounded evidence construction is
required. The three-topic benchmark is not a literature-completeness or
universal-recall claim. See `docs/literature_survey_operator_guide.md` for the
evidence fields and verdict boundary.

## Research Artifacts

```bash
ra derivation create --paper-id paper_example --title "Derivation worksheet"
ra experiment checklists
ra experiment create --paper-id paper_example --claim-id claim_1 --checklist-id reproducibility
ra synthesis propose --paper-id paper_example
ra traceability build --paper-id paper_example
```

Derivations, experiments, synthesis proposals, traceability reports, and
readiness outputs are review material. They do not certify mathematical
correctness.

## Showcase: NeuTra To DSGE Survey Chapter

A realistic workflow is to seed a DSGE survey chapter from NeuTra and related
normalizing-flow papers, then keep the literature, architecture taxonomy,
chapter links, code experiments, and review notes in one auditable workspace.

```bash
ra ingest --query "NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport"
ra ingest --query "Normalizing Flows for Probabilistic Modeling and Inference"
ra citation-neighborhood --paper-id neutra_hmc --limit 25
ra audit-note append --paper-id neutra_hmc --field open_questions --value "Does the learned transport remain stable for DSGE posterior ridges?"
ra link-add --paper-id neutra_hmc --target docs/chapters/dsge_normalizing_flows.tex --relationship "supports chapter section on neural transport HMC" --target-type chapter_section
ra synthesis propose --paper-id neutra_hmc --kind survey_chapter_outline
ra traceability build --paper-id neutra_hmc
ra export-context --review-status approved --output /tmp/dsge_flow_chapter_context.json
```

The goal is not automatic survey writing. The goal is a reviewable evidence
trail for writing faster while preserving human judgment.

## Backup And Restore

```bash
ra backup create
ra backup inspect --path /path/to/backup.tar.gz
ra --root /tmp/restore-check backup restore --path /path/to/backup.tar.gz
ra --root /tmp/restore-check backup restore --path /path/to/backup.tar.gz --no-dry-run --confirm-restore
```

Restore is dry-run by default. Overwrite requires an additional opt-in.

## Git Sharing

Before sharing a repository:

```bash
ra repository-hygiene check --strict
```

To inspect another researcher's checked-out repository:

```bash
ra workspace merge --source /path/to/other/repo --dry-run
```

To apply only after review:

```bash
ra workspace merge --source /path/to/other/repo --apply --confirm-merge
ra workspace rebuild-derived
```

Private papers, extracted text, backup archives, credentials, `.codex`,
`.claude`, caches, `build/`, `dist/`, and bytecode must not be committed.

## Release Validation

```bash
scripts/ra-agent fast-tests
scripts/ra-agent focused-tests
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/ra-agent pytest tests/integration/test_individual_release_cli.py -q
scripts/build_release_artifacts.sh
WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl scripts/run_clean_install_smoke.sh
scripts/run_individual_git_release_gate.sh
```

The supported release is a Linux/WSL local tool for one researcher. Tagging and
publication require explicit release-owner approval; external-user and macOS
validation are outside this product scope.
