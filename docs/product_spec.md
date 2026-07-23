# Product specification

## Product
Personal Research Assistant

## Product goal
Provide a trustworthy local-first workflow for ingesting, reviewing, discovering, and organizing research papers without silently attaching the wrong metadata or hiding uncertainty.

## Generic-tools policy

Product functions solve topic-independent research problems. A domain-specific
query profile, coverage matrix, vocabulary, or expected paper set may exist as
an explicitly named regression fixture, but it must never be selected
automatically or embedded in a public default.

Topic-only discovery has two distinct claims:

1. Candidate nomination ranks bounded metadata results for later inspection.
2. Central-candidate validation determines, from topic fit, resolved identity,
   primary sources, paper role, and backward/forward snowball evidence, whether
   a candidate is genuinely central to the supplied topic.

Citation counts, venue metrics, title-token matches, and source availability
are prioritization or diagnostic signals only. Engineering candidate nomination
and handoff are implemented. A generic, deterministic centrality assessor now
promotes only candidates with resolved identity, safe inspected source,
direct/foundational topic fit, an eligible scholarly role, and independent
centrality evidence. Its evaluator-owned benchmark covers three unrelated
topics with high-citation off-topic controls. `survey central-papers` now
constructs that bundle through bounded OpenAlex/arXiv capabilities,
source-grounded inference, backward/forward expansion, six audit ledgers, and
replay-safe checkpoints. Remaining gaps are broader provider/source coverage,
expert-grade semantic classification, comprehensive source-safety checks, and
external-topic recall validation, not another metadata score.

## Target user
One serious local researcher first. The product is optimized for a single-user CLI workflow running on a local machine with an inspectable file-based store.

## Primary workflows
1. Prefer structured source for mathematical audits: arXiv LaTeX first when available, then structured publisher/TEI sources, then PDF parsing and raw PDF text as fallback.
2. Check parser readiness and capability limits before a PDF fallback audit.
3. Ingest an arXiv ID, local PDF, or query into the research store.
4. Review source extraction, parser consensus, extracted text location, section headings, metadata provenance, and confidence before trusting the record.
5. Keep human technical-audit notes separate from machine extraction.
6. Search the local library and inspect structured paper summaries.
7. Discover related/citing/cited work from external scholarly APIs when available.
8. Download open-access candidates into an inbox with persisted proposal metadata.
9. Mark papers as approved, needs review, or rejected without losing provenance.
10. Export trusted paper context for downstream writing and coding workflows.
11. Run a bounded topic-to-central-papers campaign that reports validated
    candidates together with blocked sources, uncovered roles, omission risks,
    budgets, provenance, and nonclaims.
12. Run a retrieval-only `survey seed-papers` campaign that fuses bounded
    OpenAlex, Crossref, and Semantic Scholar metadata into an inspectable,
    identity-safe candidate queue with provider gaps and replay evidence.
13. Configure generic topic facets, controlled aliases, exclusions, and scope
    notes; balance selected candidates across required facets and scholarly
    roles; and hand the replay-valid selected portfolio into an explicit-seed
    source mission with hash-bound provenance.

## Core product promises
- Structured-source-first for arXiv papers when LaTeX source is available.
- Local-first and file-based.
- Conservative by default.
- Clear provenance and review status.
- Parser capability limits are explicit rather than implied.
- Remote enrichment degrades visibly instead of blocking local review.
- Deterministic tests plus manual validation scripts.
- No silent final moves for downloaded papers.
- Local assistant integration may use a read-only-by-default MCP adapter without
  changing the product into a hosted service.

## Non-goals
- No opaque metadata auto-merges.
- No bulk scraping or broad web crawling.
- No unsupported silent auto-organization of the paper library.
- No task-specific vocabulary, coverage cells, or ranking rules in generic
  product defaults.
- No high-stakes claim verification without explicit evidence support.
- No GUI-first rewrite at this stage.
- No database requirement for v0.1.
- No hosted MCP/HTTP server, shared MCP deployment, or MCP write tools without
  explicit local grant and audit behavior.

## v0.1 milestone
Reviewable local library:
- arXiv-source-first ingest with local source artifacts and review/conflict signals,
- extracted source structure in `source-show` and `ra show`,
- parser-first PDF fallback with extracted text and parser reconciliation inspection in `ra show`,
- parser capability-limit reporting in preflight, parse output, benchmark output, and show output,
- review queue commands,
- audit-oriented technical fields that survive review/export,
- degraded discovery and citation statuses that distinguish empty results from unavailable sources,
- inbox proposal inspection commands,
- benchmark release report,
- documented install/test/validation workflow.

## Acceptance criteria
- `scripts/run_tests.sh` passes.
- `scripts/run_parser_preflight.sh` reports parser readiness clearly.
- `scripts/run_clean_ingest_palazzo.sh` confirms parser-consensus identity using the sanitized deterministic regression fixture, without a private PDF dependency.
- parser benchmark script emits a release report and fixture-level results.
- review and inbox commands work on temporary local stores in integration tests.
