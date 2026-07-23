# Personal Research Assistant

A local-first research development assistant for Claude Code and terminal workflows.

The v0.1 runtime contract is Python 3.11.x only.

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

## Local MCP adapter

`research-assistant` can also run as a local stdio MCP server with the optional
MCP extra:

```bash
python -m pip install ".[mcp]"
ra --root /tmp/ra-demo demo setup
ra-mcp --root /tmp/ra-demo
```

The first MCP surface is read-only by default. It does not expose ingest,
download, review mutation, backup restore, destructive operations, or hosted
server deployment.

See [docs/mcp.md](docs/mcp.md).

This checkout also includes project/workspace MCP config for Claude Code and
VS Code. See [docs/mcp_client_setup.md](docs/mcp_client_setup.md).

## Product posture

This is a validation-first personal research tool, not an automatic paper-library manager. Uncertain records should surface review signals instead of being silently accepted.

See [docs/product_spec.md](docs/product_spec.md) for the v0.1 product contract.

## Core commands

From an installed package, use `ra`. From a source checkout, use
`scripts/ra-dev` to run the same CLI without manually exporting
`PYTHONPATH=src`:

```bash
scripts/ra-dev version
scripts/ra-dev --root /tmp/ra-demo demo setup
scripts/ra-dev --root /tmp/ra-demo release-report
```

For agent-friendly local validation presets, use:

```bash
scripts/ra-agent release-report
scripts/ra-agent release-report --root /tmp/ra-demo
scripts/ra-agent mcp-status
scripts/ra-agent fast-tests
scripts/ra-agent focused-tests
```

These helpers do not bypass safety policy. Live network work, review mutation,
PDF downloads, and destructive actions still require explicit approval or a
bounded local grant.

```bash
ra init
ra doctor
ra --root /tmp/ra-demo demo setup
ra --root /tmp/ra-demo demo run
ra workspace validate
ra backup create
ra privacy status
ra bounded-workflow diagnostic --workflow parser-demo --timeout-seconds 60
ra performance smoke --synthetic-count 25
ra release-report
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
ra doctor --matrix
ra parser-tool-matrix
ra parser-benchmark-smoke
ra parse-pdf --pdf /path/to/paper.pdf
```

For a colleague-facing individual install path, start with [docs/installation.md](docs/installation.md) and [docs/quickstart.md](docs/quickstart.md). This release target is local and private: no shared server, no shared database, and no live LLM/provider calls by default.

## Literature Survey Workflow

The active survey workflow is credential-free. Topic-only missions use bounded
OpenAlex metadata nomination; explicit-seed local source work remains
arXiv-first. Start a durable topic mission without inventing a paper seed:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --out /tmp/ra-survey-topic
```

The first run stops at the one public-discovery confirmation. After
confirmation, the bounded generic topic-bootstrap adapter nominates candidates
when the configured public provider is available; provider failure closes
honestly as `terminal_blocked_bootstrap_unavailable`. It does not read
credentials or claim that a nominated candidate is technically verified.

For an exact paper identifier, build the available local evidence skeleton:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --seed arxiv:2201.12220v3 \
  --out /tmp/ra-survey-seed \
  --run-safe-local
```

The command stops before public metadata or source transport until the bounded
public-discovery confirmation is recorded. Explicit-seed local source work
advertises arXiv metadata/source-package scope; forward-citation coverage is
unavailable and non-blocking, and PDF fallback is not part of the active
workflow.

After checked source inspection and snowball review, evaluate a canonical local
centrality evidence bundle with `ra survey assess-centrality --topic-contract
<json> --evidence <json> --out <mission>/centrality`. Refresh `ra survey
mission-plan --mission-root <mission>` to see validated, relevant, rejected,
blocked, and quarantined counts. The command does not fetch or review sources;
metadata rank, citations, venue metrics, and availability cannot promote a
paper.

For a bounded topic-to-central-papers campaign, use:

```bash
ra survey central-papers \
  --topic "Reinforcement learning for financial-product recommenders" \
  --out /tmp/ra-central-papers \
  --confirm-public-discovery
```

This command nominates candidates with OpenAlex, attempts arXiv structured
source acquisition, expands bounded reference and citing identities, writes
the six literature-audit ledgers, and returns validated, rejected,
quarantined, and blocked dispositions. Use `--resume` only with the identical
topic and capability. This is bounded evidence construction, not a claim of
literature completeness, paper correctness, or expert semantic review.

For the retrieval-only seed-candidate queue, use:

```bash
ra survey seed-papers \
  --topic "Reinforcement learning for financial-product recommenders" \
  --out /tmp/ra-seed-papers \
  --confirm-public-discovery
```

This queries bounded OpenAlex, Crossref, and Semantic Scholar metadata,
reconciles DOI/arXiv/OpenAlex identities, and writes provider gaps and
provider-local priority signals. Google Scholar is not automated because it
has no supported public API. A selected row is still metadata-only: inspect
its primary source and run the centrality/snowball workflow before treating it
as a seed paper for scholarly claims.

For compound topics, repeat `--required-facet`, `--alias`, and `--exclude` to
record controlled terminology and scope. Selection balances required facets
and metadata-only scholarly role hypotheses while preserving abstract/concept
evidence and provider-local priority signals. Continue a replay-valid portfolio
without manual copying:

```bash
ra survey continue-seeds \
  --seed-campaign /tmp/ra-seed-papers \
  --out /tmp/ra-seed-inspection
```

The hash-bound handoff starts the existing explicit-seed source workflow. It
does not establish source safety, technical support, centrality, or literature
completeness.

Use `ra survey qualitative-assessment` to record concise merits, concerns,
uncertainties, exact evidence references, and a next action. Qualitative
assessments never authorize technical claims or prose readiness.

See [docs/literature_survey_operator_guide.md](docs/literature_survey_operator_guide.md)
for output interpretation, resume/recovery, corrections, privacy, and the exact
scientific nonclaims.

## Literature-audit operator note

Use the tool as a conservative ingest/review/export workflow rather than a full equation or bibliography extractor.

- `ra show`, `ra discover`, `ra citation-neighborhood`, `ra review-show`, `ra review-mark`, `ra parse-pdf`, `ra doctor --matrix`, `ra parser-tool-matrix`, and `ra parser-benchmark-smoke` return JSON.
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
- `ra doctor --matrix`, `ra parser-tool-matrix`, and `ra parser-benchmark-smoke` report parser/tool availability, workflow readiness, fixture smoke status, and capability limits;
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
scripts/ra-agent fast-tests
scripts/ra-agent focused-tests
scripts/run_tests.sh
scripts/run_parser_preflight.sh
scripts/run_clean_ingest_palazzo.sh
python tests/scripts/run_parser_benchmark.py
```

`scripts/run_clean_ingest_palazzo.sh` uses the deterministic sanitized
parser-consensus regression in the test suite. It does not require a private
paper file.
