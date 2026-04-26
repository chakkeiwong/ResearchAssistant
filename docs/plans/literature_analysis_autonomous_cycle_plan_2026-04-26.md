# Literature Analysis Autonomous Cycle Plan — 2026-04-26

# Context

The current `research-assistant` pipeline has reached a useful structured-source-first baseline: arXiv LaTeX source can be fetched, flattened, extracted into sections/equations/theorems/citations/macros, surfaced through CLI commands, kept separate from PDF/parser fallback, exported with provenance, and combined with degraded discovery/citation status reporting. The next need is to turn this into a mostly autonomous **literature analysis loop**: read papers, build and expand citation graphs, extract source-linked evidence, propose conservative technical-audit notes, test the workflow, and iterate without frequent human intervention.

The key constraint is trust. The system should automate mechanical extraction, graph construction, candidate note generation, validation, and regression testing, but it should not silently convert machine extraction into accepted mathematical conclusions. Human intervention should be minimized by making the tool produce reviewable proposals, confidence/status fields, and deterministic checks; final approval remains an explicit review state.

# Recommended approach

Implement this as a staged audit-and-implement cycle rather than a single large refactor. Each stage should add a usable workflow slice, tests, and a reset-memo update before moving on.

## Phase 1 — Add editable, source-linked technical audit notes

Goal: make `technical_audit` operator-editable through CLI and link notes to source evidence.

Modify:
- `/home/chakwong/research-assistant/src/research_assistant/cli.py`
- `/home/chakwong/research-assistant/src/research_assistant/query/paper_lookup.py`
- `/home/chakwong/research-assistant/src/research_assistant/query/review.py` if review display needs richer note summaries
- `/home/chakwong/research-assistant/src/research_assistant/schemas/paper_record.py`
- tests in `/home/chakwong/research-assistant/tests/integration/test_cli_commands.py` and `/home/chakwong/research-assistant/tests/unit/test_draft_summary.py`

Reuse:
- `PaperRecord.technical_audit` in `schemas/paper_record.py`
- `FileStore.read_json/write_json` in `storage/file_store.py`
- `source_record_path(...)` in `source/structured_source.py`
- `get_paper_summary(...)` in `query/paper_lookup.py`
- existing review/export preservation in `query/review.py` and `adapters/workspace_exports.py`

Add commands:
- `ra audit-note show --paper-id ...`
- `ra audit-note set --paper-id ... --field objective --value ...`
- `ra audit-note append --paper-id ... --field claimed_results --value ...`
- `ra audit-note link-section --paper-id ... --label sec:...`
- `ra audit-note link-equation --paper-id ... --label eq:...`

Rules:
- Only allow known `technical_audit` fields.
- For `link-section` / `link-equation`, validate labels against `source_extraction` when a structured source record exists.
- Store linked labels in existing list fields such as `relevant_sections` and `relevant_equations`; do not invent human conclusions.
- Return JSON including `updated`, `paper_id`, `technical_audit`, and any validation warnings.

Verification:
- Unit test default audit fields still initialize.
- Integration test: ingest/source-fetch fixture paper → link section/equation → `review-show` → `export-context`; exported context preserves notes and evidence labels.

## Phase 2 — Add evidence-context retrieval commands

Goal: let the autonomous loop retrieve the evidence around a section, equation, theorem, or citation before drafting audit notes.

Modify:
- `/home/chakwong/research-assistant/src/research_assistant/cli.py`
- `/home/chakwong/research-assistant/src/research_assistant/query/paper_lookup.py` or a new small module under `/home/chakwong/research-assistant/src/research_assistant/source/`
- `/home/chakwong/research-assistant/src/research_assistant/source/latex_extract.py` if theorem/equation context needs a small schema addition
- tests in `/home/chakwong/research-assistant/tests/unit/test_latex_source_processing.py` and `/home/chakwong/research-assistant/tests/integration/test_cli_commands.py`

Reuse:
- existing source subcommands in `cli.py`: `source-section`, `source-equation`, `source-theorem`, `source-citations`, `source-bibliography`, `source-labels`, `source-refs`
- existing `raw_latex`, labels, citations, bibliography, macros from `latex_extract.py`

Add commands:
- `ra evidence-context --paper-id ... --label ...`
- `ra evidence-context --paper-id ... --citation-key ...`

Output:
- source block type: section/equation/theorem/citation/bibliography
- raw LaTeX snippet
- labels and nearby references/citations when available
- limitations and provenance

Verification:
- Fixture test for equation label returns equation raw LaTeX and containing section metadata.
- Fixture test for citation key returns citation command plus BibTeX entry.

## Phase 3 — Implement citation graph cache and multi-hop expansion

Goal: move from one-shot citation-neighborhood calls to a local, reproducible graph artifact.

Modify/add:
- `/home/chakwong/research-assistant/src/research_assistant/query/citation_graph.py`
- new module: `/home/chakwong/research-assistant/src/research_assistant/query/citation_cache.py` or equivalent
- `/home/chakwong/research-assistant/src/research_assistant/config.py` if a graph path is needed
- `/home/chakwong/research-assistant/src/research_assistant/cli.py`
- tests in `/home/chakwong/research-assistant/tests/unit/test_discovery.py` and `/home/chakwong/research-assistant/tests/integration/test_cli_commands.py`

Reuse:
- `citation_neighborhood(...)`, `papers_citing(...)`, `papers_cited_by(...)` in `query/citation_graph.py`
- `discover_papers_with_status(...)` and status patterns in `query/discovery.py`
- `FileStore` for graph JSON persistence
- `canonical_paper_id(...)` for stable local node IDs where possible

Add artifact:
- `local_research/graphs/citations/<paper_id>.json`

