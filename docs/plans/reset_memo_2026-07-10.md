# Reset Memo: Clean Restart Handoff - 2026-07-19

## Objective

Leave the repository in a reproducible, reviewable state for the next
research-assistant session. Source, tests, scripts, and durable plans/results
that support promotion, vetoes, or claims are versioned. Generated operational
output is ignored and can be regenerated into a fresh validation root.

## Current State

- Branch: `main`; the working branch contains the pending local implementation
  and documentation changes and will be pushed after this cleanup commit.
- Active research boundary: M20 arXiv-only backward discovery is closed within
  its bounded source/anchor contract; M21 retained-source intake is closed with
  one explicit text-parse gap; M22B0 is ready for genuine human review.
- Forward citation coverage remains unavailable and non-blocking. No claim of
  literature completeness, technical claim truth, product readiness, or
  north-star completion is made.
- The next meaningful action is the genuine human review described in
  `docs/plans/literature_survey_north_star_m22b_genuine_human_review_subplan_2026-07-18.md`.

## Repository Boundary

Tracked:

- implementation under `src/`, executable helpers under `scripts/`, and tests;
- authored plans, reset memos, result notes, and review verdicts/bundles under
  `docs/plans/` and `docs/reviews/`;
- compact, claim-relevant M20/M21/M22 manifests, ledgers, decision records, and
  reviewer worksheets explicitly selected from `docs/validation/`.

Ignored:

- raw/private research intake under `local_research/`;
- generated validation roots except explicitly selected compact evidence;
- downloaded source/PDF/text bodies, copied execution sources, logs, JUnit
  transcripts, replay state, wheels, build products, caches, and local review
  transcripts under `.claude_reviews/`.

The policy is intentionally conservative: an ignored artifact can be rebuilt
from tracked code and plans, while a promotion or claim must be supported by a
tracked result note and its compact evidence record.

## Evidence Preserved For Restart

- M20 arXiv-only: run manifest, route ledger, backward/forward ledgers,
  candidate classifications, source/claim/omission support, combined evidence,
  offline replay, artifact inventory, and terminal result.
- M21 seven-source campaign: run manifest, route/source status, claim support,
  quarantine status, offline replay, artifact inventory, and terminal result.
- M21 candidate triage and retained anchors: compact inventories, triage/risk,
  anchor/source/claim records, and manifests.
- M22B0: production reconciliation result, packet ledgers, retained-evidence
  reconciliation/anchor records, source-intake status, and the human review
  packet plus readable worksheets.

These records preserve outcomes and limitations, not raw paper content. The
result notes remain the authoritative interpretation and explicitly separate
hard vetoes, descriptive diagnostics, and nonclaims.

## Validation And Hygiene

- Run `git diff --check` before committing.
- Confirm every non-ignored filesystem file is tracked with
  `git ls-files --others --exclude-standard` returning no paths.
- Confirm the selected compact evidence parses as JSON where applicable.
- Run focused tests for the changed implementation and review/reconciliation
  surfaces; do not rerun live, credentialed, GPU, or human-boundary actions.

## Restart Procedure

1. Start from a clean checkout of `main`.
2. Create a fresh, versioned output root under `docs/validation/` or another
   explicitly local run directory; do not reuse an old root.
3. Read the current M22B subplan and the M20/M21 result notes before any action.
4. Obtain genuine human participation before importing human decisions. Agents,
   fixtures, and generated worksheets must not fill the attestation.
5. Keep forward coverage unavailable unless a separately authorized method
   changes that boundary.

## Nonclaims And Blockers

- No technical paper claim is promoted without checked source anchors and
  genuine human disposition.
- No metadata, citation count, parser output, or source availability is treated
  as technical claim support.
- No human review, legal identity proof, literature completeness, product
  readiness, release, public message, or north-star completion follows from
  this cleanup.
- Raw/generated artifacts are intentionally absent from Git; their paths in
  result notes are historical references to local evidence roots.

## Handoff

This memo is the clean restart boundary. The next safe step is to conduct the
predeclared M22B human review against the tracked packet/worksheets, then record
the receipt-bound result and refresh the M23 handoff. Do not reopen superseded
provider, credential, approval-token, or PDF-fallback loops.
