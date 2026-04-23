# Product specification

## Product
Personal Research Assistant

## Product goal
Provide a trustworthy local-first workflow for ingesting, reviewing, discovering, and organizing research papers without silently attaching the wrong metadata or hiding uncertainty.

## Target user
One serious local researcher first. The product is optimized for a single-user CLI workflow running on a local machine with an inspectable file-based store.

## Primary workflows
1. Ingest a local PDF or query into the research store.
2. Review parser consensus, metadata provenance, and confidence before trusting the record.
3. Search the local library and inspect structured paper summaries.
4. Discover related/citing/cited work from external scholarly APIs.
5. Download open-access candidates into an inbox with persisted proposal metadata.
6. Mark papers as approved, needs review, or rejected without losing provenance.
7. Export trusted paper context for downstream writing and coding workflows.

## Core product promises
- Local-first and file-based.
- Conservative by default.
- Clear provenance and review status.
- Deterministic tests plus manual validation scripts.
- No silent final moves for downloaded papers.

## Non-goals
- No opaque metadata auto-merges.
- No bulk scraping or broad web crawling.
- No unsupported silent auto-organization of the paper library.
- No high-stakes claim verification without explicit evidence support.
- No GUI-first rewrite at this stage.
- No database requirement for v0.1.

## v0.1 milestone
Reviewable local library:
- parser-first ingest with review/conflict signals,
- review queue commands,
- inbox proposal inspection commands,
- benchmark release report,
- documented install/test/validation workflow.

## Acceptance criteria
- `scripts/run_tests.sh` passes.
- `scripts/run_parser_preflight.sh` reports parser readiness clearly.
- `scripts/run_clean_ingest_palazzo.sh` confirms parser-consensus identity on the Palazzo regression.
- parser benchmark script emits a release report and fixture-level results.
- review and inbox commands work on temporary local stores in integration tests.
