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
- Marker (CLI-backed adapter wired, needs broader paper-family validation)
- GROBID (health-check preflight and full-text TEI parsing adapter wired, requires local service validation)
- MinerU (CLI-backed adapter scaffolded via `magic-pdf`, requires config and broader runtime validation)
- MarkItDown (CLI-backed adapter wired, needs broader paper-family validation)

Current discovery scaffold includes:
- merged discovery results with source-status reporting
- citation-neighborhood lookup with endpoint-status reporting
- degraded-state handling for empty and unavailable remote sources

## Useful commands

### Ingest a local PDF

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
- `extraction` details including extracted text path, consensus section headings, parser reconciliation, parser disagreements, parser capability limits, and explicit extraction limitations;
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

Use local PDFs as the primary path when doing careful technical reading. Remote discovery and citation enrichment are useful for survey building, but they are allowed to be empty or unavailable without blocking local audit work.

1. Check parser readiness before a serious audit:

   ```bash
   ra parser-preflight
   ```

   Confirm which parsers are available and read their capability limits. Today, section headings are only partial, while equations and PDF citations are unreliable as structured output.

2. Run parser consensus directly when you want to inspect extraction before committing a record:

   ```bash
   ra parse-pdf --pdf /path/to/paper.pdf
   ```

   Inspect `parse_confidence`, `requires_manual_review`, `disagreements`, `consensus_section_headings`, and each row in `parser_outputs`.

3. Ingest the local PDF and inspect the stored record:

   ```bash
   ra ingest --pdf /path/to/paper.pdf --query "paper title or identifying query"
   ra show --paper-id paper_example
   ```

   Use `ra show` to check the stored extracted text path, parser reconciliation details, parser-output capability limits, metadata-source statuses, identity validation, and the empty `technical_audit` fields before marking the paper trusted.

4. Record human technical audit notes in the summary JSON when needed. Keep these notes separate from machine extraction. The durable fields include `transport_definition`, `objective`, `transformed_target`, `claimed_results`, `derived_results`, `open_questions`, `relevant_equations`, `relevant_sections`, and `assumptions_for_reuse`.

5. Use remote enrichment opportunistically:

   ```bash
   ra discover --query "transport maps HMC"
   ra citation-neighborhood --paper-id paper_example
   ```

   Check `status` and `source_statuses`. `empty` means at least one source responded but produced no results; `unavailable` means all relevant sources failed or could not be reached.

6. Approve only after inspection, then export trusted context:

   ```bash
   ra review-mark --paper-id paper_example --status approved
   ra export-context --review-status approved --output /tmp/paper_context.json
   ```

   The export preserves `technical_audit`, review status, provenance, and summary fields for downstream synthesis.


This is still a POC. Current limitations include:
- local PDF ingest is the dependable primary workflow; remote discovery and download enrichment should be treated as opportunistic;
- remote discovery and citation endpoints can return `available`, `empty`, or `unavailable` source statuses, including HTTP rate-limit codes;
- claim-support audit is still summary-based and conservative rather than full evidence extraction;
- parser capability reporting is explicit, but equations and PDF citations remain unreliable as structured output;
- section headings are partially supported through parser reconciliation and should be checked against the extracted text;
- Marker, MarkItDown, GROBID, and MinerU still need more representative runtime validation;
- the MCP adapter remains a thin wrapper layer and not yet a full protocol implementation.

## Recommended next steps

1. finish validating MarkItDown and Marker on representative local papers;
2. resolve MinerU config and implement real output ingestion;
3. implement GROBID header/fulltext extraction in the parser adapter;
4. build parser reconciliation and disagreement-aware metadata extraction into ingest;
5. add Semantic Scholar-backed citation graph queries;
6. add discovery-download and paper-organization proposal workflow.
