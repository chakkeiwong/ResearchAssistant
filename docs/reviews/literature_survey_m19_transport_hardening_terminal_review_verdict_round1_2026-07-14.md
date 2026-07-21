# M19A Terminal Implementation And Result Review Verdict Round 1

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer
Verdict: `REVISE`

## Material Finding

The broad `except Exception` at
`src/research_assistant/survey/build.py:1855` covered response parsing and
normalization. An unexpected parser/programmer failure such as `RuntimeError`
could therefore become
`unavailable_transport_error/other_transport_failure`, allowing a complete
ledger and passing summary. This violated the reviewed fail-closed contract.

Required repair: distinguish known malformed JSON/XML from unexpected parser
or normalization failures, propagate the latter as a sanitized non-
interpretable boundary error, and add transport and worker-level regressions.

All reviewed JUnit counts/hashes, fake-run bindings, lineage, protected hashes,
harness-failure classifications, isolated wheel, nonclaims, parent status, and
draft approval boundary were otherwise consistent. No live authority was
present.

`VERDICT: REVISE`
