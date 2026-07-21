# M19 Transport Hardening Plan Review Verdict, Round 2

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer (`/root/m19_plan_review`)
Status: `REVISE`

## Findings

1. The selected `187`-second whole-attempt bound was not independently
   enforceable if the parent blocked. The plan needed the exact
   entry+`180`, entry+`185`, entry+`186.5`, and entry+`187` instants, an
   independent watchdog able to terminate supervisor and worker, and coverage
   of every blocking preflight/start/send/receive/EOF/fsync/inventory/
   publication step.
2. The validation-root allowlist contradicted itself between its high-level
   definition and supervisor contract, particularly for `fake_run/**`,
   `pytest_tmp/<gate>/**`, JUnit, logs, and manifests.
3. Exact schemas and type/null/status compatibility remained incomplete for
   `logs/stdout.json`, `logs/stderr.log`, `logs/command_exit.json`,
   `environment_manifest.json`, `root_inventory.json`, and
   `hardening_summary.json`.
4. The header contract did not distinguish application-supplied from
   automatically generated wire headers or freeze the type and exact contents
   of `forbidden_headers`.
5. Ledger/IPC closure did not freeze exact seed/topic row values and numeric
   types, require four rows for a complete envelope, define build-result/
   provider-status/request-outcome agreement, or define retained-prefix and
   totals rules for worker-error/invalid-ledger states.

VERDICT: REVISE
