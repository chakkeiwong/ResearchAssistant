# Local MCP Trial Checklist

Use this checklist for a colleague-like local MCP trial. Record only
non-private metadata. Use `docs/mcp_colleague_trial_record_template.md` for the
final trial note, and see `docs/validation/local_mcp_external_validation_records.md`
for the full local MCP evidence index.

If delegating H1 to another agent or environment, use
`docs/validation/local_mcp_h1_external_agent_instructions.md` for the complete
handoff, exact tool calls, and required result format.

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
- no ungranted write, ingest, download, PDF batch, review mutation, backup
  restore, or delete tools are offered;
- privacy status remains provider-disabled;
- generated/source/parser outputs are presented as review material.

Confirm these tools are absent unless a later audited release explicitly adds
them:

- review mutation through MCP;
- query-based live arXiv discovery through MCP;
- PDF batch download through MCP;
- backup restore through MCP;
- delete/destructive file tools.

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

If the live fetch is skipped because network access is unavailable or not
approved, record it as skipped rather than failed. Deterministic mocked scale
tests cover local plan/grant/run mechanics, but do not prove live arXiv
reliability.

## Review-Write CLI Prototype

Review-write is intentionally not exposed through MCP. A reviewer may inspect
the CLI-only prototype separately:

```bash
ra --root /tmp/ra-mcp-trial review-write status
```

Expected result:

- `mcp_exposed` is `false`;
- status is `prototype_cli_only`;
- no MCP client offers a review mutation tool.

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
- whether review-write remained absent from MCP;
- whether query discovery and PDF batch tools remained absent from MCP;
- confusions or docs gaps.

Do not record private titles, private paper paths, raw PDFs, extracted text, or
credentials.

Local surrogate runs are useful for debugging setup mechanics, but H1 should
remain manual/external until a real colleague trial is recorded with the
template.
