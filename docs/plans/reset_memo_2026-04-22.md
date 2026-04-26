# Reset memo — research assistant status

Date: 2026-04-22
Repo: `/home/chakwong/research-assistant`
Branch: `main`
Last pushed commit: `afcd732` — `Harden parser-first ingest and add discovery validation workflows.`

## What was just completed
- Added a CLI-level regression for parser-first local PDF ingest using the Palazzo paper.
- Fixed `ingest` so temp-root runs create the extracted-text directory before writing.
- Hardened parser preflight checks and made their statuses/messages more actionable.
- Tightened benchmark fixture/schema coverage and updated parser benchmark script output.
- Implemented normalized discovery results with Semantic Scholar primary plus OpenAlex fallback/enrichment.
- Added a conservative `download-paper` workflow that downloads open-access PDFs into `local_research/inbox/` and proposes canonical names instead of silently moving files.
- Replaced tests that depended on live network behavior with mocked tests to avoid rate-limit/time-out failures.

## Current verified state
- Full test suite passes via `scripts/run_tests.sh`: `35 passed`.
- `scripts/run_clean_ingest_palazzo.sh` now shows:
  - parser hints populated,
  - summary title = `Credit Risk and the Transmission of Interest Rate Shocks`,
  - summary authors = `['Berardino Palazzo', 'Ram Yamarthy']`,
  - `identity_source = parser_consensus`,
  - `requires_manual_review = True` (intentionally conservative).
- `scripts/run_parser_preflight.sh` currently reports:
  - `pdftotext` available,
  - `markitdown` available,
  - `marker` available,
  - `mineru` misconfigured because `~/magic-pdf.json` is missing,
  - `grobid` unavailable because local service is not running.

## Important files added or changed in this round
### Core implementation
- `src/research_assistant/cli.py`
- `src/research_assistant/ingest/parser_preflight.py`
- `src/research_assistant/query/discovery.py`
- `src/research_assistant/query/downloads.py`
- `src/research_assistant/schemas/discovery_result.py`
- `src/research_assistant/ingest/metadata_resolve.py`
- `src/research_assistant/summarize/draft_summary.py`
- parser adapters/orchestrator under `src/research_assistant/ingest/`

### Tests and fixtures
- `tests/integration/test_cli_commands.py`
- `tests/integration/test_parser_first_ingest_precedence.py`
- `tests/integration/test_benchmark_inventory.py`
- `tests/integration/test_candidate_resolution.py`
- `tests/unit/test_metadata_parser_hints.py`
- `tests/unit/test_parser_preflight.py`
- `tests/unit/test_parser_adapter_status.py`
- `tests/unit/test_discovery.py`
- `tests/unit/test_discovery_normalization.py`
- `tests/unit/test_downloads.py`
- benchmark fixtures under `tests/fixtures/benchmark_papers/synthetic/`
- harness scripts under `tests/scripts/`

### Docs and operator scripts
- `CLAUDE.md`
- `docs/benchmark_plan.md`
- `docs/validation_scripts.md`
- `docs/hardening_plan.md`
- `docs/test_plan.md`
- `docs/usage.md`
- `scripts/run_tests.sh`
- `scripts/run_parser_preflight.sh`
- `scripts/run_clean_ingest_palazzo.sh`

## Current project direction
The agreed direction is still:
1. parser-first ingest correctness first,
2. benchmark corpus and parser harness hardening,
3. parser-preflight as the operator gate,
4. discovery/citation support with Semantic Scholar primary and OpenAlex fallback,
5. conservative download-to-inbox/proposal workflow,
6. more automation only after validation stays strong.

## Recommended next steps
1. Compile synthetic benchmark PDFs and upgrade the parser benchmark from `expected_record_only` to real parser-vs-ground-truth scoring.
2. Implement real GROBID endpoint parsing instead of only health checks.
3. Finish MinerU local configuration so it can participate in parser validation.
4. Expand discovery beyond search normalization into explicit citation traversal commands.
5. Decide whether `download-paper` should persist proposal records in the research store.

## Local state to remember
- `out.txt` was intentionally excluded from commit/push and remains untracked scratch output.
- The repo has already been committed and pushed; this reset memo is post-push state.
