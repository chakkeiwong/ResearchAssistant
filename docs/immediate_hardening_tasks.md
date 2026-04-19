# Immediate Hardening Tasks

## Priority 0 — Metadata merge correctness

### Problem
Title-based metadata resolution can incorrectly merge unrelated Crossref results into a correct OpenAlex match.

### Why this matters
This contaminates the canonical paper record and makes all downstream uses less trustworthy:
- summaries,
- relevance judgments,
- citations,
- chapter-polishing support.

### Immediate engineering tasks
1. Add source-specific confidence scoring.
2. Treat DOI and arXiv exact matches as high-confidence anchors.
3. Require conservative title similarity before merging Crossref-by-title.
4. Preserve provider-specific metadata separately even after merge.
5. Add `metadata_confidence` and `merge_notes` fields to summary or metadata records.
6. Refuse automatic merge when signals disagree materially.

### Acceptance criteria
- NeuTra query should not absorb an unrelated Crossref DOI.
- Ambiguous title queries should surface uncertainty rather than silently merging.

---

## Priority 1 — Provenance clarity

### Problem
Current summaries do not make source provenance sufficiently visible.

### Immediate engineering tasks
1. Store source-of-field provenance for key metadata:
   - title
   - authors
   - year
   - DOI
   - abstract
2. Add `provenance` block to metadata file.
3. Add `summary_basis` / `summary_confidence` notes to summaries.

### Acceptance criteria
- A reviewer can see whether a field came from OpenAlex, Crossref, arXiv, or local extraction.

---

## Priority 2 — Retrieval trust

### Problem
Find/show works, but users cannot yet tell whether a record is high trust or low trust.

### Immediate engineering tasks
1. Show curation status prominently.
2. Show metadata confidence prominently.
3. Show mismatch warnings prominently.
4. Add a `status_summary` line in CLI output.

### Acceptance criteria
- A user can tell at a glance whether a record is safe to use for writing support.

---

## Priority 3 — Claim-audit realism

### Problem
Claim audit is currently placeholder-level and not evidence-based.

### Immediate engineering tasks
1. Keep classification conservative by default.
2. Distinguish:
   - direct support
   - background only
   - insufficient evidence
3. Add evidence snippets later only after metadata trust improves.

### Acceptance criteria
- Claim audit never overstates confidence before real evidence extraction exists.
