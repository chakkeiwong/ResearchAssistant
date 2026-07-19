# M22 Qualitative Scholarly Assessment Redesign Result

Date: `2026-07-19`
Parent: `M22_human_attested_review_and_real_missions`
Status: `PASSED_LOCAL_QUALITATIVE_REDESIGN_CLAUDE_UNAVAILABLE`

## Decision

The binary scholarly judgment path and numeric score worksheet are retired as
the active interpretation model. M22 now represents nuanced paper/claim/
omission assessment with concise qualitative notes. Deterministic binary gates
remain for source provenance, source safety, exact anchor identity, and import
lineage. This is a change in representation and prioritization, not permission
to promote unsupported claims.

## What Changed

- Added [qualitative_assessment.py](../../src/research_assistant/survey/qualitative_assessment.py)
  with bounded summary, merits, concerns, uncertainties, evidence references,
  next action, exact replay validation, and explicit nonclaims.
- Added `survey qualitative-assessment`, an offline CLI command that writes one
  assessment and always reports `claim_support_allowed: false` and
  `ready_for_prose: false`.
- Added `qualitative_assessment_worksheet.csv` to generated M22 bundles. It
  asks for short evidence-grounded notes for seven source-located papers plus
  aggregate omission frontiers rather than 55 independent binary decisions or
  pseudo-precise numbers.
- Removed the experimental `scored_uncertainty.py`, `survey score-assessment`,
  and the numeric worksheet from active code. Historical plan text preserves
  why that experiment was rejected.
- Regenerated the production reviewer bundle without changing packet or queue
  hashes. The old JSON/CSV packet remains preserved as historical/compatibility
  evidence and is not treated as a human-readable scientific conclusion.

## Evidence And Limits

| Item | Result |
| --- | --- |
| New qualitative assessment tests | `9 passed` |
| Existing M22 packet tests | `16 passed` |
| Changed-module compile | passed |
| `git diff --check` | passed |
| Claude read-only review | unavailable after two bounded trusted probes; no output |
| Calibration | not applicable to active qualitative interface |
| Scientific promotion | not performed; zero claims are newly supported |

The qualitative note is not a truth label or probability. It should state both
merits and concerns when both are present, preserve unresolved uncertainty and
reviewer disagreement, and point to exact local evidence. A note cannot clear
source safety, claim support, or prose readiness.

## Handoff

The next M22 work may use the qualitative worksheet to prioritize expert
inspection and qualify wording. It must preserve the hard source/provenance
gates. M22/G5 remains open at the genuine human/expert
review boundary; this redesign does not establish literature completeness,
scientific correctness, forward-citation coverage, or north-star completion.

The old binary human packet is preserved at:

`docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/`
