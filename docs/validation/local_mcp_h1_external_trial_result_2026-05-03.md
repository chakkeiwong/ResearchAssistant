# H1 External MCP Trial Result - 2026-05-03

## Classification

- Outcome: passed
- H1 classification: accepted
- Reason: required demo setup and MCP read-only tool calls succeeded under 15
  minutes; unsafe tools were absent; review-write was not exposed through MCP.
  One sandbox-specific stdio issue was bypassed by running the MCP client
  outside the sandbox.
- Trial runner: Codex external agent
- Maintainer assistance used: no

## Environment

- Operating system: Linux WSL2
- Python version: 3.11.14
- Install source: local source checkout
- Source commit or package version:
  `0ea4a094c65b4e62da614fca768953f5db5eb6a8`,
  `research-assistant==0.1.0`
- MCP client: Python MCP SDK stdio client
- MCP client version: `mcp==1.26.0`
- Workspace root: `/tmp/ra-mcp-h1-trial`

## Timing

- Install time: about 3 seconds for successful active-environment install
- Demo setup time: under 1 second
- MCP client configuration time: under 1 minute
- Time to first successful MCP tool call: 0.305 seconds

## Setup Command Results

- `python -m pip install ".[mcp]"`: passed in active Python environment;
  installed `research-assistant==0.1.0`; `ra-mcp` available
- `ra --root /tmp/ra-mcp-h1-trial demo setup`: passed; status `ready`; demo
  paper id `demo_transport_paper`
- `ra --root /tmp/ra-mcp-h1-trial review-write status`: passed;
  `mcp_exposed: false`
- `ra --root /tmp/ra-mcp-h1-trial mcp status`: passed; default mode
  `read_only`; destructive tools disabled; review-write disabled
- `ra-mcp --help`: passed

## MCP Tool Inventory

Research-assistant tools listed by the client:

- `ra_workspace_status`
- `ra_find_paper`
- `ra_get_paper_summary`
- `ra_paper_code_links`
- `ra_claim_support_audit`
- `ra_review_list`
- `ra_review_show`
- `ra_source_show`
- `ra_parser_tool_matrix`
- `ra_privacy_status`
- `ra_plan_arxiv_batch_intake`
- `ra_run_arxiv_batch_intake`

`ra_run_arxiv_batch_intake` was present and shown as grant-bound explicit-ID
source intake. Unsafe research-assistant tools were absent.

## Required Tool Calls

| Tool | Status | Sanitized evidence summary |
| --- | --- | --- |
| `ra_workspace_status` | passed | Reported status `ok`, mode `read_only`, transport `stdio`, non-hosted service, and no write/destructive tools. |
| `ra_find_paper` | passed | Found one demo item: `demo_transport_paper`, `needs_review`. |
| `ra_get_paper_summary` | passed | Returned read-only demo summary/review material for `Demo Transport Map Paper`; manual review still required. |
| `ra_source_show` | passed | Returned fixture source record for `demo_transport_paper`, source type `fixture_latex`, status `available`. |
| `ra_review_list` | passed | Listed one `needs_review` demo item without mutation. |
| `ra_claim_support_audit` | passed | Returned summary-level read-only audit; classification was background/low-confidence, not approval. |
| `ra_privacy_status` | passed | Reported offline mode, providers disabled, no live LLM calls, and no network required for default workflows. |

## Review-Write Boundary

- `mcp_exposed`: false
- Review mutation offered by MCP client: no
- Notes: no review mutation tools appeared in the MCP inventory.

## Optional Batch-Grant Boundary Check

- Run mode: skipped
- Explicit arXiv IDs used: none
- Grant creation result: not checked
- Live run result: not checked
- Manifest/audit summary: not checked
- Any paper marked approved: not checked

## Problems And Suggestions

- Confusing setup steps: `python3 -m venv` failed because system
  `python3-venv` was unavailable; installing into the active Python
  environment worked.
- Missing docs: mention that external agents may use an existing Python
  environment if fresh venv creation is unavailable.
- Client-specific issues: MCP stdio initialization timed out inside the
  sandbox, but succeeded outside the sandbox with the same server and SDK
  client.
- Error messages to improve: an isolated prefix install with system Python
  produced `UNKNOWN-0.0.0`; successful active-environment install produced
  correct metadata.
- Suggested docs/code changes: add troubleshooting for sandboxed stdio
  transports and for verifying `ra-mcp` with `command -v ra-mcp`.

## Privacy Confirmation

- Demo or non-private workspace only: yes
- No private titles included: yes
- No raw PDFs or extracted text included: yes
- No credentials/tokens included: yes
- No private local paths included: yes

## Final Notes

The H1 functional trial passed. The result accepts the local stdio MCP setup
and read-only permission boundary for a demo workspace. It does not validate
live arXiv execution, query discovery, PDF batch execution, or MCP
review-write.

The external runner noted generated packaging metadata after local install:
`src/research_assistant.egg-info/` changed and `UNKNOWN.egg-info/` appeared.
Those are generated install artifacts, not validation evidence. The repository
now ignores `*.egg-info/` and no longer tracks `src/research_assistant.egg-info/`.
