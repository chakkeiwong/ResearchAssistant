# M22 Qualitative Scholarly Assessment Redesign Plan

Date: `2026-07-19`
Status: `QUALITATIVE_IMPLEMENTATION_PASSED_CLAUDE_UNAVAILABLE`
Parent: `M22_human_attested_review_and_real_missions`

## Why Numeric Scoring Is Being Demoted

The current M22B queue treats claim review and omission review as binary
dispositions. A numeric 0-4 rubric was then added, but that also imposed false
precision: reviewers must decide what the numbers mean, whether intervals are
calibrated, and whether weights are defensible. That burden is not useful for
the current evidence set. A concise source-grounded narrative is a better
representation of scholarly judgment.

The `55` unused bibliography entries also show that exact per-row disposition is
not a reasonable human workload. They should remain machine-accounted
provenance and be ranked/aggregated, not treated as 55 equal expert reviews.

## Academic Evidence Contract

| Field | Contract |
| --- | --- |
| Question | How strong is the evidence for a proposed paper/claim, how relevant is it to the stated topic, and how likely is the proposed wording to overstate what the source establishes? |
| Primary output | A concise qualitative assessment with summary, merits, concerns, uncertainties, evidence references, and next action. |
| Hard gates | Source provenance, source-safety notices, exact anchor identity, and claim-support class remain deterministic gates. Scores cannot clear them. |
| Numeric migration | The experimental `scored_uncertainty` code and active worksheet were removed. Any previously rendered score sheet is historical only and is not an input to M22. |
| Decision use | Narrative notes expose evidence, merits, concerns, uncertainty, disagreement, and next action. They do not establish truth, completeness, superiority, or prose readiness. |
| Nonclaims | No narrative establishes scientific correctness, paper relevance in fact, claim truth, literature completeness, reviewer competence, or claim-support authorization. |

## Qualitative Assessment Contract

Each assessment records:

- a short summary of what the inspected evidence appears to show;
- concrete merits or reasons the paper/claim may matter;
- concrete concerns, including scope mismatch, missing controls, or possible
  overstatement;
- unresolved uncertainties and disagreements;
- exact local source/anchor references; and
- one next action, such as narrow wording, inspect a section, expand the source
  frontier, or retain the item as an omission risk.

This is a structured scholarly note, not a probability forecast. It is valid to
say that a source has important merits and serious limitations at the same time.

## Workload Policy

- Score the seven source-located candidates and the explicit seed at paper level.
- Aggregate the 55 unused bibliography entries into one omission-frontier row
  with a count and machine provenance. Expand individual review only when an
  automated prioritization rule identifies a high-risk candidate.
- Keep the 195 identifier-free units as one aggregate frontier risk.
- Keep forward-citation unavailability as an explicit nonblocking limitation.

## Implementation Scope

1. Add a pure local qualitative-assessment module with strict field/list
   validation and explicit nonclaims.
2. Add merits/concerns/uncertainties/evidence/next-action columns to the active
   reviewer worksheet without changing existing binary import schemas or hard
   gates.
3. Add a qualitative assessment artifact and focused tests for bounded text,
   required evidence references, exact replay, and non-promotion behavior.
4. Remove the experimental numeric scorer from active code and refresh M22B
   documentation to describe qualitative expert-assisted assessment.

## Implementation Result

Completed locally on `2026-07-19`:

- `src/research_assistant/survey/qualitative_assessment.py` provides strict
  bounded-text/list validation, exact replay, explicit evidence references,
  and fixed nonclaims.
- `survey qualitative-assessment` emits a concise JSON assessment but never
  promotes claim support or prose readiness.
- The reviewer bundle now includes `qualitative_assessment_worksheet.csv` with
  one row per source-located paper and aggregate rows for omission frontiers.
- The experimental `scored_uncertainty.py`, `survey score-assessment`, and the
  numeric reviewer worksheet were removed from active code. Historical plan
  text records why the experiment was rejected.
- Existing binary packet/import schemas and hard provenance/source-safety gates
  are unchanged. The old 73-row packet remains preserved as historical and
  compatibility evidence; no human attestation was created.

Focused verification: `9` qualitative tests and `16` existing M22 packet tests
passed; changed-module compile and
`git diff --check` passed. Two bounded trusted Claude health probes returned no
output, so Claude was recorded unavailable for this review round. Local checks
are sufficient for this additive, non-promoting change under the repository's
review-proportionality policy.

## Numeric Scorer Migration

The experimental numeric scorer had no labeled adjudication set, scoring rule
analysis, or held-out calibration check. Its midpoint was never a probability
estimate in the statistical sense, so it was removed rather than retained as
active complexity. A future probabilistic forecasting phase, if ever justified,
must be separately planned and must not relabel these notes retroactively.

## Skeptical Audit

The main risk is false precision. The revised plan removes active numeric
judgment and requires concrete prose plus evidence references instead. A second
risk is workload inflation; aggregate treatment of unused bibliography entries
addresses it. The plan does not change source provenance, safety, or exact
replay contracts.

Audit verdict: `READY_FOR_LOCAL_SCORED_REVIEW_IMPLEMENTATION`.
