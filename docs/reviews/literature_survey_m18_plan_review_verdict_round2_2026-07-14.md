# M18 Material Plan Review Verdict, Round 2

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer (`/root/m18_plan_review_round2`)
Status: `REVISE_ONE_MATERIAL_REPAIR_REQUIRED`

The reviewer complied with the passive-inspection role: no project command,
helper action, test, Git command, edit, or agent launch was performed.

## Material Finding

1. The attempt-2 repair path cannot satisfy its declared authoritative gates.
   The plan requires the entire suite to run on the repair child, including
   `audit-candidate`, but `_audit_candidate_commit` rejects any commit whose
   immediate parent is not the M18 baseline. A repair child's immediate parent
   is the failed attempt-1 candidate, so the audit always fails before checking
   its repair record. The helper also lacks a post-commit audit that binds the
   repair child to both the original stage authority and
   `repair_stage_record.json`.

   Required repair: add a repair-aware final-candidate audit that accepts
   exactly the declared two-commit chain, revalidates the original candidate,
   verifies the repair commit's exact path/mode/OID/hash/size set and protected
   exclusions, and preserves the exact whitespace constraint. This invalidates
   the current retry implementation, not the M18 reproducibility question or
   attempt-1 candidate path.

## Otherwise Coherent

The Git-mode separation, initial exact-stage transaction, protected-path
exclusion, isolated evidence design, targeted-trace limitations, closeout
self-hash nonclaim, boundary limits, and stop conditions otherwise appear
materially coherent on the reviewed surface.

VERDICT: REVISE
