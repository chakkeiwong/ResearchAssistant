# Personal Research Assistant POC

## What exists now

This first proof-of-concept supports:
- paper ingestion from a local PDF, DOI-like query, arXiv-like query, or general title/topic query;
- raw PDF storage;
- PDF text extraction via `pdftotext`;
- OpenAlex metadata lookup and basic Crossref/arXiv enrichment;
- draft structured paper summary generation;
- local search over stored summaries;
- explicit paper-to-code/document link creation;
- simple claim-audit record generation;
- workspace export generation for assistant-friendly context;
- thin MCP-wrapper-ready backend functions.

## New v2 scaffolding now present

The codebase now also includes early scaffolding for:
- multi-parser document understanding
- parser reconciliation and confidence reporting
- parser preflight / availability diagnostics
- discovery query support

Current parser scaffold includes:
- `pdftotext` (operational)
- Marker (CLI-backed adapter wired, runtime validation still needed)
- GROBID (health-check preflight + placeholder service adapter)
- MinerU (CLI-backed adapter scaffolded via `magic-pdf`, requires config)
- MarkItDown (CLI-backed adapter wired, runtime validation still needed)

Current discovery scaffold includes:
- OpenAlex-backed `discover`
- placeholder citation graph module for future Semantic Scholar/OpenAlex expansion

## Useful commands

### Check parser readiness

```bash
ra parser-preflight
```

This shows which parsers are:
- available
- unavailable
- misconfigured

before you try to parse anything.

### Run parser consensus on a PDF

```bash
ra parse-pdf --pdf /path/to/paper.pdf
```

### Manual parser checks

#### MarkItDown
```bash
markitdown /path/to/paper.pdf -o /tmp/markitdown_test.md
```

#### Marker
```bash
marker_single /path/to/paper.pdf --output_dir /tmp/marker_test --output_format markdown --disable_multiprocessing
```

#### MinerU
```bash
magic-pdf --path /path/to/paper.pdf --output-dir /tmp/mineru_test --method auto
```

#### GROBID health check
```bash
curl http://localhost:8070/api/isalive
```

## Current limitations

This is still a POC. Current limitations include:
- OpenAlex is the strongest active discovery/metadata source in the current workflow;
- citation graph traversal is not fully implemented yet;
- claim-support audit is still summary-based and conservative rather than full evidence extraction;
- only `pdftotext` is currently fully validated in the parser layer;
- Marker and MarkItDown are now wired but still need successful runtime validation;
- GROBID still needs endpoint-specific parsing implementation;
- MinerU still needs config and runtime validation;
- the MCP adapter remains a thin wrapper layer and not yet a full protocol implementation.

## Recommended next steps

1. finish validating MarkItDown and Marker on representative local papers;
2. resolve MinerU config and implement real output ingestion;
3. implement GROBID header/fulltext extraction in the parser adapter;
4. build parser reconciliation and disagreement-aware metadata extraction into ingest;
5. add Semantic Scholar-backed citation graph queries;
6. add discovery-download and paper-organization proposal workflow.
