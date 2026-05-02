# Local MCP Trial Checklist

Use this checklist for a colleague-like local MCP trial. Record only
non-private metadata.

## Setup

```bash
python -m pip install ".[mcp]"
ra --root /tmp/ra-mcp-trial demo setup
ra-mcp --root /tmp/ra-mcp-trial
```

Configure a local MCP client with stdio command `ra-mcp --root
/tmp/ra-mcp-trial`.

## Read-Only Trial

Exercise these tools:

- `ra_workspace_status`
- `ra_find_paper`
- `ra_get_paper_summary`
- `ra_source_show`
- `ra_review_list`
- `ra_claim_support_audit`
- `ra_privacy_status`

Expected result:

- tools can inspect demo data;
- no ungranted write, ingest, download, review mutation, backup restore, or
  delete tools are offered;
- privacy status remains provider-disabled;
- generated/source/parser outputs are presented as review material.

## Batch-Grant Trial

Use a tiny explicit-ID plan. A real network fetch is optional and should be
bounded.

```bash
ra --root /tmp/ra-mcp-trial arxiv-batch plan --ids 2401.00001 --max-papers 1
ra --root /tmp/ra-mcp-trial mcp grant arxiv-intake --plan-hash <plan_hash> --max-papers 1 --ids 2401.00001 --skip-duplicates
ra --root /tmp/ra-mcp-trial arxiv-batch run --grant-id <grant_id> --plan-hash <plan_hash> --ids 2401.00001
ra --root /tmp/ra-mcp-trial mcp audit list --grant-id <grant_id>
```

Expected result:

- execution requires the grant ID and matching plan hash;
- manifest and audit events are created;
- source records remain review material;
- no paper is marked approved.

## Metadata To Record

- platform;
- Python version;
- MCP client;
- install mode;
- workspace root type, for example `/tmp` demo;
- tools exercised;
- whether read-only tools worked;
- whether write tools were absent;
- whether batch grant/run worked or was skipped;
- confusions or docs gaps.

Do not record private titles, private paper paths, raw PDFs, extracted text, or
credentials.
