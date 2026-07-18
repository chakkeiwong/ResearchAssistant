# M21 Source Campaign Reconciliation

Date: `2026-07-18`
Milestone: `M21_live_source_status_and_anchor_intake`
Status: `CLOSED_G4_WITH_ONE_EXPLICIT_TEXT_PARSE_GAP`

## Question And Contract

The single authorized M21 campaign asked whether seven exact seed-cited arXiv
source packages could be retained under bounded credential-free transport and
yield honest text-only source/anchor candidates. It did not ask, and does not
establish, relevance, technical claim support, mathematical correctness,
publication/retraction safety, forward-citation coverage, literature
completeness, or human review.

## Immutable Live Evidence

- Root: `docs/validation/literature_survey_north_star_m21_seven_candidate_sources_2026-07-18/`
- Exactly 7 requests dispatched, 0 retries, 7 source packages retained.
- Retained root size: `66,766,356` bytes; cap: `500,000,000` bytes.
- Preserved execution commit in the live manifest: `3890a41c75ab7d7db7ef45d5c3d98b6784170217`.
- Preserved-source replay with the original execution bytes: `passed`.
- Repaired offline replay: `passed` with `6` parsed packages and `1` text-parse gap.
- Source package `1412.6980` SHA-256:
  `7d2362abfa27d56fd59b70d30b6d721311f78281009448318cb5147bf1cf7e0e`.

## Reconciled Outcomes

| arXiv ID | Outcome | Anchors | Evidence interpretation |
| --- | --- | ---: | --- |
| `1412.6980` | `closed_source_parse_gap` | 0 | The retained `arxiv.tex` is a 298-byte `\\includepdf` wrapper. PDF fallback is out of scope. |
| `1506.03365` | `accepted_and_parsed` | 11 | Machine-extracted review candidates only. |
| `1709.08894` | `accepted_and_parsed` | 65 | Machine-extracted review candidates only. |
| `1805.07277` | `accepted_and_parsed` | 18 | Machine-extracted review candidates only. |
| `1902.07197` | `accepted_and_parsed` | 130 | Machine-extracted review candidates only. |
| `2003.06635` | `accepted_and_parsed` | 42 | Machine-extracted review candidates only. |
| `2003.06788` | `accepted_and_parsed` | 22 | Machine-extracted review candidates only. |

Total machine anchors: `288`. Supported claims: `0`. All publication,
retraction, version, and human-support fields remain `NOT_CHECKED` or
`SOURCE_GAP_BLOCKER` as applicable. Forward coverage remains
`unavailable_out_of_scope`, non-blocking.

## Defect And Repair

The original live root recorded `1412.6980` as `accepted_and_parsed` because
the wrapper itself was parseable TeX. That was wrong relative to the M21
technical-text/anchor target. The active runner now detects zero structural
yield and classifies the exact wrapper as
`SOURCE_AVAILABLE_TEXT_PARSE_GAP_PDF_FALLBACK_OUT_OF_SCOPE`.

The original root was not edited. Replay permits exactly this historical
projection and rejects unrelated route, source, derived-artifact, aggregate,
execution-source, input, or hash tampering. Focused campaign tests pass
`13/13`; the related M20/M21/arXiv slice passes `45/45`; compile, static
boundary, JSON, and diff checks pass. Claude was healthy under a tiny probe but
did not complete the bounded packet review after two prompt/read attempts; this
procedural limitation is recorded and did not override the local evidence.

## Decision Table

| Decision | Primary criterion | Veto status | Interpretation | Next action |
| --- | --- | --- | --- | --- |
| Close M21/G4 | Every ID has one honest outcome and replay passes | No campaign veto; one allowed source-format gap | `PASS` within bounded source/anchor scope | Hand off to refreshed M22 planning only |
| Promote technical claims | Checked primary anchors plus human decision | Not met | `REJECTED`; zero claims supported | M22 must perform genuine review |
| Claim source completeness | All source routes/versions/forward coverage checked | Not met | `NOT_CONCLUDED` | Preserve gaps and unavailable forward coverage |
| Treat parser gap as campaign failure | Gap is per-paper, not harness-wide | Not met | `NOT A CONTINUATION VETO` | Do not retry or use PDF fallback |

## Forbidden Follow-On Actions

No M21 retry/rerun, PDF fallback, new ID/route, provider/credential access,
M22 human decision, Git integration, push, release, or north-star completion
claim follows from this record.

## Exact M22 Handoff

M22 may refresh its planning inputs from this record and the immutable root.
M22 remains non-executable until its genuine human identity/attestation policy,
predeclared mission matrix, rights/privacy boundary, execution-commit binding,
and required user/human participation are separately satisfied.
