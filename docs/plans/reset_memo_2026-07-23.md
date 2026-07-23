# Clean Reset Memo: Topic-to-Survey Product Handoff

Date: 2026-07-23
Branch: `main`
Repository: ResearchAssistant

## Restart Authority

This memo is the clean restart boundary after the bounded topic-to-survey
campaign. Read it before reopening older planning artifacts. Historical plans,
raw validation runs, downloaded papers, parser outputs, and transient campaign
roots are not active gates unless explicitly reintroduced by a new task.

## Product Goal

ResearchAssistant owns the generic workflow:

```text
topic -> central-paper candidates -> checked sources -> audit ledgers
      -> evidence projection -> deterministic survey candidate
      -> optional LaTeX render -> optional DynareMCP structure QA
```

DynareMCP is an optional document-neutral provider. It does not own discovery,
source truth, claim authority, prose, or final interpretation.

## Current Implementation

- `ra survey literature-review --topic ...` is the end-to-end command.
- Discovery is bounded, replayable, pairwise-facet aware, and preserves
  DOI/OpenAlex/arXiv aliases.
- OpenAlex OA PDFs can be downloaded under byte/domain/no-overwrite limits and
  parsed with the existing PDF extraction toolkit.
- PDF title identity is checked before extracted text becomes source evidence.
- Evidence authority remains `source_attributed` unless an exact hostile-reviewed
  packet authorizes `reviewed_primary` projection.
- LaTeX output is ASCII-safe; original extracted source text remains in JSON
  evidence artifacts.
- Completed runs are append-only and resume only after manifest/hash validation.

## Verified Topic Run

Topic: `Reinforcement learning for recommender systems for financial products and credit cards`

Final local artifact root:
`/tmp/ra-topic-survey-rl-finance-final2-Fi8bkv`

Terminal status: `insufficient_survey_evidence`.

The run reached discovery, source acquisition, projection, synthesis, PDF
rendering, DynareMCP QA, and hash-valid resume. It produced a diagnostic PDF,
but only one inspected source survived and it was `PERIPHERAL` to the complete
topic. Direct financial-product/card evidence and four scholarly roles remain
open. Do not call this a completed literature survey or publication-ready
document.

## Evidence Boundary

Citation counts, venue metrics, metadata nominations, PDF rendering, and
DynareMCP clean output are prioritization or structural diagnostics only. They
do not establish technical truth, centrality, literature completeness,
publication readiness, or expert authorship.

The next scholarly action is additional lawful source acquisition and primary
technical inspection, especially direct financial-product/card recommendation
work, competitors, and foundational/review sources. Do not weaken the thin-
evidence veto to make a document appear complete.

## Repository Hygiene

- Runtime source, tests, fixtures, operator documentation, and this reset memo
  are tracked.
- `.localresources/`, downloaded PDFs, parser/source caches, build products,
  test caches, replay trees, generated validation roots, generated review notes,
  and generated planning notes are ignored.
- Compact validation records are tracked only when they preserve a promotion
  gate, a release decision, source/claim/omission evidence, or a canonical
  regression fixture consumed by the test suite. They are force-added against
  the default `docs/validation/*` ignore rule and are listed in the closeout
  commit's staged file review. A tracked generated file must have one of these
  roles; all other generated files are removed from the index and ignored.
- Historical plans and reviews remain on the local filesystem for archaeology
  and are removed from the Git index unless active code, tests, documentation,
  or a hash-bound evidence record consumes them. Retained consumers are product
  fixtures, not active approval gates.
- `docs/plans/reset_memo_2026-07-23.md` is the authoritative tracked planning
  handoff for this restart boundary; templates and the small set of consumed
  plan fixtures remain tracked source material.

## Verification

- Full terminal suite with `CUDA_VISIBLE_DEVICES=-1`: `1873 passed, 229
  skipped` in 19m33s.
- The pre-fix suite had three failures: one 51-line CLI-facade guard and two
  phase-10 CPU-only tripwire checks. The facade was refactored into a named
  service factory; the tripwire suite was rerun under its required CPU-only
  environment and passed `10 passed`.
- Main affected workflow: `105 passed`.
- Seed and continuation regression partition: `39 passed`.
- Legacy survey partition: `216 passed`.
- DynareMCP document utility: `11 passed`.
- `python -m compileall -q src tests`: passed.
- `git diff --cached --check`: passed after the final repair was staged.
- Hygiene audit: zero unclassified untracked files; no tracked transient
  `pytest_tmp`, log, JUnit/XML, cache, downloaded-source, or parser-payload
  files. The remaining ignored-by-pattern tracked paths are the explicit
  regression/evidence exceptions described above.

## Restart Procedure

1. Confirm `git status --short --branch` and read this memo.
2. Use a fresh output root for any new campaign; never overwrite evidence.
3. State a new evidence contract before live or long research work.
4. Run focused tests before the affected suite.
5. Keep source, numerical/scientific interpretation, and engineering ledgers
   separate.
6. Request explicit direction before publication, credentials, destructive
   operations, or another external campaign.

No release, publication, tag, or external push is implied by this memo.
