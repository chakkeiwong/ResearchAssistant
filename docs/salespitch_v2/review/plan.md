# Cash-flow, macroeconomic scenarios, and FX choice: revision plan

Date: 2026-10-08. Active task: write a new, self-contained survey and product proposal, preserving `docs/salespitch`. Reader: quantitatively literate bank product, treasury, model-risk and data-science teams; prerequisites: probability, calculus, linear algebra and regression. Deliver a compiled PDF, complete LaTeX source, local copies of every cited paper, and source/derivation checks. No bank data or empirical model training is part of this task.

## Argument and evidence

Currency-specific gross inflows and outflows -> joint dynamic forecasts -> macroeconomic scenarios and structural counterfactual assumptions -> currency exposure and hedging utility -> discrete choice among available offers -> incremental outreach and phased delivery. Mathematical derivations appear where the argument needs them, not in a detached technical appendix. Methods surveyed are reconstructed for the question rather than reproducing whole copyrighted papers.

The predictive layer estimates bank-observed flows. Total-wallet flows require extra observations or explicit sensitivity assumptions. GDP is an externally supplied scenario input, not automatically an identified exogenous cause. Positive GDP loadings for every client will be offered as a constrained scenario specification; heterogeneity and general-equilibrium channels prevent presenting this as an established universal fact. Thirty-six shared macroeconomic dates remain thirty-six dates even with one million customers.

## Skeptical audit before drafting

Main risks: presenting conditional predictions as interventions; confusing gross currency turnover with residual FX exposure; learning preferences from selected offers; confusing product choice with causal outreach lift; claiming the cross-section solves short macro history; exact Gaussian inference applied to zero-inflated non-Gaussian observations; counterfactual changes in bank capture mistaken for underlying demand; asserting predictive superiority without bank data. The proposed structure explicitly derives these distinctions. Preserve both gross flows, their dependence, existing hedges, choice sets, release-date macro vintages, and market FX paths. Audit passes for a document project; empirical superiority and causal identification remain future evidence requirements.

## Material defaults and assumptions

- Monthly USD reporting, foreign-currency native-unit flows, 1/3/6-month horizons: illustrative design choices; confirm units and settlement calendars before implementation.
- Hierarchical low-dimensional dynamics: hypothesis motivated by 36 dates; compare with client mean, last value, seasonal naive, peer pooled regression, and transparent state-space models, conditionally by segment.
- Gaussian transformed-flow baseline: analytic teaching and diagnostic model; zeros require a separately derived hurdle extension, whose inference is approximate.
- Positive GDP scenario response: user-requested economic restriction, not a discovered causal law. Check heterogeneous and unrestricted sensitivity models and multistep response signs.
- CARA-normal utility: exact only under stated normal-wealth conditions. Unbounded lognormal payments can make exponential expected utility diverge. The first release therefore uses an explicitly declared mean-variance preference with finite second moments, or expected utility under a separately justified bounded/default-limited wealth model. Finite Monte Carlo arithmetic does not establish existence of population expected utility.
- Logit/mixed logit: behavioral hypotheses; revealed preferences require offered alternatives, availability, price and outcome data plus treatment of price/offer endogeneity.

## Verification and stopping criteria

Every citation must have an inspected primary technical source and a correctly named local PDF in `dcos/papers/salespitch`. Use six source/metadata/snowball/claim/omission ledgers. Verify critical algebra with bounded deterministic CPU checks; these establish identities only. Compile until references resolve, inspect all rendered pages, repair confirmed clipping and unexplained notation. Stop with explicit source gaps if an indispensable source cannot be obtained, otherwise substitute a fully inspected accessible source. Human evaluation of explanatory voice remains pending; it does not prevent delivering the requested new draft.

Outputs: `docs/salespitch_v2/`; working evidence: `.localresources/bank-sales-v2-2026-10-08/`. No time-consuming model experiments, package mutation, GPU work, or external messaging.
