# Personal Research Assistant POC

## What exists now

This first proof-of-concept supports:
- paper ingestion from arXiv IDs, local PDFs, DOI-like query, arXiv-like query, or general title/topic query;
- arXiv LaTeX source fetching, caching, flattening, and structural extraction;
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
- structured-source-first arXiv LaTeX audit artifacts
- multi-parser document understanding
- parser reconciliation and confidence reporting
- parser preflight / availability diagnostics
- discovery query support

Current structured-source scaffold includes:
- `ra source-fetch --arxiv-id ...` for caching arXiv source bundles;
- conservative main-TeX detection and `\input` / `\include` flattening;
- source-derived sections, equations, theorem-like blocks, labels, refs, citations, bibliography entries, and macros;
- `ra source-show` and `ra show` visibility for source artifacts.

Current parser scaffold includes:
- `pdftotext` (operational)
- Marker (CLI-backed adapter wired, needs broader paper-family validation)
- GROBID (health-check preflight and full-text TEI parsing adapter wired, requires local service validation)
- MinerU (CLI-backed adapter scaffolded via `magic-pdf`, requires config and broader runtime validation)
- MarkItDown (CLI-backed adapter wired, needs broader paper-family validation)

Current discovery scaffold includes:
- merged discovery results with source-status reporting
- citation-neighborhood lookup with endpoint-status reporting
- degraded-state handling for empty and unavailable remote sources

## Useful commands

### Ingest an arXiv paper with source-first extraction

```bash
ra ingest --arxiv-id 2401.00001 --query "paper title or identifying query"
```

### Fetch and inspect arXiv source artifacts

```bash
ra source-fetch --arxiv-id 2401.00001
ra source-show --paper-id paper_example
```

### Ingest a local PDF fallback

```bash
ra ingest --pdf /path/to/paper.pdf --query "paper title or identifying query"
```

### Search the local library

```bash
ra find --query "transport maps"
```

Search output is tab-separated:

```text
paper_id    year    review_status    title
```

### Show a paper record

```bash
ra show --paper-id paper_example
```

This returns a review-focused JSON payload with:
- top-level `review` status, provenance, identity-validation fields, and metadata-source statuses;
- `source_extraction` details including structured source status, primary source, artifact paths, section/equation/theorem/citation counts, labels, bibliography, macros, provenance, diagnostics, and limitations;
- `extraction` / `pdf_extraction` details including extracted text path, consensus section headings, parser reconciliation, parser disagreements, parser capability limits, and explicit extraction limitations;
- top-level `technical_audit` placeholders for operator-entered technical reading notes;
- raw `summary` and `metadata` payloads;
- linked records.

### Review queue

```bash
ra review-list
ra review-list --status needs_review
ra review-show --paper-id paper_example
ra review-mark --paper-id paper_example --status approved
```

Review statuses are `approved`, `needs_review`, and `rejected`. Marking a paper does not erase provenance or merge notes.

### Discovery and inbox workflow

```bash
ra discover --query "transport maps HMC"
ra citation-neighborhood --paper-id paper_example
ra download-paper --query "transport maps HMC"
ra inbox-list
ra inbox-list --duplicate-status possible_duplicate
ra inbox-show --proposed-name candidate_paper.pdf
```

Discovery results are merged and ranked across supported scholarly APIs. `citation-neighborhood` returns JSON with compact `summary.top_citing` and `summary.top_cited` sections for reviewable survey building.

Downloaded papers go to `local_research/inbox/`. Proposal metadata is saved under `local_research/inbox/metadata/`. The tool does not silently move papers into final library locations.

Inbox proposals include duplicate-aware review signals against existing summaries and raw filenames. `inbox-show` exposes a `review_summary` section with duplicate counts and matched local paper ids.

### Check parser readiness

```bash
ra parser-preflight
```

This shows which parsers are:
- available
- unavailable
- misconfigured

Each check also reports parser capability limits. Treat section headings as partial, and treat equation and PDF-citation extraction as unreliable unless a later manual parser validation proves otherwise for the specific paper.

before you try to parse anything.

### Run parser consensus on a PDF

```bash
ra parse-pdf --pdf /path/to/paper.pdf
```

