# M21 Retained Seed Source And Anchor Result

Date: `2026-07-18`
Status: `PASSED_LOCAL_RETAINED_SEED_SOURCE_AND_ANCHOR_SLICE_G4_REMAINS_OPEN`
Plan: `docs/plans/literature_survey_north_star_m21_retained_seed_source_anchor_subplan_2026-07-18.md`
Final evidence:
`docs/validation/literature_survey_north_star_m21_retained_seed_anchors_v2_2026-07-18/`
Preserved diagnostic:
`docs/validation/literature_survey_north_star_m21_retained_seed_anchors_2026-07-18/`

## Result

The exact M20-retained `2201.12220v3` source body is byte-identical to the
existing project-native structured-source record: `26,842,514` bytes and
SHA-256
`2eb686b1f5dd9b2fa95ed5185cfe5da4d8e93a2b7d8a294902962e9dac66bd0f`.
The clean core anchor implementation generated and exactly replayed `53`
machine-extracted review pointers for only the seed paper:

- `24` section anchors;
- `18` labeled equation anchors;
- `11` labeled theorem-like anchors.

All `53` anchors remain `machine_extracted_requires_human_or_model_review` and
`anchor_available_claim_not_mapped`. The packet has zero supported claims,
zero local source gaps, no raw source text, an explicit unperformed
retraction/version check, and `ready_for_prose=false`.

This passes the retained-seed local source/anchor slice. It does not close all
of M21/G4 because candidate relevance/source status, identifier-free recovery,
retraction/publication status, technical claim mapping, and genuine review
remain open.

## Repair Record

The first preserved packet used the inherited `24`-anchor convenience default.
It produced `24` section anchors and no equation/theorem-like anchors. That was
a wrong default relative to the technical-anchor objective, not a source or
method negative result.

The localized repair changed only this one-seed invocation to the exact `53`
eligible labeled/important anchors derived from the bound record. It used a
fresh root, changed no shared code or scientific target, and passed `12`
focused anchor tests before execution. The legacy supervisor replay hardcodes
`24`, so the final packet was checked by exact regenerated-row and full
artifact semantic equality against the clean `_extract_anchor_rows` core.

## Evidence Contract Result

| Field | Result |
| --- | --- |
| Question | Exact retained source can produce a project-native replayable seed source/anchor packet: `passed`. |
| Baseline | M20 exact source plus byte-identical historical structured record. |
| Primary criterion | Passed: one seed, exact bytes, `53` full-type eligible anchors, zero supported claims, zero local source gaps, no raw leakage, no prose readiness. |
| Hard vetoes | None fired after repair. The first packet failed the type-coverage criterion and is preserved as diagnostic evidence. |
| Explanatory only | Structure/anchor counts, output bytes, and runtime. |
| Not concluded | Claim truth/support, mathematical correctness, candidate relevance, retraction/publication safety, complete source understanding, completeness, product readiness. |

## Decision Table

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Pass retained-seed M21 slice; keep G4 open | Passed after one local default repair | No final veto | Reference relevance, identifier-free recall, source status, and technical claim mapping remain unchecked | Source-grounded citation-context triage for all `62` M20 candidates, then define a bounded primary-source selection | Scientific relevance, support, safety, completeness, M21/north-star completion |

## Verification

- Pre-run anchor/source slice: `75 passed`, `122 deselected`.
- Focused repair gate: `12 passed`, `53 deselected`.
- Final post-run anchor/source slice: `75 passed`, `122 deselected`.
- Core compilation, JSON, fresh-root, no-network scan, and diff hygiene: passed.
- Exact semantic replay: `53` unique anchors with type counts `24/18/11`;
  artifact rows exactly regenerated from the bound record.
- Final artifact SHA-256 values:
  - inventory: `f1c80f02048352a033a2c1eba29881f218b35b04df7ca5fa54bd216d74c816e8`;
  - source support: `2dda97878fa3560e60c093922feb5efa1263f7d74504de6d18201e80c9cb4b58`;
  - claim support: `7ca0dc1b3b5810f0f7a013257cb628ba301a6722fa1a6f1d8d35d2138a63918f`;
  - quarantine: `97f9ef16b693b56f11a618c8d0c89669b2f8620b7d342593ef65ef91f97fd1b1`;
  - manifest: `727e775b08cd92dccf7d80af21d9cb62453d647869d9ec57497de5308890834a`.

## Post-Run Red Team

The packet's main limitation is that machine-extracted labeled blocks are
review pointers, not checked technical support. Full eligible-anchor coverage
also does not mean complete paper understanding: unlabeled mathematics,
figures, tables, prose qualifications, appendix dependencies, macro semantics,
and proof correctness remain unchecked. The prior local record being
byte-identical answers source drift, not publication/retraction status.

## Handoff

Continue M21 locally with citation-context triage against the exact retained
TeX and the `62` preliminary M20 candidates. Keep formal scholarly class and
support status unpromoted unless primary technical sources are inspected. The
next subplan is
`docs/plans/literature_survey_north_star_m21_candidate_context_triage_subplan_2026-07-18.md`.
M22 remains a planning preview only until M21/G4 has an honest candidate/source
selection and the required source/status outcomes.
