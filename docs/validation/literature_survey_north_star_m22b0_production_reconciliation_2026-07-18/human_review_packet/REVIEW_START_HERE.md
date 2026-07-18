# M22B Human Review: Start Here

This is the reviewer-facing guide for the selected Neural Optimal Transport evidence. The adjacent JSON files are machine interchange artifacts; you do not need to understand their schema to perform the review.

## What this review is

The packet contains 7 paper-level claim decisions, 7 source-safety decisions, 58 omission-risk decisions, and one workflow-blocker decision. The packet SHA-256 is `0e2fe0a04a93a7dc418434cbe8fd87d20b3a8df65fd127beba0e95bf09b9a7e0`; the selected queue SHA-256 is `dfac76952f156ca082a7d332f95e1c03623c40dc150f5a4c52dba9a423a608d9`. Neither is changed by this guide.

Your task is to record what the retained evidence actually supports. You are not being asked to prove that the survey is complete, rank methods, or approve final prose. It is valid to reject every claim candidate and leave the workflow blocker open.

## Review order

1. Read `claim_review_worksheet.csv`. For each paper, open the generated `source_reading/.../README.md` named in `local_source_to_inspect`, then inspect its listed local text files and section/line pointers. Decide whether one precise technical claim is supportable. Use `rejected_or_blocked` when it is not. Do not turn an anchor title, citation count, abstract, or machine parser output into a claim.
2. Read `source_safety_worksheet.csv`. For each source, check the five listed status/version questions. Choose `checked_clear` only when the checks are actually documented; otherwise choose `blocked` or `quarantined` and explain why.
3. Read `omission_review_worksheet.csv`. These are not 58 separate demands to find more papers. They are risks retained so that unused bibliography entries, identifier-free references, the 1412.6980 parse gap, and unavailable forward citations cannot disappear. Choose whether each risk stays open, is omitted for this recorded scope, or requires expansion.
4. Read `workflow_blocker_worksheet.md`. This is derived from the seven claim decisions; it is not a new paper review. Leave it open if no reviewed supported technical claim exists.
5. Complete `human_attestation_worksheet.md` and the supplied `human_attestation_template.json`. The attestation says that the decisions are yours and that you understand the limitations; it is not legal identity proof.

## Decision vocabulary

- Claim support: `human_reviewed_passed` only for a precise claim tied to checked technical text and exact retained anchor IDs. Otherwise use `rejected_or_blocked` with a reason and next action.
- Source safety: `checked_clear` means all five checks were performed and no notice remains. `blocked` means the checks could not be completed. `quarantined` means a retraction, withdrawal, version conflict, erratum, or other explicit safety concern was found.
- Omission risk: `acceptable_omission` closes only the current bounded scope; `out_of_scope` records a deliberate scope exclusion; `must_inspect`, `expand_scope`, and `blocked_pending_source` keep work open. None means literature completeness.
- Workflow blocker: `resolved_by_reviewed_evidence` is allowed only when the required claim rows genuinely provide supported claims. Otherwise use `remains_open`.

## Important limitations

- Forward-citation coverage is permanently unavailable and non-blocking; it is not zero citations and not complete coverage.
- The 55 unused identifier-bearing bibliography entries and 195 identifier-free units are visible omission risks, not relevance rejections.
- `1412.6980` has a source-format parse gap. Do not infer its contents from metadata.
- The seven source rows were selected because they were source-located in the seed, not because the machine proved relevance or quality.
- A completed receipt can establish that a human made decisions; it cannot establish claim truth, source safety in fact, scientific correctness, or north-star completion.

## Return

Fill the CSV/Markdown worksheets and return them with the completed JSON attestation template. Codex may mechanically transcribe your stated choices into the exact decision envelopes, but you must inspect the transcription before attesting. Do not edit `human_review_packet.json` or change its packet hash.

Machine queue path (for conversion only): `/home/chakwong/research-assistant/docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/.artifact_state/sets/s-2312a9bc0cbef0574c4746426ea3473d6c853db64db6723b24d8e9bbd958dd25/review_queue.json`
