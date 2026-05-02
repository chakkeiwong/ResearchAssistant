# Local MCP Live Query Discovery Protocol

Use this protocol only after the operator explicitly approves a live arXiv query
smoke. Live query discovery is not enabled in MCP or the default CLI workflow.

Current status: `manual_live_approval_required`.

## Purpose

Validate H3-live:

> Live arXiv query discovery can produce a bounded candidate file without
> uncontrolled pagination, and the pinned file can drive source intake through
> the existing grant path.

The implemented safe path is offline candidate-file planning. A future live
query feature must produce the same pinned candidate-file contract before any
grant or intake execution.

## Approval Gate

Before running a live query smoke, record:

- approving person:
- date:
- exact query:
- whether the query is non-private:
- max candidates:
- pagination cap:
- timeout:
- workspace root under `/tmp`:

Do not use private research queries unless they are intentionally sanitized.

## Bounds

- Endpoint: `https://export.arxiv.org/api/query`
- Allowed domain: `export.arxiv.org`
- Initial max candidates: `10`
- Hard maximum before broader approval: `50`
- Pagination cap: no more pages than needed for `max_candidates`
- Request timeout: `30` seconds
- Output: candidate file only
- No source intake until the candidate file is inspected and a grant is created

## Candidate File Contract

The candidate file must use schema version `arxiv-query-candidates-v1` and
include:

- candidate batch ID;
- exact query;
- normalized query;
- endpoint URL;
- max candidates;
- request timeout;
- result ordering;
- source status;
- ordered candidate list;
- arXiv ID for every candidate.

Each candidate should include:

- arXiv ID;
- title;
- authors;
- entry URL;
- PDF URL;
- source URL;
- primary category if available;
- provenance index.

## Future Command Shape

This command is not implemented/enabled yet; it records the intended live
interface:

```bash
ra --root /tmp/ra-live-query-smoke arxiv-batch discover \
  --query "transport maps HMC" \
  --max-candidates 10 \
  --timeout-seconds 30 \
  --output-candidate-file /tmp/ra-live-query-smoke/candidates.json
```

Once a candidate file exists, the currently implemented safe path is:

```bash
ra --root /tmp/ra-live-query-smoke arxiv-batch candidate-file inspect \
  --path /tmp/ra-live-query-smoke/candidates.json

ra --root /tmp/ra-live-query-smoke arxiv-batch plan \
  --candidate-file /tmp/ra-live-query-smoke/candidates.json \
  --max-papers 10
```

After inspecting the plan, use the explicit local grant and run path:

```bash
ra --root /tmp/ra-live-query-smoke mcp grant arxiv-intake \
  --plan-hash <plan_hash> \
  --max-papers 10 \
  --ids <ordered-candidate-ids> \
  --expires-hours 2 \
  --skip-duplicates

timeout 900 ra --root /tmp/ra-live-query-smoke arxiv-batch run \
  --grant-id <grant_id> \
  --plan-hash <plan_hash> \
  --candidate-file /tmp/ra-live-query-smoke/candidates.json
```

## Metrics To Record

- query:
- max candidates:
- candidate count:
- candidate file checksum:
- pagination count:
- elapsed discovery time:
- source status:
- plan hash:
- whether exact ordered IDs were preserved:
- whether source intake was skipped or run:
- failure/throttling summary:

Do not commit raw API responses, private queries, source archives, manifests, or
audit logs.

## Pass Criteria

- live query returns at most the approved candidate count;
- pagination is bounded;
- candidate file validates with `ra arxiv-batch candidate-file inspect`;
- plan hash changes if candidate order/content changes;
- source intake, if run, requires explicit grant and uses the saved candidate
  file.

## Narrow Criteria

- query returns noisy candidates but the candidate-file path is safe;
- API throttling suggests lower max candidates or longer spacing;
- candidate metadata is incomplete but arXiv IDs are valid and bounded.

## Fail Criteria

- unbounded pagination;
- missing arXiv IDs;
- candidate drift between discovery and planning;
- live query writes source/PDF data before grant;
- live query becomes visible in MCP before approval.

## Current Result Table

| Date | Query | Max Candidates | Candidate Count | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| pending | | 10 | | `manual_live_approval_required` | |
