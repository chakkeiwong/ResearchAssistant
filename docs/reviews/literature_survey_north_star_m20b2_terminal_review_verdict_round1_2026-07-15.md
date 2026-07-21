# M20B2 Synthetic Credential/Cost Terminal Review Verdict, Round 1

Date: `2026-07-15`
Reviewer: fresh Codex read-only fallback
Verdict: `REVISE`

The review found five material issues:

1. M20B3 was not explicitly gated on new human Git-integration authority even
   though current authority excludes Git integration.
2. `CampaignCostBudget` validated only its initial cap and trusted later mutable
   fields, allowing invalid state either to bypass accounting or raise outside
   the closed boundary.
3. The claimed post-getter reservation token did not exist. An under-cap
   re-entrant mutation could remain dispatchable; the existing regression
   proved only the already-blocked case.
4. IPC serialization rejected only the raw canary, not the approved encoded
   representation set used for response scanning.
5. The `v5` result and manifest therefore overstated the re-entrancy repair and
   could not be terminal evidence.

Required repair: add explicit new-human-Git-authority gating to M20B3;
encapsulate and validate budget state; bind exact state tokens across injected
callbacks; share the bounded raw/percent/form/JSON/nested-JSON detector across
response, IPC, and validation scans; add focused adversarial regressions;
preserve `v5` as superseded; and create fresh evidence.

`VERDICT: REVISE`
