# M16 Phase 10 Implementation Review Verdict - Round 1

Date: `2026-07-13`
Reviewer provenance: fresh independent Codex read-only reviewer; downgraded
fallback because Claude repository export was policy-rejected.
Supervisor/executor: Codex `/root`.

## Hash Verification

All `22` path/SHA-256 rows in the submitted change manifest existed and matched
before review.

## Findings

1. `HIGH`: the change manifest hashed the summary and aggregate artifacts but
   did not transitively bind the primary case results, CLI records, setup
   manifests, or mission authority files. Those files could drift without
   invalidating a manifest row.
2. `HIGH`: the focused test generated and read a temporary candidate rather
   than independently validating the frozen canonical candidate. The canonical
   closeout `static_audit.json` also had a different shape than the harness
   audit the test asserted, demonstrating that it had not tested the frozen
   artifact referenced by the summary.
3. `HIGH`: positive selected artifact/decision IDs were read only after the
   second run and were not compared between the first and second CLI payloads
   or selector snapshots. The second action, reason, and classification were
   also not exact catching predicates.
4. `MEDIUM`: negative before/after authority snapshots were serialized but not
   generally enforced. Several tests checked only key sets or one pointer,
   leaving undeclared mutation possible.
5. `MEDIUM`: the outside-write tripwire used lexical absolute-path ancestry and
   could be bypassed by a symlinked ancestor inside the case root.

## Required Repair

- Bind every regular primary E2E case artifact through a deterministic
  inventory/tree digest that the summary and change manifest hash.
- Give the harness audit a distinct immutable filename and make the focused
  test validate the canonical persisted candidate and its complete inventory.
- Snapshot and compare selected authority IDs before and after replay and
  require the exact second terminal tuple.
- Gate every negative through a declared full mission-tree mutation allowlist,
  with zero unexpected changes.
- Resolve candidate and root paths through existing symlink ancestors and add
  a catching symlink-ancestor outside-write test.

`VERDICT: REVISE`
