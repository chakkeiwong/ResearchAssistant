# Final technical and editorial review

Date: 2026-10-08. Deliverables: `../salespitch_survey_proposal.pdf`, editable LaTeX and bibliography, build script, and ten full-text source PDFs under `dcos/papers/salespitch/`. Scope: a self-contained reconstruction of the methods used in the bank proposal, not a reproduction of every theorem or empirical table in the original papers. Reader: a banking quantitative/product audience familiar with probability, regression and calculus.

## Technical review

The design distinguishes three quantities throughout: probability of an event at this bank, incremental contribution from assignment to a defined outreach protocol, and net contribution after outreach cost under salesperson constraints. Assignment effects include failed contact attempts; multiplying them again by delivery probability would double-count non-delivery. An event at another bank is unobserved market need but still a valid zero for a fully observed own-bank event target. Overlapping outcome windows and repeat contacts are addressed explicitly.

Checked source-sensitive details include global representability without unnecessary client identifiers; the finite-memory qualification and dependent-client limitation; monthly risk sets and repeated spells; the BG/NBD beta factor and initial-active convention; Li's preceding-month purchase dummy and unavailable sampler details; logistic boosting's factor-of-two score conversion; DeepAR manuscript/journal differences; the AIPW conditional-bias expansion; and the PU positive-validation estimator's overlap counterexample. Generic covariance updates in the reconstructed cross-selling sampler retain all parameter-dependent hierarchical densities. No model-specific performance assertion is borrowed from a different application.

The proposed first model is a regularized pooled monthly hazard with appropriate product risk sets and partial pooling, supplemented by count/amount components where relevant. Boosting and DeepAR remain candidates for measured comparisons. A distinct causal model and a constrained allocation problem are required for scarce sales capacity. Historical propensity prediction alone cannot establish incremental commercial value.

The six literature ledgers identify support, metadata, backward and forward candidates, source-to-claim mappings, and omissions. The forward search is bounded: sampled index neighborhoods do not establish comprehensive coverage, and the tutorial-specific identity query was rate-limited after a wrong identifier was detected and excluded. No omitted paper supplies hidden technical evidence. The survey's scope is declared rather than represented as an exhaustive 2026 literature review.

## Mathematical and build evidence

- `derivation_checks.json`: 22 deterministic CPU-only checks passed. They cover BG/NBD integration and forecast formulas, AIPW bias cancellation, the PU counterexample and weighted risk, negative-binomial moments, logistic score conversion, horizon survival, a monthly forward recursion, and exact enumeration of the hypothetical capacity example. They check selected identities, not every line of mathematics and not any bank model.
- `deliverable_checks.json`: ten citation keys equal ten bibliography keys and ten paper-manifest entries; PDF signatures, filename suffixes and SHA-256 checksums match; final PDF equals the compiled copy.
- `build.sh`: pdflatex, BibTeX and two subsequent LaTeX passes succeed. The final log has no undefined citations/references, LaTeX/package warnings, overfull or underfull boxes. The PDF has 33 A4 pages.
- All 33 final pages were inspected in `final-v2-contact-sheet-1.jpg` through `final-v2-contact-sheet-4.jpg`. Pages 2, 8, 14, 19, 20, 24 and 33 were also inspected at 125 dpi: contents, BG/NBD, cross-selling estimation, causal derivations, allocation and bibliography. Equations and tables stay inside the margins; no overlaps or clipped text were observed. The contents now fit on one page, and the appendix starts on a fresh page. The rendered evidence is retained in `review/` and `build/pages/`.

No customer dataset, train/test result, randomized experiment, model runtime benchmark or bank revenue result exists for this task. No empirical superiority or default-readiness claim is made. The proposed pilot and comparisons remain necessary.

## Comparison with the protected draft

The first 21-page draft is retained in `first_draft.zip`; the revision has 33 pages. The source comparison counts 8,451 versus 14,108 whitespace-delimited LaTeX tokens (a reproducible text-size diagnostic, not linguistic word counts). This is an expansion and correction, not a shortening exercise. The original seven core papers remain, and recurrent survival, boosting and DeepAR are developed in the final ten-paper set. `revision_comparison.json` preserves the exact equation-label differences.

| Removed or renamed draft label | Substantive disposition |
|---|---|
| bgnbd-active | Corrected erroneous beta factor B(a,b+x+1) to B(a,b+x); now bgnbd-A, with integral derivation. |
| bgnbd-dropout | Preserved with derivation as bgnbd-D. |
| bgnbd-future | Conditional intensity integral retained in prose/math and extended to posterior integral and hypergeometric form. |
| bgnbd-likelihood | Preserved as bgnbd-conditional. |
| cate | Potential-outcome contrast retained as tau and uplift identification; margin and event effects distinguished. |
| event-likelihood | Expanded into survival-product, first-event and row-loglik with censoring/risk sets. |
| hurdle | Count hurdle identity retained unnumbered, with NB truncation; positive-amount version appears as hurdle-value. |
| logistic-residual, tree-newton | Reconstructed in full log odds as boosting-newton, with explicit conversion to the source's half-score. |
| pilot-effect | Randomized assignment contrast retained in prospective-trial prose; equal-capacity policy comparison added. |
| proposed-hazard | Replaced by hazard-model plus the integrated product specification; arbitrary client intercepts are no longer presumed estimable. |
| random-effect, shrinkage | Retained and expanded into a complete-square normal shrinkage derivation and an explicit cold-start treatment. |
| scar | Retained as the stated SCAR condition, pu-lemma and weighted-loss derivation; unsupported labeling-rate inference repaired. |

No measured empirical finding was deleted: neither draft used bank data. Qualifications about partial bank visibility, short calendar coverage, causality, timestamp leakage and business validation were retained and strengthened. The revised document also includes a recurrent-event source, a worked four-client capacity calculation, a feasible 36-month split, a prospective experiment distinction, power arithmetic and a bounded implementation sequence.

## Editorial assessment

The argument proceeds from bank outcomes and timing to pooled estimation, product history, causal outreach and capacity allocation. Method mathematics is in the relevant main sections, with a notation/source index in the appendix. Assumptions precede consequential formulas; examples are explicitly hypothetical. The TOC, tables and bibliography were revised after rendering. Author inspection is not a substitute for a human reader's judgment of naturalness, which remains pending.

| Decision | Evidence status | Remaining uncertainty | Next justified action |
|---|---|---|---|
| Deliver the survey and product proposal | Sources retained; selected identities and document integrity pass | Bounded literature coverage and human readability assessment | Read the PDF; use the proposal to define a bank-data pilot. |
| Promote a bank model or claim commercial improvement | Not established | No bank data or prospective results | Execute a separately authorized, predeclared evaluation when data and product definitions exist. |

Strongest alternative explanation for future forecast success is natural customer propensity or label leakage rather than effective outreach. A prospective equal-capacity trial with complete outcome capture distinguishes that explanation. The weakest present evidence is domain transfer: methodological coherence and consumer-bank precedent do not establish corporate-bank returns.
