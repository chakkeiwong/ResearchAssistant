# M22 Omission Frontier Triage And Source Inspection Result

Date: `2026-07-19`
Milestone: `M22_qualitative_scholarly_assessment_and_real_missions`
Status: `PASSED_BOUNDED_OMISSION_TRIAGE_AND_FIVE_SOURCE_INSPECTION`

## Question And Evidence Contract

This phase asked whether the exact `55` unused identifier-bearing bibliography
entries could be replayably grouped for omission-risk triage, and whether a
predeclared five-paper direct-method subset could receive bounded
credential-free arXiv source intake and primary technical inspection.

The phase did not ask and does not establish literature completeness,
publication or retraction safety, official-code faithfulness, independent
reproduction, universal correctness, method ranking, forward-citation
coverage, or prose readiness.

## Parser Repair And Corrected Frontier

The retained M20 BibTeX title parser stopped at the first closing brace. A
balanced braced/quoted field reader now preserves nested capitalization groups
and multiline titles. Focused cases include
`Learning High Dimensional {W}asserstein Geodesics` and quoted/nested titles.

Re-extraction from the retained `references.bib` exactly matches the production
set of `62` identifier-bearing candidates and the exact `55` deferred IDs.
Thirteen previously truncated titles are corrected in the new M22 artifact;
historical M20/M22B0 ledgers remain unchanged.

Provisional title-context groups:

| Group | Count |
| --- | ---: |
| `DIRECT_OT_OR_GEOMETRY` | 24 |
| `FOUNDATIONAL_COMPONENT` | 4 |
| `COMPARATOR_OR_FAILURE_ANALYSIS` | 15 |
| `APPLICATION_OR_DATASET` | 10 |
| `PERIPHERAL_OR_BACKGROUND` | 2 |

These counts prioritize reading only. They are not scholarly classifications
or claim support.

## Live Source Campaign

One bounded CPU-only credential-free invocation completed in `103.29448`
seconds:

| Item | Result |
| --- | --- |
| Exact arXiv IDs | `1902.02934`, `1905.10812`, `1906.09691`, `2102.02992`, `2205.15269` |
| Requests | `5/5` dispatched |
| Retries | `0` |
| Per-source cap | `50,000,000` bytes |
| Evidence-root cap | `300,000,000` bytes |
| Retained root before close | `61,925,753` bytes |
| Accepted and parsed | `5/5` |
| Source failures / parse gaps | `0 / 0` |
| Offline replay | `passed` |
| Credentials/providers/PDF fallback | none |

The source-intake campaign preserved `claims=[]`; successful intake did not
promote relevance or claim support.

## Technical Inspection Decisions

| Paper | Inspected survey role | Main source-grounded boundary |
| --- | --- | --- |
| `1902.02934` | `COMPARATOR_OR_FAILURE_ANALYSIS` | Proposes an OT-regularity explanation of GAN mode collapse; checked regularity conditions are narrower than a universal GAN-causation claim. |
| `1905.10812` | `REGULARIZED_DIRECT_METHOD` | Defines a nearest smooth/strongly-convex pushforward objective; generally not exact transport to the original target and not a metric to that target. |
| `1906.09691` | `DIRECT_METHOD` | Proves W2-geodesic and Monge-map recovery under perfect-discriminator and ideal-update assumptions; finite training remains conditional. |
| `2102.02992` | `DIRECT_METHOD` | Neural dynamical-OT/geodesic method; the true smooth solution is a critical point, not a proved outcome of neural saddle optimization. |
| `2205.15269` | `DIRECT_METHOD` | Analyzes fake weak-quadratic saddle maps and proves characteristic-kernel optimal-saddle results under compactness, gamma, and optimal-potential assumptions. |

The active qualitative bundle now contains `16` assessments: the seven prior
source-located papers, these five inspected papers, and four omission-frontier
records. All `75` evidence files resolve; `64` technical-text references have
valid source line anchors. `claim_support_allowed=false` and
`ready_for_prose=false` remain fixed.

## Execution-Lineage Finding

The live run preserved the M20 archive worker after that worker began importing
the new `bibtex_fields.py` helper, but did not copy the helper into its
`execution_sources/` directory. The run used the helper from the recorded dirty
worktree and its source bytes, routes, accepted packages, derived artifacts,
and scientific outcomes replay. However, its preserved execution-source set is
not independently sufficient to reconstruct that import.

The runner now preserves the helper for future runs and replay reports the
exact historical gap as `legacy_execution_source_gaps=["bibtex_fields.py"]`.
The immutable live root was not edited. This is a provenance limitation, not a
source-intake or scientific-result veto.

## Decision Table

| Decision | Primary criterion | Veto status | Interpretation | Next action |
| --- | --- | --- | --- | --- |
| Close bounded omission triage | Exact 55 replay; five exact source outcomes; five technical inspections | No scientific or campaign veto | `PASS` within declared scope | Carry 50 title-context-only rows as residual omission risks |
| Promote paper roles | Method/theory/evaluation/limitations inspected | Passed for scoped survey roles | Five roles may inform qualitative survey structure | Keep every technical statement tied to the recorded assumptions and anchors |
| Authorize final prose | Independent claim review and mission-level evidence | Not met | `REJECTED` | M22 representative mission matrix and reviewed terminal remain open |
| Claim completeness or ranking | Forward coverage, broader source audit, uncertainty-supported comparison | Not met | `NOT_CONCLUDED` | Preserve explicit limitations |

## Remaining M22 Gaps

1. Fifty identifier-bearing rows remain title-context provisional.
2. The `195` identifier-free bibliography units remain an unresolved identity
   frontier.
3. Official code and publication/retraction status were not checked for the
   five inspected papers.
4. Forward citations remain unavailable and non-blocking.
5. The predeclared representative real-mission matrix and at least one
   assessed terminal from the production topic/bootstrap route remain to be
   executed before M22 can close.

## Verification

- Related M20/M21/M22 compatibility slice: `71 passed` before the live run.
- Focused source-campaign and inspection tests: `15 passed`, followed by `9`
  lineage/replay tests after the preservation repair.
- Compile checks: passed.
- `git diff --check`: passed.
- Actual live-root offline replay after repair: passed with the one explicit
  legacy execution-source gap.
- Final related terminal slice: `92 passed`.
- Source-inspection validator binds exact titles and every evidence line to the
  matching candidate source directory; cross-candidate evidence and title drift
  are rejected.
- `source_inspection_manifest.json` binds the inspection output to exact
  triage, queue, campaign result, route ledger, and five accepted package
  hashes.
- Claude health probe returned `CLAUDE_PROBE_OK`. The bounded material review
  was rejected before repository content export by the external-data policy.
  No workaround was attempted. A fresh Codex terminal audit found and repaired
  the missing helper preservation and candidate-specific evidence-binding
  issues; focused and full related checks then passed.

## Handoff

The next M22 subplan should use the existing frozen representative mission
matrix, remove retired binary-human prerequisites, and define a small
qualitative assessed-terminal campaign. It must separate engineering terminal
behavior from scientific interpretation and must not reopen provider,
credential, numeric-scoring, generic-human-attestation, or PDF-fallback loops.
