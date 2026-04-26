# Reset Memo — 2026-04-24

## Why this memo exists

This memo is a restart point for the current `research-assistant` hardening pass.
It records what has already been implemented, what is now true of the codebase, what remains incomplete, and the recommended next execution order.

The immediate goal remains: make the tool dependable for rigorous local-first literature-audit workflows, especially where operator trust matters more than automation.

---

## Current product posture

The project is no longer just a generic ingest/query POC.
It now has a clearer audit-oriented shape:

1. arXiv LaTeX source is the primary audit substrate when available,
2. PDF parser reconciliation is retained as fallback and rendered-output cross-check,
3. parser-derived trust signals are exposed for inspection,
4. review and export flows preserve conservative operator state,
5. discovery/citation enrichment is useful but still secondary to local evidence,
6. mathematical/audit-specific fields remain explicit placeholders rather than fabricated automation.

This is progress, but the tool is still not ready to claim fully normalized equation extraction, citation extraction from PDFs, or robust remote discovery under upstream failures.

---

## What has been implemented in this pass

### Phase 1 — local-first ingest and inspection trust

Implemented:
- `ra show` now exposes extraction-facing inspection data.
- Extracted text availability and extracted text path are surfaced.
- Parser reconciliation data is surfaced, including:
  - parse confidence,
  - requires-manual-review flag,
  - parser agreement,
  - disagreements,
  - parser outputs used.
- Consensus section headings are surfaced.
- Explicit limitations are shown for:
  - equations,
  - citations.

Relevant files:
- `src/research_assistant/query/paper_lookup.py`
- `tests/integration/test_cli_commands.py`

Meaning:
- an operator can now inspect more of what the parser layer actually produced before trusting a paper record.

### Audit-scenario coverage added

Implemented:
- integration coverage for an audit workflow where citation enrichment is unavailable but the local workflow still proceeds.
- the scenario covers:
  - `show`,
  - degraded `citation-neighborhood`,
  - `review-mark`,
  - `export-context`.

Relevant file:
- `tests/integration/test_cli_commands.py`

Meaning:
- we now have at least one realistic degraded-state scenario instead of only isolated command tests.

### Phase 2 scaffold — audit-oriented fields

Implemented:
- `PaperRecord` now includes `technical_audit`.
- draft summaries initialize explicit empty audit placeholders rather than pretending to auto-extract them.
- `ra show` returns a top-level `technical_audit` block.

Current placeholder fields:
- `transport_definition`
- `objective`
- `transformed_target`
- `claimed_results`
- `derived_results`
- `open_questions`
- `relevant_equations`
- `relevant_sections`
- `assumptions_for_reuse`

Relevant files:
- `src/research_assistant/schemas/paper_record.py`
- `src/research_assistant/summarize/draft_summary.py`
- `src/research_assistant/query/paper_lookup.py`
- `tests/unit/test_draft_summary.py`
- `tests/integration/test_cli_commands.py`

Meaning:
- the system now has explicit structured slots for a skeptical literature reader, while staying honest that these are not auto-filled facts.

### Audit fields carried through review/export

Implemented:
- review views default and preserve `technical_audit` fields.
- exported paper context now preserves `technical_audit` and fills missing defaults.
- review/export tests now cover these fields.

Relevant files:
- `src/research_assistant/query/review.py`
- `src/research_assistant/adapters/workspace_exports.py`
- `tests/unit/test_workspace_exports.py`
- `tests/integration/test_cli_commands.py`

Meaning:
- audit-oriented operator notes can survive through review and downstream export payloads.

### Phase 3 started — discovery degradation reporting

Implemented:
- `discover_papers_with_status(...)` now exists.
- it reports:
  - top-level `status`,
  - merged `results`,
  - per-source `source_statuses`.
- current status distinctions:
  - `available`
  - `empty`
  - `unavailable`
- failures from one source no longer force the whole discovery status to look silently empty.

Relevant files:
- `src/research_assistant/query/discovery.py`
- `tests/unit/test_discovery.py`

Meaning:
- the backend can now distinguish:
  - no papers found,
  - one provider failed but another responded,
  - everything is unavailable.

### Structured-source-first arXiv audit path

Implemented:
- arXiv source records now carry source priority fields in summaries:
  - `primary_source_type`,
  - `structured_source_status`,
  - `structured_source_record_path`.
- `ra show` and exported paper context preserve structured-source artifacts separately from PDF/parser extraction.
- source inspection commands are available for source-derived sections, equations, theorem-like blocks, citations, bibliography, macros, labels, and references:
  - `ra source-sections`, `ra source-section`,
  - `ra source-equations`, `ra source-equation`,
  - `ra source-theorems`, `ra source-theorem`,
  - `ra source-citations`, `ra source-bibliography`, `ra source-macros`, `ra source-labels`, `ra source-refs`.
- LaTeX extraction now preserves section `raw_latex`, nested section titles, section labels, macro argument signatures, and macro definitions.
- arXiv source fetch now records visible degradation for HTTP-unavailable source and malformed source packages.

Relevant files:
- `src/research_assistant/cli.py`
- `src/research_assistant/source/latex_extract.py`
- `src/research_assistant/source/arxiv_source.py`
- `src/research_assistant/schemas/paper_record.py`
- `src/research_assistant/summarize/draft_summary.py`
- `src/research_assistant/adapters/workspace_exports.py`
- `tests/integration/test_cli_commands.py`
- `tests/unit/test_latex_source_processing.py`
- `tests/unit/test_arxiv_source.py`
- `tests/unit/test_draft_summary.py`
- `tests/unit/test_workspace_exports.py`

