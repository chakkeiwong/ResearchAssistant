# Personal Research Assistant

A local-first research development assistant for Claude Code and terminal workflows.

The product focuses on:
- ingesting papers from local PDFs, DOI/title queries, arXiv IDs, or URLs;
- extracting PDF text and parser-derived document structure;
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
ra ingest --pdf /path/to/paper.pdf --query "paper title or topic"
ra find --query "transport maps"
ra show --paper-id paper_example
ra review-list
ra review-show --paper-id paper_example
ra review-mark --paper-id paper_example --status approved
ra discover --query "transport maps hmc"
ra download-paper --query "transport maps hmc"
ra inbox-list
ra inbox-show --proposed-name candidate_paper.pdf
ra parser-preflight
ra parse-pdf --pdf /path/to/paper.pdf
```

## Validation

```bash
scripts/run_tests.sh
scripts/run_parser_preflight.sh
scripts/run_clean_ingest_palazzo.sh
python tests/scripts/run_parser_benchmark.py
```
