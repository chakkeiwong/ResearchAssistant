# Personal Research Assistant

A local-first research development assistant for Claude Code and terminal workflows.

The product focuses on:
- ingesting papers from arXiv IDs, local PDFs, DOI/title queries, or URLs;
- using arXiv LaTeX source as the primary audit substrate when available;
- extracting PDF text and parser-derived document structure as fallback and cross-check;
- reconciling parser outputs and metadata candidates conservatively;
- storing structured paper summaries with provenance and review status;
- discovering related/citing/cited papers through scholarly APIs;
- downloading open-access candidates into a reviewable inbox;
- linking papers to code and documents;
- querying and exporting trusted local paper context.

This is intentionally local-first and file-based so it remains inspectable and easy to debug.

## Product posture

This is a validation-first personal research tool, not an automatic paper-library manager. Uncertain records should surface review signals instead of being silently accepted.

See [docs/product_spec.md](docs/product_spec.md) for the v0.1 product contract.

## Core commands

```bash
ra ingest --arxiv-id 2401.00001 --query "paper title or topic"
ra source-fetch --arxiv-id 2401.00001
ra source-show --paper-id paper_example
ra source-sections --paper-id paper_example
ra source-section --paper-id paper_example --label sec:method
ra source-equations --paper-id paper_example
ra source-equation --paper-id paper_example --label eq:target
ra source-theorems --paper-id paper_example
ra source-theorem --paper-id paper_example --label thm:main
ra source-citations --paper-id paper_example
ra source-bibliography --paper-id paper_example
ra source-macros --paper-id paper_example
ra source-labels --paper-id paper_example
ra source-refs --paper-id paper_example
ra ingest --pdf /path/to/paper.pdf --query "paper title or topic"
ra find --query "transport maps"
ra show --paper-id paper_example
ra review-list
ra review-show --paper-id paper_example
ra review-mark --paper-id paper_example --status approved
ra discover --query "transport maps hmc"
ra citation-neighborhood --paper-id paper_example
ra download-paper --query "transport maps hmc"
ra inbox-list
ra inbox-show --proposed-name candidate_paper.pdf
ra export-context --review-status approved --output /tmp/paper_context.json
ra parser-preflight
ra parse-pdf --pdf /path/to/paper.pdf
```

## Literature-audit operator note

Use the tool as a conservative ingest/review/export workflow rather than a full equation or bibliography extractor.

- `ra show`, `ra discover`, `ra citation-neighborhood`, `ra review-show`, `ra review-mark`, `ra parse-pdf`, and `ra parser-preflight` return JSON.
- `ra find`, `ra review-list`, and `ra inbox-list` return tabular output by default.
- `ra export-context` writes a JSON file for downstream coding or writing workflows.

Local outputs live under:
- `local_research/papers/source/` for structured source bundles, flattened LaTeX, and source records
- `local_research/papers/raw/` for stored PDFs
- `local_research/papers/extracted/` for extracted text
- `local_research/metadata/` for metadata JSON
- `local_research/summaries/` for structured paper summaries
- `local_research/inbox/` and `local_research/inbox/metadata/` for downloaded open-access proposals

Current extraction posture:
- arXiv LaTeX source is primary when available and is stored under `local_research/papers/source/`;
- `ra source-fetch` caches source artifacts and extracts sections, equations, theorem-like blocks, labels, citations, bibliography entries, and macros;
- `ra show` separates `source_extraction` from PDF/parser `extraction` and human `technical_audit` notes;
- `ra parser-preflight` reports availability and capability limits for each PDF parser;
- `ra parse-pdf` reports the reconciled parser payload, including per-parser capability limits;
- section headings: partially supported through parser reconciliation;
- equations: not yet reliable as structured output;
- PDF citation extraction: not reliable enough to promise;
- citation graph lookup from scholarly APIs: supported via `ra citation-neighborhood`, with source status reporting when APIs are empty or unavailable.

Example:

```bash
ra ingest --pdf ~/papers/neutra_hmc.pdf --query "Neural Transport HMC"
ra find --query "Neural Transport HMC"
ra show --paper-id neutra_hmc
ra citation-neighborhood --paper-id neutra_hmc
```

## Validation

```bash
scripts/run_tests.sh
scripts/run_parser_preflight.sh
scripts/run_clean_ingest_palazzo.sh
python tests/scripts/run_parser_benchmark.py
```
