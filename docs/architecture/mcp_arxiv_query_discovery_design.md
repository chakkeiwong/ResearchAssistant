# MCP arXiv Query Discovery Design

## Purpose

This document defines the design gate for query-based arXiv discovery through
local MCP workflows.

The current implemented batch path accepts explicit arXiv IDs. Query discovery
is intentionally not enabled yet because it adds network fanout, pagination,
ranking, and candidate drift risks.

## Design Goals

- Convert a query into a bounded candidate list.
- Bind the exact candidate list into the batch plan hash.
- Require a local grant before any source/PDF intake.
- Keep deterministic tests fully mocked and offline.
- Keep live query discovery manual, bounded, and auditable until validated.

## Non-Goals

- No broad web search.
- No unbounded arXiv pagination.
- No automatic PDF download.
- No automatic review approval.
- No hosted/shared MCP discovery service.

## Proposed Workflow

1. Discover candidates:

```bash
ra arxiv-batch discover --query "transport maps HMC" --max-candidates 50
```

2. Inspect a candidate file:

```text
local_research/governance/mcp/query_candidates/<candidate_id>.json
```

3. Plan from that fixed candidate file:

```bash
ra arxiv-batch plan --candidate-file <candidate_file> --max-papers 25
```

4. Create grant using the resulting `plan_hash`.

5. Execute intake using grant ID and plan hash.

MCP should expose discovery only after the CLI path is tested and bounded.

## Candidate Contract

A candidate record should contain:

- schema version;
- candidate batch ID;
- query string;
- normalized query;
- created timestamp;
- workspace root;
- max candidates;
- endpoint URL;
- request timeout;
- pagination limit;
- result ordering;
- candidate list;
- source status;
- limitations.

Each candidate should include:

- arXiv ID;
- title;
- authors;
- abstract snippet;
- published/updated dates;
- primary category;
- PDF URL;
- source URL;
- entry URL;
- provenance index;
- duplicate status.

## Bounding Rules

- `max_candidates` is required.
- `max_candidates` must have a conservative upper bound, initially 100.
- Pagination must not exceed the number needed for `max_candidates`.
- Request timeout must be explicit.
- Endpoint domain must be `export.arxiv.org`.
- Live discovery must record source status and failures.
- Candidate ordering must be deterministic from the API response.

## Plan Hash Binding

The batch plan hash must include:

- query;
- normalized query;
- candidate batch ID;
- exact ordered arXiv ID list;
- destination;
- operation;
- max papers;
- duplicate policy;
- overwrite policy;
- review policy.

Grant execution must verify the exact candidate list or explicit ID list, not
only the query text.

## MCP Exposure Policy

Do not expose live query discovery through MCP until:

- mocked candidate parsing tests pass;
- max-candidate and pagination limits are enforced;
- candidate files are inspectable;
- grant execution verifies candidate-list identity;
- one bounded live smoke has been approved and recorded.

Before that, MCP may expose only read-only planning for explicit IDs or fixed
candidate files.

## Tests Required Before Enablement

- mocked arXiv Atom response parsing;
- max-candidate enforcement;
- pagination cap enforcement;
- plan hash changes when candidate order/content changes;
- duplicate detection from local summaries/source records;
- network failure returns structured unavailable status;
- no writes during dry-run discovery unless explicitly saving a candidate file.

## Open Questions

- Should candidate files live under `local_research/governance/mcp/` or
  `local_research/inbox/metadata/`?
- Should query discovery normalize categories or expose them raw?
- Should source-fetch batch require candidates to be pinned by candidate file
  rather than query string once query discovery is enabled?