`parse-pdf` returns the reconciled parser payload, including each parser output, derived title/author/section candidates, parser disagreements, parse confidence, and the same capability limits reported by preflight. Use it as an inspection checkpoint before trusting `ingest` metadata.

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

## Literature-audit workflow

Use structured source as the primary path when doing careful technical reading. For arXiv papers, LaTeX source preserves sections, equations, labels, theorem/proof environments, macros, citations, and bibliography structure better than PDF text extraction. PDF parser reconciliation remains useful as fallback and rendered-output cross-check. Remote discovery and citation enrichment are useful for survey building, but they are allowed to be empty or unavailable without blocking local audit work.

1. Fetch or ingest arXiv source when available:

   ```bash
   ra source-fetch --arxiv-id 2401.00001
   ra source-show --paper-id paper_example
   ra ingest --arxiv-id 2401.00001 --query "paper title or identifying query"
   ```

   Inspect source status, flattened source path, section/equation/theorem/citation extraction, macro table, provenance, diagnostics, and limitations. Treat source-derived evidence as machine extraction, not as human-verified audit conclusions.

2. Check parser readiness before a PDF fallback audit:

   ```bash
   ra parser-preflight
   ```

   Confirm which parsers are available and read their capability limits. Today, section headings are only partial, while equations and PDF citations are unreliable as structured output.

3. Run parser consensus directly when you want to inspect PDF extraction before committing a record:

   ```bash
   ra parse-pdf --pdf /path/to/paper.pdf
   ```

   Inspect `parse_confidence`, `requires_manual_review`, `disagreements`, `consensus_section_headings`, and each row in `parser_outputs`.

4. Ingest the local PDF fallback and inspect the stored record:

   ```bash
   ra ingest --pdf /path/to/paper.pdf --query "paper title or identifying query"
   ra show --paper-id paper_example
   ```

   Use `ra show` to check source extraction when present, the stored extracted text path, parser reconciliation details, parser-output capability limits, metadata-source statuses, identity validation, and the empty `technical_audit` fields before marking the paper trusted.

5. Record human technical audit notes in the summary JSON when needed. Keep these notes separate from machine extraction. The durable fields include `transport_definition`, `objective`, `transformed_target`, `claimed_results`, `derived_results`, `open_questions`, `relevant_equations`, `relevant_sections`, and `assumptions_for_reuse`.

6. Use remote enrichment opportunistically:

   ```bash
   ra discover --query "transport maps HMC"
   ra citation-neighborhood --paper-id paper_example
   ```

   Check `status` and `source_statuses`. `empty` means at least one source responded but produced no results; `unavailable` means all relevant sources failed or could not be reached.

7. Approve only after inspection, then export trusted context:

   ```bash
   ra review-mark --paper-id paper_example --status approved
   ra export-context --review-status approved --output /tmp/paper_context.json
   ```

   The export preserves `technical_audit`, review status, provenance, and summary fields for downstream synthesis.


This is still a POC. Current limitations include:
- arXiv LaTeX source is the preferred audit substrate when available, with PDF parsing retained as fallback and cross-check;
- remote discovery and citation endpoints can return `available`, `empty`, or `unavailable` source statuses, including HTTP rate-limit codes;
- claim-support audit is still summary-based and conservative rather than full evidence extraction;
- source-derived equations, theorem-like blocks, citations, bibliography, and macros are extracted conservatively from LaTeX and still require human technical review;
- parser capability reporting is explicit, but equations and PDF citations remain unreliable as PDF-derived structured output;
- section headings are partially supported through parser reconciliation and should be checked against the extracted text;
- Marker, MarkItDown, GROBID, and MinerU still need more representative runtime validation;
- the MCP adapter remains a thin wrapper layer and not yet a full protocol implementation.

## Recommended next steps

1. validate arXiv source-first ingest on representative mathematical papers;
2. improve LaTeX extraction around custom macros, theorem variants, and bibliography edge cases;
3. finish validating MarkItDown and Marker on representative local papers;
4. resolve MinerU config and implement real output ingestion;
5. implement GROBID header/fulltext extraction in the parser adapter;
6. add structured-source MCP tools after the internal CLI path stabilizes.