Meaning:
- mathematical papers with available arXiv LaTeX source now expose inspectable source evidence as the primary audit path while keeping PDF/parser extraction separate as fallback or cross-check.

---

## What is still incomplete

### 1. CLI and download flow are not yet wired to degradation-aware discovery

Right now:
- the backend has `discover_papers_with_status(...)`,
- but CLI commands still mostly use `discover_papers(...)`.

This means operators still do not reliably see degraded-source state when running:
- `ra discover`
- `ra download-paper`

Needed next:
- wire CLI command output to the richer discovery status payload,
- make download flow surface whether failure was:
  - no OA result,
  - remote source unavailable,
  - all sources unavailable,
  - partial-source result.

### 2. Citation neighborhood degradation is only partially modeled

Current state:
- citation neighborhood already returns `available`, `empty`, or `unavailable`,
- tests cover degraded usage in the audit workflow.

Still missing:
- richer status detail for why it is unavailable,
- possibly per-endpoint/source diagnostics analogous to discovery status,
- clearer distinction between upstream no-data vs upstream outage where feasible.

### 3. Audit fields are placeholders only

This is intentional, but still incomplete.

Current state:
- fields exist,
- they survive summary/show/review/export,
- tests assert defaults and persistence,
- structured-source artifacts can identify candidate relevant sections/equations/theorems but do not auto-populate human audit conclusions.

Still missing:
- deliberate ways for operators or future tooling to populate them,
- any structured CLI support for editing or surfacing them beyond raw JSON,
- any conservative linkage between source-derived evidence and `technical_audit` notes.

### 4. No end-to-end scenario yet combines local ingest + remote discovery degradation + inbox workflow

We now have a better degraded audit scenario, but the broader workflow is still missing.

Still desirable:
- local ingest,
- inspection of parser trust,
- degraded discover/download behavior,
- inbox duplicate handling,
- review decision,
- export.

### 5. Parser capability reporting is still incomplete

Still missing from the operator experience:
- a clearer unified capability statement around section headings vs equations vs citations,
- possibly surfaced in parser preflight and/or parser show payloads.

---

## Recommended next execution order

### Completed since the last reset

#### Discovery/download CLI degradation surfaced

Implemented:
- `ra discover` returns degradation-aware JSON from `discover_papers_with_status(...)`.
- `ra download-paper` distinguishes:
  - discovery unavailable,
  - discovery returned no open-access candidates,
  - discovery results exist but no open-access PDF is available.
- CLI integration tests cover degraded discovery, unavailable discovery, empty discovery, and results without OA PDFs.

Verification:
- focused discovery CLI tests passed: `29 passed in 131.78s`.
- full deterministic suite passed after this change: `113 passed in 263.14s`.

### Immediate next task

#### Improve citation-neighborhood degradation diagnostics

Implemented:
- `citation-neighborhood` preserves current `available` / `empty` / `unavailable` status semantics.
- payloads now include `status_reason`.
- payloads now include `diagnostics.unavailable_endpoints`, `diagnostics.available_empty_endpoints`, and `diagnostics.failure_reasons`.
- focused citation/CLI diagnostics tests passed: `29 passed in 140.85s`.
- full deterministic suite passed after this change: `113 passed in 404.04s`.

### Then

#### Expand scenario testing

Add a more complete workflow test covering:
1. local record exists,
2. parser inspection works,
3. remote discovery partially fails,
4. download/inbox result remains reviewable,
5. review/export still function.

---

## Files most relevant at reset

### Core implementation files
- `src/research_assistant/query/paper_lookup.py`
- `src/research_assistant/summarize/draft_summary.py`
- `src/research_assistant/schemas/paper_record.py`
- `src/research_assistant/query/review.py`
- `src/research_assistant/adapters/workspace_exports.py`
- `src/research_assistant/source/arxiv_source.py`
- `src/research_assistant/source/latex_bundle.py`
- `src/research_assistant/source/latex_flatten.py`
- `src/research_assistant/source/latex_extract.py`
- `src/research_assistant/source/structured_source.py`
- `src/research_assistant/query/discovery.py`
- `src/research_assistant/query/citation_graph.py`
- `src/research_assistant/query/downloads.py`
- `src/research_assistant/cli.py`

### Most relevant tests
- `tests/integration/test_cli_commands.py`
- `tests/unit/test_arxiv_source.py`
- `tests/unit/test_latex_source_processing.py`
- `tests/unit/test_draft_summary.py`
- `tests/unit/test_workspace_exports.py`
- `tests/unit/test_discovery.py`
- `tests/unit/test_downloads.py`
- `tests/integration/test_parser_first_ingest_precedence.py`

---

## Verification completed in this pass

Completed and passing during this session:
- targeted structured-source tests:
  - `tests/unit/test_latex_source_processing.py`,
  - `tests/unit/test_arxiv_source.py`,
  - `tests/unit/test_draft_summary.py`,
  - `tests/unit/test_workspace_exports.py`,
  - `tests/integration/test_cli_commands.py`.
- full deterministic test suite via `/home/chakwong/research-assistant/scripts/run_tests.sh`:
  - `110 passed in 244.24s`.

---

## Short restart instruction

If resuming from this memo, do this next:

1. review the current structured-source-first diff for naming/API ergonomics before commit,
2. optionally tighten CLI edge cases around `source-section` requiring either `--label` or `--title`,
3. update `cli.py` to use `discover_papers_with_status(...)` for `discover` and likely `download-paper`,
4. add CLI integration tests for partial-source failure and fully unavailable discovery,
5. verify download flow reports degraded remote states without pretending the result set is trustworthy,
6. implement richer citation-neighborhood degradation reporting;
7. expand the end-to-end audit scenario once citation diagnostics stabilize.
