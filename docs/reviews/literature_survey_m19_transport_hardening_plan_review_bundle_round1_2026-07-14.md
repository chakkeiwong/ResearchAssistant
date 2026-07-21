# M19 Transport Hardening Plan Review Bundle, Round 1

Date: `2026-07-14`
Reviewer role: passive read-only

## Review Question

Is the dedicated M19A local hardening plan correct, feasible, artifact-
complete, proportionate, and fail-closed enough to authorize implementation
without authorizing live access?

## Exact Surface

- `docs/plans/literature_survey_north_star_m19_metadata_transport_hardening_subplan_2026-07-14.md`
- Parent:
  `docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_subplan_2026-07-13.md`
- M18 close authority:
  `docs/plans/literature_survey_north_star_m18_local_close_record_2026-07-14.md`
- Current transport anchors in candidate `654e6e1...`:
  `src/research_assistant/survey/build.py` constants and functions
  `_collect_public_metadata`, `_fetch_public_json`,
  `_openalex_metadata_search`, `_openalex_cited_by`, and
  `_arxiv_metadata_query`.
- Historical design input:
  `docs/plans/literature_survey_m16_phase11_bounded_live_smoke_subplan_2026-07-10.md`
  plus its three `REVISE` verdicts.

## Focus

Check:

1. exact M18 entry authority and no overlap with protected user work;
2. whether route/query/proxy/redirect/retry/byte/time/error/ledger contracts are
   closed and implementable;
3. whether one-frame IPC, deadlines, process cleanup, and output publication
   can be tested without network;
4. missing defaults, catching tests, evidence, repair, stop, or handoff terms;
5. whether the edit/artifact allowlist is sufficient but not overbroad;
6. whether boundary-invalid states can still be hidden as `unavailable`;
7. whether the `187` second whole-attempt hypothesis is coherent; and
8. whether the plan follows current proportional academic governance rather
   than retired token ceremony.

## Reviewer Constraints

Do not run tests, Python, helpers, network, GPU, Git mutation, or external
models. Do not edit files. This review cannot authorize live access, source
retrieval, human decisions, scientific claims, defaults, push, or release.

Return severity-ordered findings and exactly `VERDICT: AGREE` or
`VERDICT: REVISE`.

Round 1 returned `REVISE`. The repaired plan must be rereviewed from a new
round-2 bundle; this file remains the historical round-1 request.
