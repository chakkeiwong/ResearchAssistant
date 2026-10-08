# Bank sales opportunity survey and product proposal

Read [the compiled PDF](salespitch_survey_proposal.pdf). The 33-page document develops the problem, ten papers' relevant methods and derivations, their application to corporate banking, a proposed forecast–outreach–allocation system, and an evaluation and implementation plan.

- [Main LaTeX source](salespitch_survey_proposal.tex), with chapters in [sections](sections/).
- [Bibliography](references.bib).
- [Downloaded paper catalog](../../dcos/papers/salespitch/README.md) and [source manifest](../../dcos/papers/salespitch/manifest.json). All ten citations have a local full-text PDF. Filenames use the full title, first author's surname, and publication year; filesystem-unsafe punctuation is normalized. The requested directory is **dcos/papers/salespitch**.
- [Technical and editorial review](review/final_review.md), [citation/file checks](review/deliverable_checks.json), and [22 numerical derivation checks](review/derivation_checks.json).

## Build

From this directory, run `bash build.sh`. It requires `pdflatex`, `bibtex`, `pdftotext`, and `pdfinfo`, plus the LaTeX packages declared in the source. The script runs LaTeX, BibTeX, and two further LaTeX passes, preserves logs under `build/`, and copies the final PDF here. No GPU or model training is involved.

From the repository root, run `python3 docs/salespitch/scripts/check_deliverable.py` to verify citation coverage, PDF signatures, source checksums, filenames, and the final build log. `scripts/check_derivations.py` uses NumPy and SciPy for deterministic mathematical checks; it explicitly hides GPU devices. These checks establish selected identities and document integrity, not bank-model effectiveness.

## Scope and source versions

This is a focused methodological survey and a proposed product design. No client data were supplied and no bank performance was measured. Full derivations cover the quantities used in the proposal; unrelated empirical tables and every theorem from the original papers are not reproduced.

Accessible author manuscripts are retained where appropriate. In particular, the local DeepAR manuscript has three authors, whereas the cited journal publication has four. The source catalog records this difference. Li et al. do not publish their complete prior/sampler specification in the article; the survey supplies an explicitly labeled estimation construction. A limitation in Elkan and Noto's labeling-rate argument is explained with a derivation and counterexample rather than silently carried into the bank model.

Research reading notes, OCR text, source retrieval records, and ResearchAssistant intake records are retained under `.localresources/bank-sales-2026-10-08/` at the repository root. The six final literature ledgers are in `review/`. The first compiled draft is preserved in `review/first_draft.zip` for substantive comparison.
