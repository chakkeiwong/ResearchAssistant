# Research Assistant Validation Checklist

## Purpose

This checklist is for targeted validation of the personal research assistant POC before expanding features or trusting it for literature-backed chapter polishing.

The goal is not broad QA. The goal is to determine whether the current system is trustworthy enough for real research-development use and, if not, what must be fixed first.

---

## Core validation questions

1. Does paper ingestion create the right canonical paper record?
2. Does metadata resolution select the correct paper rather than a nearby false match?
3. Does extracted text correspond to the actual PDF contents?
4. Does the summary preserve the essential contribution of the paper?
5. Are paper IDs stable and deduplication sane?
6. Do links to code/documents work and persist correctly?
7. Is the claim-audit conservative enough to avoid misleading confidence?
8. Is the output usable enough to support literature-aware coding and documentation?

---

## Test categories

### A. Metadata correctness
Check:
- title correct
- authors correct
- year correct
- DOI/arXiv correct
- source URL plausible
- does OpenAlex/Crossref/arXiv merge cleanly?

Failure examples:
- wrong paper with similar title
- unrelated DOI attached
- incorrect year/authors

### B. PDF extraction correctness
Check:
- extracted text non-empty
- title visible in extracted text
- abstract visible in extracted text
- no catastrophic corruption

Failure examples:
- blank extraction
- unreadable output
- wrong file copied

### C. Summary correctness
Check:
- main contribution roughly right
- method family reasonable
- no obvious hallucinated claims
- confidence level appropriately low if uncertain

Failure examples:
- summary describes a different paper
- claims exactness where paper does not
- claims DSGE relevance where none exists

### D. Deduplication and identity
Check:
- same paper ingested twice should not create silent conflicting identities
- canonical ID stable enough for repeated use
- ambiguity is visible rather than hidden

Failure examples:
- duplicate records for same DOI/arXiv
- one paper ID reused for different papers

### E. Link workflow
Check:
- paper-to-code link saved
- paper-to-doc link saved
- retrieval of links works
- links remain readable and inspectable

Failure examples:
- broken target paths
- wrong target type
- links not returned in show/query output

### F. Claim-support audit behavior
Check:
- output is conservative
- does not overstate support
- clearly indicates limitation of current evidence extraction

Failure examples:
- “direct support” with only title-level match
- missing uncertainty note

### G. Practical usability
Check:
- commands understandable
- outputs inspectable
- no excessive friction in normal use
- useful enough to support real work

Failure examples:
- too much manual cleanup
- retrieval not good enough to save time

---

## Validation verdict scale

For each tested paper/workflow, record one of:
- PASS
- PASS WITH CAVEATS
- FAIL

And assign issue severity:
- P0 — correctness blocker
- P1 — high-priority usability blocker
- P2 — improvement needed but not blocking
- P3 — nice-to-have

---

## Go / No-Go criteria for using the assistant on real HMC chapter work

Minimum conditions before relying on the tool for literature-backed chapter polishing:

1. At least 5 representative papers ingested
2. No P0 metadata mismatch remains
3. No summary of a tested paper is materially about the wrong paper
4. Claim-audit remains conservative in all tested cases
5. Link workflow works for paper ↔ code and paper ↔ doc
6. At least one end-to-end workflow feels time-saving rather than time-consuming

If any P0 remains, do not trust the tool for high-stakes documentation support yet.
