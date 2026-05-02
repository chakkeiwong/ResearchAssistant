# Local MCP Adapter

`research-assistant` includes an optional local MCP adapter for assistant
clients that support Model Context Protocol.

This adapter is local stdio only. It is not a hosted service, shared database,
HTTP API, SSO/RBAC system, or live collaboration server.

## Install

Base install:

```bash
python -m pip install .
```

Install with MCP support:

```bash
python -m pip install ".[mcp]"
```

The base `ra` CLI does not require the MCP extra.

## Start The Server

Use an explicit workspace root:

```bash
RA_ROOT=/tmp/ra-demo ra-mcp
```

or:

```bash
ra-mcp --root /tmp/ra-demo
```

To create demo data first:

```bash
ra --root /tmp/ra-demo demo setup
RA_ROOT=/tmp/ra-demo ra-mcp
```

## Client Configuration Shape

Use a stdio command in your MCP client configuration:

```json
{
  "mcpServers": {
    "research-assistant": {
      "command": "ra-mcp",
      "args": ["--root", "/tmp/ra-demo"]
    }
  }
}
```

If `ra-mcp` is not on `PATH`, use the full path from the Python environment
where `research-assistant[mcp]` is installed.

## Read-Only Tools

First-stage MCP tools are read-only:

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

These tools inspect local records. They do not ingest papers, fetch arXiv,
download PDFs, mutate review status, restore backups, delete files, or call
external LLM/provider services.

## Resources

The adapter also exposes read-only resources:

- `research-assistant://workspace/status`
- `research-assistant://paper/{paper_id}`
- `research-assistant://source/{paper_id}`

## Privacy Boundary

The MCP server runs on the local machine and reads the configured local
workspace. Tool responses may include local paper metadata, review notes,
provenance, source-extraction records, and local paths to stored artifacts.

Do not point `RA_ROOT` at a workspace you do not want the assistant client to
inspect.

## Batch ArXiv Intake

Large arXiv intake is planned as a separate grant-bound workflow. The intended
flow is:

1. plan a bounded batch;
2. approve a local expiring grant;
3. run intake using that grant;
4. inspect the manifest and audit log.

Batch intake creates review material only. It must not mark records approved.

Explicit-ID source intake is available first:

```bash
ra --root /tmp/ra-demo arxiv-batch plan --ids 2401.00001 --max-papers 1
ra --root /tmp/ra-demo mcp grant arxiv-intake --plan-hash <plan_hash> --max-papers 1 --ids 2401.00001 --skip-duplicates
ra --root /tmp/ra-demo arxiv-batch run --grant-id <grant_id> --plan-hash <plan_hash> --ids 2401.00001
```

Query-based live arXiv discovery and PDF batch downloads remain future work.

For a validation checklist, see `docs/mcp_trial_checklist.md`.

## Deferred Write Modes

Query-based arXiv discovery has a design gate in
`docs/architecture/mcp_arxiv_query_discovery_design.md`. It is not live-enabled
through MCP yet.

PDF batch downloads have a separate design gate in
`docs/architecture/mcp_pdf_batch_intake_design.md`. PDF batch execution remains
disabled until byte limits, duplicate handling, cleanup, and tests are in
place.

Review-write is being prototyped through CLI confirmation commands, not MCP:

```bash
ra review-write propose-status --paper-id <id> --status approved
ra review-write apply --confirmation-id <confirmation_id>
```

MCP review mutation remains disabled. The CLI prototype records old/new values,
file hashes, expiration, and audit events, and blocks if the target file changed
after proposal creation.

## Troubleshooting

If `ra-mcp` reports that the MCP SDK is missing, install the optional extra:

```bash
python -m pip install ".[mcp]"
```

Check the local workspace:

```bash
ra --root /tmp/ra-demo doctor
ra --root /tmp/ra-demo privacy status
```

Check the MCP entrypoint:

```bash
ra-mcp --help
```

Stop the server through the MCP client, or interrupt the foreground process.
