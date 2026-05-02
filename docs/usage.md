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

Broad release still requires real fresh-reader onboarding, real macOS
validation, real minimal parser-tool machine validation, release-owner tag
approval, and release-owner publication approval. Until those are recorded, the
release remains pilot-scoped.
