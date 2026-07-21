# M18 Material Plan Review Verdict, Round 3

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer (`/root/m18_plan_review_round2`)
Status: `REVISE_SINGLE_PARENT_REPAIR_REQUIRED`

The reviewer complied with the passive-inspection role.

## Material Finding

1. The repair audit validates only the first-parent chain, not an exact
   single-parent two-commit lineage. `_validate_initial_candidate_commit` uses
   `candidate^`, and `_audit_candidate_commit` uses `HEAD^`/`HEAD^^`, but
   neither rejects additional parents. An initial or repair merge commit with
   the expected first parent could pass lineage validation if its resulting
   tree satisfies the other checks. This is also an accidental-state risk if
   `MERGE_HEAD` exists when the prescribed `git commit` runs.

   Required repair: require the initial candidate to have exactly one parent
   equal to the baseline and the repair candidate to have exactly one parent
   equal to the validated initial candidate; reject active merge/sequencer
   state before staging.

The path, mode, OID, hash, size, protected-path, record, and whitespace checks
otherwise resolve the round-2 defect. This finding invalidates only the
fail-closed lineage repair, not the M18 question or ordinary single-parent
attempt paths.

VERDICT: REVISE
