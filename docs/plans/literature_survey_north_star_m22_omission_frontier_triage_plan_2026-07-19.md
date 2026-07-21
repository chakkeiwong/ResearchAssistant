# M22 Omission Frontier Triage And Targeted Source Inspection Plan

Date: `2026-07-19`
Status: `CLOSED_PASSED_BOUNDED_OMISSION_TRIAGE_AND_FIVE_SOURCE_INSPECTION`
Parent: `M22_qualitative_scholarly_assessment_and_real_missions`

## Objective

Classify all `55` unused identifier-bearing bibliography entries into
provisional survey-role groups, nominate a small highest-omission-risk set, and
inspect primary technical source text for that set. Replace provisional labels
only where inspected source evidence supports a stronger classification.

## Entry Conditions

- M20 retained `62` identifier-bearing backward-reference candidates.
- M21 inspected seven source-located candidates; `55` unused BibTeX entries
  remain machine-accounted omission risks.
- M22 qualitative assessments are the active scholarly interface. Numeric
  scoring and generic human attestation are retired.
- OpenAlex, credentials, PDF fallback, and forward-citation providers remain
  unavailable and out of scope.

## Research Intent And Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Which unused bibliography entries are plausible direct/foundational/comparator/application/peripheral survey risks, and what do primary technical sources establish for the highest-risk direct-method nominees? |
| Baseline | Exact `55` unused rows from the production M22 candidate ledger; every row is currently `NOT_CHECKED` and `SOURCE_GAP_BLOCKER`. |
| Provisional classification | Deterministic title/identifier rules may group and prioritize papers. These labels are `TITLE_CONTEXT_PROVISIONAL`, not scholarly classifications or technical evidence. |
| Primary criterion | All 55 rows receive one replayable provisional group and rationale; exactly five predeclared arXiv nominees receive at most one source request each and one closed source/parse outcome; accepted sources receive technical-section inspection notes. |
| Hard vetoes | Candidate loss/duplication; hidden title-to-truth promotion; extra nominee/request/route; retry; credential/provider/PDF use; unsafe archive/write; root-cap breach; missing source outcome; claim promotion. |
| Explanatory only | Group counts, title keywords, source bytes, sections/equations/theorems, and anchor counts. |
| Not concluded | Literature completeness, citation importance, venue quality, publication/retraction safety, mathematical correctness, claim truth, or general method superiority. |

## Provisional Groups

- `DIRECT_OT_OR_GEOMETRY`: title signals an OT map/plan, Wasserstein method,
  Brenier potential, barycenter, or probability-space optimization.
- `FOUNDATIONAL_COMPONENT`: architecture, dataset-independent generative model,
  inference, invertibility, or optimization component used by later methods.
- `COMPARATOR_OR_FAILURE_ANALYSIS`: GAN/WGAN alternatives, stabilization,
  convergence, density-estimation, or failure analysis.
- `APPLICATION_OR_DATASET`: dataset, image/color/domain application, or
  empirical use case.
- `PERIPHERAL_OR_BACKGROUND`: weakly related optimization, activation, or
  general learning background.

These groups guide inspection only. Title-only classification cannot authorize
a citation or technical claim.

## Exact Source Nominees

1. `1902.02934` - Mode collapse and regularity of optimal transportation maps.
2. `1905.10812` - Smooth/strongly convex Brenier potentials.
3. `1906.09691` - Adversarial computation of optimal transport maps.
4. `2102.02992` - Learning high-dimensional Wasserstein methods.
5. `2205.15269` - Kernel Neural Optimal Transport.

Selection is based on direct map/potential/neural-OT title signals and proximity
to the survey question. It is not a ranking by correctness, citations, venue,
or expected favorable result.

## Resource Budget

| Resource | Bound |
| --- | --- |
| Source IDs | Exact five above, in order |
| Requests | At most one per ID; at most five total |
| Retries/reruns | No automatic retries; localized harness repair may continue within the same total campaign budget only before any affected ID has dispatched |
| Credential interface | None |
| Route | `https://arxiv.org/e-print/<id>` only, bounded arXiv redirects |
| Per-source bytes | `50,000,000` |
| Total evidence root | `300,000,000` |
| PDF fallback | Forbidden |
| Retained source members | Existing safe `.tex`, `.bib`, `.bbl` policy |
| Hardware | Deliberate CPU-only; `CUDA_VISIBLE_DEVICES=-1` |

## Default And Assumption Audit

| Choice | Status | Failure mode | Early diagnostic |
| --- | --- | --- | --- |
| Keyword groups | Convenience hypothesis | Titles misstate technical role | Keep provisional status and inspect primary text before promotion |
| Five nominees | Bounded omission-risk sample | Another direct method is missed | Preserve all 55 rows and publish next-candidate queue |
| arXiv source | Credential-free source hypothesis | Unavailable/malformed/PDF wrapper | Closed per-paper source gap, no fallback |
| No citation metadata | Campaign boundary | Recent/influential work not prioritized | Record unavailable, never treat as zero |
| Machine anchors | Reading aids | Anchor availability mistaken for support | `claims=[]`, `ready_for_prose=false` |

## Pre-Mortem

- The classification could look complete because every row has a label while
  remaining scientifically shallow. Mitigation: all title-only labels state
  `TITLE_CONTEXT_PROVISIONAL`, and the result separates group coverage from
  source-inspected evidence.
- The five sources could parse successfully but contain no evidence relevant to
  the survey. Mitigation: inspect method/theory/experiments/limitations and allow
  `BACKGROUND`, `APPLICATION`, or `PERIPHERAL` outcomes.
- A successful download could be mistaken for publication or retraction safety.
  Mitigation: safety remains `NOT_CHECKED` unless exact evidence is present.
- A source failure could be mistaken for an irrelevant paper. Mitigation:
  classify it `SOURCE_BLOCKED` and retain its provisional omission priority.

## Required Artifacts

1. `provisional_classification.json` with all 55 exact rows and group counts.
2. `inspection_queue.json` with the exact five nominees and rationale.
3. Run manifest, route ledger, per-source exact bytes/status, structured source,
   machine anchors, and offline replay.
4. `source_inspection.json` with method/theory/evaluation/limitation notes for
   accepted sources and explicit source gaps otherwise.
5. `omission_frontier_result.json` and a readable Markdown report.

## Stop And Handoff Conditions

Stop for candidate-accounting mismatch, unsafe route/archive/write, campaign
root-cap failure, corrupted replay, or an unrepresentable outcome. Continue
past an individual unavailable/malformed source. Do not stop because a nominee
turns out peripheral or scientifically weak.

M22 may close this omission-triage step when all 55 provisional rows replay,
all five exact source outcomes are recorded, technical inspection notes exist
for accepted sources, remaining source gaps/nonclaims are explicit, and the
next inspection queue is derived without claiming completeness.

## Skeptical Audit

The baseline is the exact production candidate ledger, not hand-selected title
examples. Title rules are a prioritization mechanism, not evidence. Technical
promotion requires inspected primary text. Individual candidate failure does
not invalidate the campaign. The commands and artifacts answer omission-risk
triage and targeted source support, not completeness or method correctness.

Audit verdict: `PASS_FOR_IMPLEMENTATION_AND_BOUNDED_EXECUTION`.

Close record:
`docs/plans/literature_survey_north_star_m22_omission_frontier_triage_result_2026-07-19.md`.
