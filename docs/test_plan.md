# Representative Paper Test Set and Validation Workflow

## Purpose

This document defines a small but meaningful validation set for the personal research assistant POC.

The point is to test the exact kinds of failures we already observed:
- wrong metadata merge,
- ambiguous paper title resolution,
- summary mismatch,
- weak provenance,
- and usability gaps.

---

## Recommended initial test set

Use at least the following categories.

### 1. Directly relevant arXiv paper
Example:
- NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport

Why:
- central to current work
- known target paper
- useful to test title matching and summary quality

### 2. Directly relevant journal / established publication paper
Example:
- Riemann Manifold Langevin and Hamiltonian Monte Carlo Methods

Why:
- canonical method paper
- good test of metadata correctness for older/highly cited works

### 3. Broad review paper
Example:
- Normalizing Flows for Probabilistic Modeling and Inference

Why:
- tests summary usefulness for synthesis tasks
- tests whether metadata and abstract are captured well

### 4. Ambiguous-title or similar-title paper
Choose a paper where nearby unrelated records are likely.

Why:
- tests whether wrong DOI / wrong Crossref merge is possible
- this is one of the most dangerous failure modes

### 5. Local PDF-only paper
A paper stored in the Google Drive library or local folder without relying on a perfect online metadata match.

Why:
- tests PDF extraction path
- tests fallback behavior when metadata is incomplete

### 6. One paper not directly relevant to current work
Use a clearly adjacent but not central paper.

Why:
- tests whether the system can remain conservative and not overstate relevance

---

## Validation workflow per paper

For each paper:

1. Ingest paper
   - from PDF, query, DOI, arXiv, or combined path
2. Record generated paper ID
3. Inspect metadata JSON
4. Inspect summary JSON
5. Check extracted text if a PDF was used
6. Run a find query
7. Run a show query
8. Add one paper-to-doc or paper-to-code link
9. Run a simple claim audit
10. Record verdict and issues

---

## Suggested validation record template

For each paper, fill in:

- Paper title:
- Input method: PDF / query / DOI / arXiv
- Paper ID:
- Metadata verdict: PASS / PASS WITH CAVEATS / FAIL
- Summary verdict: PASS / PASS WITH CAVEATS / FAIL
- Extraction verdict: PASS / PASS WITH CAVEATS / FAIL
- Link workflow verdict: PASS / PASS WITH CAVEATS / FAIL
- Claim-audit verdict: PASS / PASS WITH CAVEATS / FAIL
- Overall verdict: PASS / PASS WITH CAVEATS / FAIL
- Issues observed:
- Severity: P0 / P1 / P2 / P3
- Notes:

---

## End-to-end validation scenario

After validating individual papers, run one end-to-end scenario:

1. ingest 3–5 papers relevant to transport / HMC
2. create links from at least 2 papers to the HMC/transport chapters
3. run find queries for “transport”, “rmhmc”, “neural transport”
4. inspect results
5. attempt to use the outputs to support one small documentation improvement task
6. judge whether the tool saves time or creates more cleanup

This end-to-end test is critical. Even if individual commands pass, the system may still not be usable enough for real research work.
