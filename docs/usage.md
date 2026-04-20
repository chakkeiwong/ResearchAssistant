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
- discovery query support

Current parser scaffold includes:
- `pdftotext`
- Marker (placeholder)
- GROBID (placeholder)
- MinerU (placeholder)
- MarkItDown (placeholder)

Current discovery scaffold includes:
- OpenAlex-backed `discover`
- placeholder citation graph module for future Semantic Scholar/OpenAlex expansion

## Directory layout

- `src/research_assistant/` — source code
- `local_research/papers/raw/` — raw PDFs
- `local_research/papers/extracted/` — extracted text
- `local_research/metadata/` — metadata JSON
- `local_research/summaries/` — structured paper summaries
- `local_research/links/` — paper/code/doc links
- `local_research/reviews/` — review artifacts
- `local_research/indices/` — future indices
- `local_research/caches/` — future caches

## Install

From the project root:

```bash
python3 -m pip install -e .
```

## Basic commands

### Ingest a PDF

```bash
ra ingest --pdf /path/to/paper.pdf --query "paper title or topic"
```

### Ingest from query only

```bash
ra ingest --query "NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport"
```

### Ingest with arXiv ID hint

```bash
ra ingest --query "Deep Learning Hamiltonian Monte Carlo" --arxiv-id 2105.03418
```

### Find papers

```bash
ra find --query "transport hmc"
```

### Show a summary and links

```bash
ra show --paper-id paper_foo_bar_12345678
```

### Add a paper-to-code or paper-to-doc link

```bash
ra link-add --paper-id paper_foo_bar_12345678 --target src/my_module.py --relationship implements
ra link-add --paper-id paper_foo_bar_12345678 --target docs/chapter.tex --target-type document_section --relationship supports
```

### Run a claim audit

```bash
ra audit-claim --claim "This paper proposes an invertible transport for exact HMC" --papers paper_foo_bar_12345678
```

### Run parser consensus on a PDF

```bash
ra parse-pdf --pdf /path/to/paper.pdf
```

### Discover papers by topic

```bash
ra discover --query "neural transport hmc posterior geometry" --limit 10
```

## Current limitations

This is still a POC. Current limitations include:
- OpenAlex is the strongest active discovery/metadata source in the current workflow;
- citation graph traversal is not fully implemented yet;
- claim-support audit is still summary-based and conservative rather than full evidence extraction;
- parser scaffold exists but only `pdftotext` is operational today;
- MCP adapter remains a thin wrapper layer and not yet a full protocol implementation.

## Recommended next steps

1. implement parser adapters for Marker / GROBID / MinerU / MarkItDown;
2. build parser reconciliation and disagreement-aware metadata extraction into ingest;
3. add Semantic Scholar-backed citation graph queries;
4. add discovery-download and paper-organization proposal workflow;
5. strengthen claim-support audit once parser quality improves.
