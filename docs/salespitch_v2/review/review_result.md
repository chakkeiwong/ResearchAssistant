# Terminal review — version 2

Review date: 9 October 2026 (Asia/Hong_Kong). Scope: the requested new survey and product proposal, its bibliography, downloaded source collection, mathematical checks, and compiled PDF. This is author self-review, supported by primary-source inspection and deterministic checks; it is not an independent referee report or human readability acceptance.

## Decision

| Decision | Primary criterion | Veto checks | Main uncertainty | Next justified action | What is not concluded |
|---|---|---|---|---|---|
| Deliver the revised proposal draft | Complete modular design, self-contained derivations for the uses made of all 12 cited works, local source copies, and successful PDF build | No missing cited PDF, unresolved citation, LaTeX warning, or failed deterministic check remains | Total-wallet visibility, macro identification, flow/FX dependence, choice-set completeness, and revealed preferences | Bank data audit followed by a separately budgeted forecasting prototype and phased validation | No predictive superiority, commercial return, identified GDP elasticity, or production readiness |

No stochastic method comparison or bank-data experiment was performed. A statistical ranking or stochastic inference-status table would therefore have no empirical entries. Human evaluation of the explanatory voice remains pending; this draft is ready for that review.

## Scientific repairs and boundaries

1. The problem definition now models gross native-currency inflows and outflows jointly. Partial-wallet observation is treated explicitly; neither client count nor a hidden-state model identifies unobserved competitor activity.
2. The scenario chapter distinguishes conditioning, intervention, and unit counterfactuals, derives a confounding example and the adjustment argument, and proves the positive GDP response under stated restrictions. A positive one-step state loading does not ensure a positive multistep response. GDP effects remain imposed or estimated predictive relations until a defensible causal design is supplied.
3. The proposed calendar term is restricted to finite known calendar predictors. Unrestricted date effects would absorb a common GDP regressor; residual factors also require separation restrictions. Regularization is not causal identification.
4. The source-inspired Gaussian filter, smoother, lag covariance, EM updates, and likelihood are reconstructed. The proposed hurdle likelihood correctly handles zeros, positive observations, missing coordinates, covariance submatrices, and the change-of-variable Jacobian. Its approximate inference is not described as exact Kalman filtering or exact EM.
5. The Froot–Scharfstein–Stein derivation now distinguishes net investment profit `P(w)` from total value `G(w) = w + P(w)`. When fees or carry change expected wealth, the hedge first-order condition retains `1 + P_w`; omitting the one would change the target.
6. CARA-normal certainty equivalence is derived with its domain stated. Unbounded lognormal losses can make exponential expected utility divergent. A finite simulation does not prove integrability. The proposed first release explicitly chooses mean–variance preferences with finite second moments or a justified bounded/default-limited wealth model.
7. The hedge derivation uses net exposure and the joint covariance of flow and FX. Choice utility is independent of the cash-flow model's estimation objective. Product choice, price response, and the causal value of outreach remain distinct estimands.
8. The mixed-logit explanation distinguishes integration of a product for panel choices from a product of separately integrated probabilities, and states the scope of the displayed approximation argument.
9. Validation respects outcome maturity and macro publication dates. Conditioning on realized future macroeconomic inputs is labeled an oracle diagnostic. Six practical competitors are constructed and evaluated by commercially relevant segment under the proposed protocol.
10. The rendered title was repaired to avoid an awkward word break. No substantive mathematical content was removed for layout.

## Primary sources and search coverage

All 12 cited works have readable local PDFs, totaling 307 pages, named using the requested title/surname/year convention. The source catalog and source-support ledger record inspected methods, equation or section anchors, local versions, application limits, and SHA-256 checksums. Earlier manuscript, transcription, supplementary-long-version, and OCR differences are disclosed in the manuscript and source manifest.

The six separate literature ledgers are `source_support.json`, `citation_venue_metadata.json`, `backward_snowball.json`, `forward_snowball.json`, `claim_support.json`, and `omitted_paper_risks.json`. The backward pass records 39 relevant candidate dispositions. Ten DOI forward queries returned bounded samples of 100 records each; two additional title queries were rate-limited, and citation-count requests were unavailable. These samples do not establish an exhaustive search or global citation ranking. Metadata-only follow-up candidates are not used as technical support. The omission register includes structural macroeconometrics, intermittent demand, contemporary forecasting models, richer choice systems, and fuller corporate-finance models.

The official GluonTS DeepAR and Deep State Space network sources were inspected for the narrow input distinction relevant to the survey: DeepAR uses lagged target inputs; Deep State Space generates parameters from covariates and conditions latent states through filtering. The cached code versions, hashes, and inspected ranges are recorded in `code_inspection.json`. No full implementation call-chain, parity, historical-paper reproduction, or production capability claim is made. Those questions are not checked.

## Checks and rendered review

Twenty-three deterministic checks pass. They cover direct Gaussian conditioning against filter/smoother/lag-covariance formulas, the EM quadratic objective, capture nonidentification and bounds, net-flow variance, the GDP derivative and negative-AR counterexample, financing-value derivatives, Gaussian CARA integration, hedge value and first-order conditions, logit derivatives and invariances, panel mixing, and the doubly robust score identities. The exact results are in `mathematical_checks.json`.

Every PDF page was rendered and visually inspected through the numbered four-page contact sheets, with full-size checks of the title and selected equation-heavy pages. Equations, bibliography links, headings, and text remain inside the page boundaries. Short final chapter pages are retained rather than compressing the derivations. LaTeX and BibTeX checks find no warnings, unresolved references, or overfull/underfull boxes. The final PDF checksum and page count are in `document_checks.json`.

The build manifest records the checkout, commands, environment, final-build wall time, and artifact locations. No GPU or framework import was used. The source ZIP contains all required LaTeX inputs and passes archive integrity checks.

## Strongest remaining alternative explanation

A mathematically coherent scenario model may fit common trends or changes in bank capture rather than a firm's structural cash-flow response. Even accurate bank-observed forecasts may misstate total exposure; even valid utility calculations may miss the client's private information or available competitor offers. These are data and identification risks, not defects that PDF compilation or additional model complexity can settle. External capture information, vintage-correct held-out forecasts, observed choice sets, and randomized outreach evidence would respectively address them.
