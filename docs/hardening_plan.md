# Research Assistant Battle-Readiness Hardening Plan

## Purpose

This document is the follow-up planning artifact after targeted validation.

The goal is to convert observed test results into a coherent hardening plan before:
- expanding features,
- trusting the tool for literature-backed chapter polishing,
- or proposing broader adoption.

---

## Current stage

The research assistant is currently a functional proof-of-concept backend.
It is not yet battle ready.

That means the correct engineering posture is:
- stabilize first,
- expand second.

---

## Observed validation findings so far

### Confirmed P0
- Query-based metadata resolution can merge the wrong Crossref record into an otherwise correct OpenAlex match.
- Local PDF ingest can still select the wrong OpenAlex paper from weak title matching.
- These are correctness blockers because they can contaminate summaries and downstream literature writing.

### Confirmed P1
- Retrieval and show workflows are usable, but trust in the result is capped by metadata mismatch risk.

### Confirmed strengths
- CLI installation works.
- Local store, ingest, find, and show workflows all execute conceptually as intended.
- The architecture is usable enough to produce real signals from early testing.
- Conservative confidence signaling is materially better than the initial silent-wrong behavior.

---

## Strategic architecture update

The project should now be understood as having four major subsystems:

1. **Core local research store and CLI**
2. **Multi-parser scholarly document understanding layer**
3. **Citation-graph discovery layer (Semantic Scholar + OpenAlex)**
4. **Paper organization / download / review workflow**

This is a stronger and more realistic architecture than relying on:
- one parser,
- one metadata API,
- or one-step automatic ingest.

### Benchmark stabilization requirement

All major parser and metadata improvements should now be evaluated against a benchmark corpus, not only ad hoc real-paper testing.
The benchmark corpus should have three classes:
- synthetic LaTeX papers with exact ground truth,
- arXiv source/PDF pairs where source-derived structure acts as near-ground truth,
- real-world acceptance cases for manual validation.

---

## Hardening plan structure

For each observed issue, record:

- Issue ID
- Symptom
- Root cause hypothesis
- Severity
- Affected workflow
- Proposed fix
- Validation method
- Owner
- Status

---

## Severity definitions

### P0 — correctness blocker
Examples:
- wrong paper metadata attached to the summary
- unrelated paper merged into canonical record
- claim audit overstates support in a misleading way

If any P0 remains, do not rely on the tool for serious literature-backed documentation.

### P1 — major usability blocker
Examples:
- repeated manual correction needed
- poor retrieval quality for real queries
- unstable file IDs or duplicate handling

### P2 — important improvement
Examples:
- weak summary fields
- missing citation graph query
- insufficient provenance details

### P3 — enhancement
Examples:
- convenience commands
- nicer outputs
- more polished adapter surface

---

## Likely hardening priorities

### Priority 0: Metadata correctness
Questions:
- Are we matching the correct paper?
- Are Crossref/OpenAlex/arXiv merges too aggressive?
- Should source precedence rules be stricter?

Likely fixes:
- title similarity threshold before merge
- DOI/arXiv exact match preference
- do not merge low-confidence records automatically
- explicit `metadata_confidence` field
- candidate-based ranking over multiple OpenAlex results instead of taking the top result blindly
- use filename-derived title and extracted-title heuristics as ranking anchors for local PDF ingest
- introduce explicit candidate-review mode instead of always auto-accepting one result

### Current status
- Crossref false-positive merge: improved significantly
- arXiv-priority author/title/abstract precedence: improved significantly
- local PDF / weak title matching: still unresolved and remains the main active correctness blocker

### Priority 1: Multi-parser document understanding
Questions:
- Can one parser be trusted for academic PDFs?
- Can parser disagreement be used as a confidence signal?
- Can title/authors/abstract extraction become more reliable with multiple parsers?

Likely fixes:
- define a `ParsedDocument` schema
- support multiple parsers: pdftotext, Marker, GROBID, MinerU, optional MarkItDown
- normalize parser outputs
- reconcile title/authors/abstract via agreement scoring rather than naive majority vote
- preserve disagreement reports and parser provenance
- build benchmark papers with exact expected title/authors/abstract/sections
- add parser benchmark harness and fixture-based parser comparison tests

### Priority 2: Discovery and citation graph support
Questions:
- Can we discover large relevant literatures without manual Google Scholar exploration?
- Can we trace papers citing a seed paper, and papers citing those papers?

Likely fixes:
- Semantic Scholar as primary citation/discovery engine
- OpenAlex as fallback and enrichment
- add discovery commands for citing / cited-by / related work / clustered survey candidates
- cache graph results locally

