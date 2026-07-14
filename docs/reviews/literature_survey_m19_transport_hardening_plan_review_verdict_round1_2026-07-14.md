# M19 Transport Hardening Plan Review Verdict, Round 1

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer (`/root/m19_plan_review`)
Status: `REVISE`

## Findings

1. The parent M19 plan still described terminal M18 review and closeout as
   future despite the child correctly citing `e7f1499...` and terminal
   `AGREE`.
2. The ledger and IPC contracts lacked exact key/type/null/enum/cross-field
   schemas, so catching tests could not objectively establish closure.
3. Request rows bound query keys but not exact query values/templates or a
   canonical request hash, and no exact header policy was frozen.
4. Current `build.py` broad catch/normalization paths could still collapse a
   boundary defect into ordinary provider `unavailable`.
5. Supervisor artifact naming, atomic publication/residue, process-session
   ownership, and finite pipe/send/read/EOF rules were incomplete.
6. Fallback helpers and exact one-seed/provider/order/`max_records` topology
   were not all mandatory tripwires.
7. Shared regression checks were conditional despite required sink threading
   through shared `build.py` paths.
8. The `187`-second whole-attempt bound remained an unresolved hypothesis.

VERDICT: REVISE