Graph schema:
- `seed_paper_id`
- `depth`
- `nodes`: paper metadata, local paper id if known, external ids, review status if local
- `edges`: citing/cited direction, source endpoint, provenance, retrieval status
- `source_statuses` and `diagnostics`
- `ranking`: relevance/citation/OA indicators already used in discovery

Add commands:
- `ra citation-graph-build --paper-id ... --depth 1|2 --limit ...`
- `ra citation-graph-show --paper-id ...`
- `ra citation-graph-export --paper-id ... --output ...`

Automation guardrails:
- Default depth should be 1; depth 2 only after passing focused tests because API fanout can grow quickly.
- Cache nodes/edges so reruns do not repeatedly hit remote APIs unless explicitly refreshed.
- Preserve `available` / `empty` / `unavailable` diagnostics from citation endpoints.

Verification:
- Unit tests with mocked citation endpoints for partial and full unavailability.
- Integration test builds graph from mocked neighborhood and verifies graph JSON, edge directions, diagnostics, and export.

## Phase 4 — Add candidate literature-analysis synthesis as proposals, not accepted facts

Goal: generate structured, reviewable analysis proposals from source evidence and graph context without claiming they are verified.

Modify/add:
- new module: `/home/chakwong/research-assistant/src/research_assistant/analyze/literature_audit.py`
- `/home/chakwong/research-assistant/src/research_assistant/cli.py`
- `/home/chakwong/research-assistant/src/research_assistant/adapters/workspace_exports.py`
- tests under `/home/chakwong/research-assistant/tests/unit/` and `/home/chakwong/research-assistant/tests/integration/test_cli_commands.py`

Reuse:
- `get_paper_summary(...)`
- `source_extraction` payloads
- citation graph artifacts from Phase 3
- `technical_audit` schema from Phase 1

Add commands:
- `ra literature-audit-propose --paper-id ...`
- `ra literature-audit-show --paper-id ...`
- optional later: `ra literature-audit-approve --paper-id ... --proposal-id ...`

Proposal payload should separate:
- `paper_claims`: source-linked claims explicitly tied to sections/theorems/equations
- `method_components`: proposal generation, transformed target, force/gradient, MH correction when relevant
- `assumptions`: source-linked assumptions
- `open_questions`: explicit unknowns
- `graph_context`: top citing/cited neighbors with diagnostics
- `limitations`: why the proposal requires review

Important rule:
- Do not write proposal content directly into `technical_audit` as accepted notes. Store it under a separate proposal artifact, then allow operator acceptance in a later command.

Verification:
- Fixture-based proposal test proves the proposal references labels/raw snippets and includes limitations.
- Export test preserves approved notes and optionally includes pending proposals under a separate key.

## Phase 5 — Add the autonomous audit/implement cycle script

Goal: run a low-intervention loop that proposes the next safe action, executes deterministic checks, and writes a reset memo.

Modify/add:
- new script: `/home/chakwong/research-assistant/scripts/run_literature_audit_cycle.sh`
- optional new Python driver: `/home/chakwong/research-assistant/tests/scripts/` or `/home/chakwong/research-assistant/src/research_assistant/analyze/`
- docs/reset memo under ignored `/home/chakwong/research-assistant/docs/plans/` if continuing current convention

Cycle steps:
1. Run targeted unit/integration tests for the current area.
2. Build or refresh citation graph from cached/mocked-safe paths unless explicitly allowed to hit remote APIs.
3. Generate literature-audit proposals for selected paper IDs.
4. Run `ra show`, `ra review-show`, `ra export-context` smoke checks.
5. Run `scripts/run_tests.sh` before checkpoint.
6. Update reset memo with: commands run, pass/fail, changed behavior, known gaps, next safe step.
7. Commit only when the user explicitly requests commit, preserving the existing git safety policy.

Verification:
- Script dry-run test or shellcheck-style smoke test.
- Integration fixture test that exercises the cycle on mocked local data without network.

## Phase 6 — Broaden end-to-end scenario tests

Goal: create one realistic test that proves the full literature workflow stays usable under degraded remote conditions.

Add/extend:
- `/home/chakwong/research-assistant/tests/integration/test_cli_commands.py`
- fixtures under `/home/chakwong/research-assistant/tests/fixtures/latex_sources/`

Scenario:
1. Fetch mocked arXiv source.
2. Ingest paper and expose `source_extraction`.
3. Retrieve evidence context for a section/equation/theorem/citation.
4. Set/link technical audit notes.
5. Build citation graph with one endpoint unavailable and one empty/available.
6. Run `download-paper` with degraded discovery.
7. Show inbox proposal and duplicate review signals.
8. Generate literature-audit proposal.
9. Mark paper approved.
10. Export context and verify notes, source evidence, graph diagnostics, and review status survive.

Verification:
- This test should not use live network, TeX, Docker, or MCP.
- Full deterministic suite must pass after each phase.

# Test and audit loop for every phase

For each phase, use this cycle:

1. Add or update a focused failing test for the desired behavior.
2. Implement the smallest code change that satisfies it.
3. Run focused tests for the touched area.
4. Run `scripts/run_tests.sh` before any checkpoint.
5. Update the reset memo with:
   - what changed,
   - tests run,
   - remaining risk,
   - next step.
6. Commit only when requested.

# Critical acceptance criteria

- Paper analysis remains source-linked and reviewable; no machine proposal is silently treated as a human-verified conclusion.
- Citation graph generation is cached, provenance-rich, and degradation-aware.
- The workflow can run on local fixtures without network or external services.
- Every new command returns JSON suitable for downstream automation.
- Full-suite tests pass after each coherent phase.
- The reset memo remains the durable handoff for autonomous continuation.
