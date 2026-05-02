# Local MCP Colleague Trial Record Template

Use this template after a real colleague completes `docs/mcp_trial_checklist.md`.
Record only non-private metadata.

Do not fill this template with local surrogate results. Local surrogate results
can validate mechanics, but they do not prove real colleague MCP usability.

## Trial Metadata

- Date:
- Recorder:
- Trial outcome: `passed`, `narrowed`, or `failed`
- Reason for outcome:
- Workspace type: `/tmp` demo, fresh local workspace, or other non-private
  workspace

## Environment

- Operating system and version:
- Python version:
- Install mode: editable source checkout, wheel, or other
- MCP client:
- MCP client version, if known:
- `ra version` result:
- `ra-mcp --help` result: passed or failed

## Setup Timing

- Time to install:
- Time to create demo workspace:
- Time to configure MCP client:
- Time to first successful tool call:

## Tools Exercised

Mark each as passed, skipped, or failed.

- `ra_workspace_status`:
- `ra_find_paper`:
- `ra_get_paper_summary`:
- `ra_source_show`:
- `ra_review_list`:
- `ra_claim_support_audit`:
- `ra_privacy_status`:

## Unsafe Tool Absence

Confirm these were absent from the MCP client tool list.

- Review mutation through MCP:
- Query-based live arXiv discovery through MCP:
- PDF batch download through MCP:
- Backup restore through MCP:
- Delete/destructive file tools:
- Arbitrary file read/write tools:

## Batch Grant Trial

- Explicit arXiv IDs used: use sanitized IDs only
- Batch run mode: live, mocked/local surrogate, or skipped
- If skipped, reason:
- Grant creation result:
- Run result:
- Manifest created: yes or no
- Audit events created: yes or no
- Any paper marked approved: should be no

## Review-Write Boundary

- `ra review-write status` result:
- `mcp_exposed`: should be `false`
- Review mutation offered by MCP client: should be no

## Observations

- Confusing setup steps:
- Missing docs:
- Error messages that should be clearer:
- MCP client configuration issues:
- Suggested checklist changes:

## Privacy Confirmation

Confirm that this record does not include:

- private paper titles;
- raw PDFs;
- extracted text;
- credentials or tokens;
- private local paths beyond a generic demo/temp workspace;
- colleague names or identifying details unless they explicitly opted in.

## Final Interpretation

- H1 interpretation: accepted, rejected, or narrowed
- Follow-up required:
- Docs or code changes recommended:
