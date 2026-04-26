# Literature Analysis Gap Closure Plan — 2026-04-26

## Context

The current workflow can ingest structured arXiv source, expose source evidence, edit basic audit notes, cache depth-1 citation graphs, and generate conservative literature-audit proposals. Remaining gaps are: proposal approval, richer evidence links, deeper graph expansion/quality checks, graph-to-inbox workflow, richer source context, optional rendered cross-checks, a stronger autonomous cycle, MCP/tool surface, and library-scale synthesis.

## Phase 1 — Proposal approval with provenance

Implement `ra literature-audit-approve --paper-id ...` so generated proposals can be selectively copied into accepted `technical_audit` fields while recording provenance. Approval must keep generated evidence reviewable and never imply mathematical verification beyond the selected fields.

Tests: proposal generation -> approval -> review-show/export preserve accepted notes and proposal provenance.

## Phase 2 — Richer audit evidence links

Extend `audit-note` with theorem/citation links and removal of list entries. Add default fields for `relevant_theorems` and `relevant_citations`, preserving existing fields.

Tests: link theorem/citation from source fixture, reject missing source labels, remove list entries.

## Phase 3 — Citation graph depth-2 with guardrails and quality diagnostics

Allow `citation-graph-build --depth 2` with fanout limits and cached artifacts. Add diagnostics for duplicate keys, missing identifiers, and endpoint degradation.

Tests: mocked two-hop graph, fanout cap, duplicate DOI merge, unavailable endpoint preservation.

## Phase 4 — Graph-to-inbox review queue

Add commands to propose downloads from graph nodes and mark graph nodes as pending/rejected/local where possible.

Tests: graph node with OA URL -> inbox proposal -> duplicate signals preserved.

## Phase 5 — Richer evidence context

Add theorem/citation/equation context windows, theorem/proof pairing where available, equation usage sites, and macro usage index.

Tests: fixture returns surrounding section, references, citations, macros, and usage lines.

## Phase 6 — Render/compile cross-check scaffold

Add optional, non-required render/compile diagnostics that are skipped unless tools are available or mocked.

Tests: mocked compile success/failure only; no TeX/Docker required.

## Phase 7 — Stronger autonomous cycle

Upgrade `scripts/run_literature_audit_cycle.sh` with dry-run mode, paper-id inputs, graph/proposal smoke checks, and reset-memo update guidance.

Tests: shell syntax and dry-run fixture execution.

## Phase 8 — MCP/tool surface and library synthesis

After CLI stabilizes, expose MCP-like backend functions and add library-level synthesis reports: method comparison table, assumptions matrix, theorem/result map, open-question clustering.

Tests: backend function unit tests and fixture-based synthesis over multiple local papers.

## Execution loop for every phase

1. Write/adjust focused tests.
2. Implement minimal code.
3. Run focused tests.
4. Audit diff for trust-boundary violations.
5. Tidy code and comments.
6. Update reset memo.
7. Run full suite at coherent checkpoints.
