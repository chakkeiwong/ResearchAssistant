# Research Assistant Validation Run Log

## Purpose

This file records concrete validation runs of the personal research assistant POC.

Each entry should summarize:
- input method,
- observed behavior,
- verdict,
- issue severity,
- and recommended follow-up.

---

## Run 001 — NeuTra query-only ingest

### Input
- Command type: query-only ingest
- Query: `NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport`

### Observed behavior
- Paper ID was created successfully.
- `ra find --query "transport"` was able to retrieve the paper.
- `ra show --paper-id ...` returned structured JSON.
- Initial version wrongly merged an unrelated Crossref record.
- After metadata hardening, the unrelated Crossref record is now stored only as `crossref_candidate`, not merged into the primary metadata.

### Verdict by category
- Metadata correctness: PASS
- Summary correctness: PASS
- Retrieval workflow: PASS
- Claim-audit readiness: PASS WITH CAVEATS

### Severity
- Previously P0, now fixed for this case

### Notes
- This case is now a regression target and should not silently regress.

---

## Run 002 — CLI availability

### Input
- Command: `ra --help`

### Observed behavior
- CLI is installed and callable.
- Subcommands visible: `ingest`, `find`, `show`, `link-add`, `audit-claim`.

### Verdict by category
- CLI installation: PASS
- Basic command surface: PASS

### Severity
- None

---

## Run 003 — Query retrieval after ingest

### Input
- Command sequence:
  - `ra ingest --query ...`
  - `ra find --query "transport"`
  - `ra show --paper-id ...`

### Observed behavior
- Retrieval worked.
- Stored summary was accessible.
- Output was inspectable and useful.

### Verdict by category
- Search workflow: PASS
- Show workflow: PASS

### Severity
- None

---

## Run 004 — RMHMC paper ingest

### Input
- Query: `Riemann Manifold Langevin and Hamiltonian Monte Carlo Methods`

### Observed behavior
- Correct title, authors, year, and DOI were returned.
- Metadata merge looked consistent.
- This is a strong positive test for the canonical paper path.

### Verdict by category
- Metadata correctness: PASS
- Summary correctness: PASS
- Retrieval workflow: PASS

### Severity
- None

---

## Run 005 — DLHMC arXiv-ID-driven ingest

### Input
- Query: `Deep Learning Hamiltonian Monte Carlo`
- arXiv ID: `2105.03418`

### Observed behavior
- Initial version produced wrong authors because OpenAlex authors were preferred.
- After hardening, arXiv authors are now preferred when an explicit arXiv ID is supplied.
- Crossref remains quarantined as candidate only.
- Metadata confidence is high.

### Verdict by category
- Metadata correctness: PASS
- Summary correctness: PASS
- Provenance correctness: PASS

### Severity
- Previously P0, now fixed for this case

---

## Run 006 — Local PDF ingest from GoogleDrivePapers

### Input
- PDF: `Credit Risk and the Transmission of Interest Rate Shocks Palazzo(20).pdf`
- Query: `Credit Risk and the Transmission of Interest Rate Shocks Palazzo`

### Observed behavior
- Local PDF access worked.
- Ingestion pipeline executed.
- However, OpenAlex selected the wrong paper (`Feverish Stock Price Reactions to COVID-19*`).
- The improved resolver did not silently overstate confidence; it marked the match as low confidence and added manual-review notes.

### Verdict by category
- PDF path handling: PASS
- Conservative uncertainty behavior: PASS
- Final metadata correctness: FAIL

### Severity
- P0 correctness blocker for automatic local-PDF-based use

### Notes
- This failure remains active.
- The next hardening target is stronger candidate ranking using filename and extracted-title signals.

---

## Current overall status

### Strongly working
- CLI installation
- query-only ingest for some papers
- arXiv-ID-driven ingest
- canonical paper ingest
- conservative merge handling

### Not yet trustworthy enough
- local PDF ingest with ambiguous or weak metadata resolution
- title-candidate ranking from filenames / extracted titles

### Current recommendation
- Do not yet trust local-PDF automatic metadata resolution for high-stakes literature-backed writing.
- Continue hardening candidate ranking before using the assistant as an automatic paper-grounding tool for chapter polishing.