### Priority 3: Paper organization and download workflow
Questions:
- Can the system search, download open versions, classify, rename, and propose folder placement for papers?
- Can it do so conservatively, with review instead of dangerous auto-moves?

Likely fixes:
- add discovery-download pipeline
- detect open versions only
- save to inbox first
- generate organization proposals with filename / folder / tags / duplicate candidates
- require user approval before final move into the main paper library

### Priority 4: Provenance and summary trust
Questions:
- Can we see which fields came from which source?
- Can summaries make uncertainty visible?

Likely fixes:
- provenance fields per metadata source and parser
- draft summaries should flag uncertainty
- support conservative summaries by default

### Priority 5: Better retrieval and links
Questions:
- Are queries useful enough in real workflows?
- Are code/doc links easy to maintain?

Likely fixes:
- search index improvements
- richer show output
- dedicated paper-to-doc and paper-to-code listing commands

### Priority 6: Claim-audit realism
Questions:
- Is the audit too weak or too strong?
- Does it overclaim support?

Likely fixes:
- classify based on explicit evidence snippets
- force `insufficient_evidence` unless strong support is found
- preserve human-review requirement

### Priority 7: Adapter maturity
Questions:
- Is the MCP layer really useful yet?
- Should CLI remain primary until backend stabilizes?

Likely fixes:
- keep MCP thin
- stabilize backend first
- only then expand native assistant integrations

---

## Suggested hardening sequence

1. Fix local-PDF metadata correctness through candidate-review mode
2. Add multi-parser document understanding layer
3. Add citation-graph discovery subsystem
4. Add download-and-organize proposal workflow
5. Improve provenance and summary trust indicators
6. Improve retrieval and show/link commands
7. Strengthen claim-audit conservatism and evidence extraction
8. Validate end-to-end workflows again
9. Only then use for high-stakes chapter-polishing support
10. Only after that, expand assistant integrations further

---

## Near-term implementation plan

### Track A — Multi-parser reading subsystem

#### Goal
Produce a high-confidence structured paper representation from local PDFs.

#### Deliverables
- parser abstraction
- parser result schema
- parser orchestrator
- parser reconciliation logic
- parser confidence / disagreement report

#### Initial parser set
- pdftotext fallback
- Marker
- GROBID
- MinerU
- optional MarkItDown as lower-fidelity auxiliary signal

#### Success criterion
The local PDF ingest path should either:
- resolve title/authors/abstract correctly, or
- clearly require manual review with interpretable candidate evidence.

### Track B — Citation-graph discovery subsystem

#### Goal
Replace painful manual literature graph traversal.

#### Deliverables
- Semantic Scholar query module
- OpenAlex fallback module
- graph traversal commands:
  - citing
  - cited-by
  - depth-2 exploration
  - related work
- local cache for discovery results

#### Success criterion
For a seed paper like NeuTra, the assistant can produce a useful first-pass list of:
- papers citing it,
- important second-order papers,
- likely criticisms,
- likely remedies,
- and nearby applications.

### Track C — Download / classify / organize workflow

#### Goal
Support your real paper-library workflow.

#### Deliverables
- discovery-download command
- open-access version detection only
- inbox download target
- AI-assisted folder/filename/tag proposal generation
- duplicate-candidate detection
- approval-before-move workflow

#### Success criterion
A set of discovered papers can be downloaded, proposed for organization, and reviewed efficiently without dangerous auto-renaming or auto-moving.

---

## Go / No-Go decision template

### Go
If:
- no P0 issues remain in the main ingest paths,
- parser consensus behaves conservatively,
- discovery results are useful enough to reduce manual search pain,
- and at least one end-to-end research workflow becomes meaningfully faster.

### No-Go
If:
- local paper ingest remains frequently wrong,
- parser disagreement is hidden rather than surfaced,
- discovery results are noisy and not useful,
- or the user spends more time repairing outputs than benefiting from them.

---

## Definition of battle ready for the personal version

The tool is battle ready for personal research use if:

1. representative papers ingest correctly or enter explicit review mode
2. metadata mismatch is rare and visible when uncertain
3. parser disagreement is surfaced and useful
4. paper summaries are good enough for guided use
5. paper-to-code/doc links are reliable
6. claim-support audit does not overstate evidence
7. at least one real literature survey or chapter-writing workflow is substantially faster
8. citation discovery is good enough to reduce manual graph traversal pain

That should be the standard before using the tool for high-stakes literature surveys or chapter polishing.
