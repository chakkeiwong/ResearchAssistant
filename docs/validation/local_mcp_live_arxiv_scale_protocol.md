# Local MCP Live ArXiv Source Scale Protocol

Use this protocol only after the operator explicitly approves a live arXiv
network run. Do not run these commands as part of deterministic tests.

Current status: `accepted`.

## Purpose

Validate H2:

> Grant-bound explicit-ID arXiv source intake works at 25, then 50, then 100
> live papers with bounded failures and useful manifests.

The existing deterministic test validates mocked 25-paper local mechanics. It
does not validate live arXiv availability, throttling, elapsed time, or partial
failure ergonomics.

## Approval Gate

Before running, record:

- approving person:
- date:
- batch size: `25`, `50`, or `100`
- explicit sanitized arXiv ID source:
- workspace root under `/tmp`:
- maximum timeout:
- expected maximum source archive footprint:

Do not use private workspaces or private paper lists. Do not commit output.

## Bounds

- Allowed domains: `arxiv.org`, `export.arxiv.org`
- Destination: source records only
- Workspace: `/tmp/ra-live-arxiv-source-<count>-<date>`
- Duplicate policy: `skip_existing`
- Overwrite policy: `no_overwrite`
- Review policy: `review_material_only`
- Batch order: run 25 first, then 50 only if 25 is comfortable, then 100 only
  if 50 is comfortable.

Suggested timeouts:

| Count | Command timeout |
| --- | --- |
| 25 | `timeout 900` |
| 50 | `timeout 1800` |
| 100 | `timeout 3600` |

## Command Template

Set variables outside the repository:

```bash
ROOT=/tmp/ra-live-arxiv-source-25-2026-05-02
IDS=<comma-separated-sanitized-arxiv-ids>
COUNT=25
```

Create the workspace and plan:

```bash
ra --root "$ROOT" init
ra --root "$ROOT" arxiv-batch plan --ids "$IDS" --max-papers "$COUNT"
```

Copy the `plan_hash` from the plan output, then create the grant:

```bash
PLAN_HASH=<plan_hash>
ra --root "$ROOT" mcp grant arxiv-intake \
  --plan-hash "$PLAN_HASH" \
  --max-papers "$COUNT" \
  --ids "$IDS" \
  --expires-hours 2 \
  --skip-duplicates
```

Copy the `grant_id` from the grant output, then run:

```bash
GRANT_ID=<grant_id>
timeout 900 ra --root "$ROOT" arxiv-batch run \
  --grant-id "$GRANT_ID" \
  --plan-hash "$PLAN_HASH" \
  --ids "$IDS"
```

Adjust the timeout for 50/100 using the table above.

Inspect sanitized results:

```bash
ra --root "$ROOT" mcp audit list --grant-id "$GRANT_ID"
ra --root "$ROOT" workspace validate
```

## Metrics To Record

Record only summaries:

- count requested:
- count attempted:
- fetched count:
- skipped duplicate count:
- failed count:
- elapsed time:
- timeout used:
- manifest exists: yes/no
- audit event count:
- common failure reasons:
- any arXiv throttling/rate-limit signal:
- any overwrite/approval concern:

Do not paste manifest contents, audit log contents, source archives, extracted
text, or private local paths into docs.

## Pass Criteria

- command completes within timeout;
- manifest and audit summary are useful;
- failures are low and explainable;
- no source record is treated as approved evidence;
- no paper review status is marked approved;
- rerun behavior skips existing records instead of overwriting them.

## Narrow Criteria

- smaller count passes but larger count hits throttling or elapsed-time limits;
- partial failures are clear and retryable;
- source availability differs by arXiv paper type but is recorded cleanly.

## Fail Criteria

- command hangs past timeout;
- failure reporting is unclear;
- grant mismatch or duplicate behavior is unsafe;
- generated outputs appear outside the temp workspace;
- any review approval happens automatically.

## Sanitized Result Table

| Date | Count | Timeout | Attempted | Fetched | Skipped | Failed | Elapsed | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05-03 | 25 | 900s | 25 | 17 | 0 | 0 | 153.99s | `accepted` | Public IDs `2401.00001`-`2401.00025`; 7 source-structure failures and 1 unavailable source were recorded as review-material limitations. |
| 2026-05-03 | 50 | 1800s | 50 | 40 | 0 | 0 | 167.70s | `accepted` | Public IDs `2401.00001`-`2401.00050`; 9 source-structure failures and 1 unavailable source were recorded as review-material limitations. |
| 2026-05-03 | 100 | 3600s | 100 | 87 | 0 | 0 | 591.90s | `accepted` | Public IDs `2401.00001`-`2401.00100`; 12 source-structure failures and 1 unavailable source were recorded as review-material limitations. |

Duplicate/no-overwrite follow-up:

- The first duplicate rerun against the 25-paper live workspace was safely
  blocked because duplicate diagnostics changed the recomputed plan hash.
- The plan hash was fixed to exclude mutable duplicate diagnostics while still
  binding ordered IDs, paper IDs, URLs, destination, policies, and
  candidate-file metadata.
- A patched-checkout rerun with a fresh grant skipped all 25 existing records,
  fetched 0 records, recorded 0 failures, and completed in 0.09s.
