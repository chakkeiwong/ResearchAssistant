# M22 Omission-Frontier Source Inspection

Five predeclared primary arXiv sources were inspected across method, theory, evaluation, and limitations. The record supports scoped source descriptions only; it does not authorize final prose or universal claims.

## arxiv:1902.02934 - Mode Collapse and Regularity of Optimal Transportation Maps

Survey role: `COMPARATOR_OR_FAILURE_ANALYSIS`

Method:

- The paper links quadratic-OT map singularities to a continuous-generator mismatch and proposes computing a continuous Brenier potential with a discrete Brenier/AE-OT construction.

Theory:

- It states regularity conditions for Brenier maps and uses non-convex or disconnected targets to motivate discontinuities on singular sets.
- The step from OT-map discontinuity to a general explanation of GAN non-convergence or mode collapse is the paper's argument, not a universal theorem covering arbitrary GAN objectives and architectures.

Evaluation:

- The empirical support is a qualitative 25-mode comparison and a CelebA latent interpolation used as a hypothesis test; no broad replicated ranking is established.

Merits:

- It makes regularity and map discontinuity visible as a concrete failure mechanism rather than treating mode collapse only as an optimizer symptom.
- It distinguishes the continuous Brenier potential from its potentially discontinuous gradient map.

Concerns:

- The statement that DNNs cannot approximate the relevant maps and therefore cause GAN failure is broader than the checked regularity theorem itself.
- One unrealistic CelebA interpolation does not establish that real-data latent supports are generally non-convex or that this mechanism dominates practical mode collapse.

Unresolved uncertainties:

- The algorithm and reported speed/accuracy were not independently reproduced.
- Official code, later corrections, and publication or retraction status were not checked.

Allowed source descriptions:

- The paper proposes an OT-regularity explanation of GAN mode collapse and a discrete Brenier-potential alternative.
- Under the paper's stated density and support conditions, the reviewed text discusses singular sets and discontinuous Brenier maps for non-convex targets.

Forbidden claims:

- OT-map discontinuity is the universal or proved fundamental cause of mode collapse in all GANs.
- The method is generally more accurate, efficient, or superior to GAN alternatives.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:325`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:346`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:497`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:511`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:526`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:550`

Next action: Use as a scoped failure-analysis source, with the theorem conditions and empirical hypothesis status stated explicitly.

## arxiv:1905.10812 - Regularity as Regularization: Smooth and Strongly Convex Brenier Potentials in Optimal Transport

Survey role: `REGULARIZED_DIRECT_METHOD`

Method:

- The paper defines smooth strongly-convex nearest-Brenier potentials by minimizing the W2 discrepancy between a regularized pushforward and the requested target.
- For discrete measures it reduces estimation to alternating a convex QCQP and a discrete OT problem, with a QCQP for out-of-sample map evaluation.

Theory:

- It proves the finite-dimensional QCQP characterization and strong consistency only when the true Brenier potential lies in the chosen global regularity class.
- The paper explicitly states that the induced transport value is not a metric to the original target and that local partitions need not give a globally optimal map.

Evaluation:

- Experiments cover controlled global/local regularity, domain adaptation, and color transfer; the paper reports an accuracy-computation trade-off as the partition changes.

Merits:

- It states the modified target precisely instead of hiding regularization behind the name of exact OT.
- It provides both formal characterization and out-of-sample evaluation for the regularized potential.

Concerns:

- The computed map generally targets the nearest admissible pushforward, not the original target distribution exactly.
- Consistency fails under regularity misspecification, and the theoretical convergence rate is left outside the paper's scope.

Unresolved uncertainties:

- How to select smoothness, strong-convexity, and partition parameters for the survey's target tasks remains unestablished.
- Official code and current solver reproducibility were not checked.

Allowed source descriptions:

- The paper is a direct regularized Brenier-map method with an explicitly modified nearest-pushforward objective.
- Its consistency result is conditional on the true potential belonging to the declared regularity class.

Forbidden claims:

- SSNB always computes the exact OT map to the requested target.
- Its induced value is a Wasserstein metric between the original measures or is dimension-free in total statistical error.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/regasreg.tex:20`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/regasreg.tex:40`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/regasreg.tex:47`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/estimation.tex:19`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/estimation.tex:43`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/experiments.tex:13`

Next action: Use as a direct regularized-map comparator and name the changed target, regularity assumptions, and misspecification risk every time.

## arxiv:1906.09691 - Adversarial Computation of Optimal Transport Maps

Survey role: `DIRECT_METHOD`

Method:

- W2GAN trains a generator against a discriminator approximating the squared 2-Wasserstein objective and interprets generator updates through a functional-gradient rule.

Theory:

- Under absolute continuity, a perfect discriminator, and ideal infinite-capacity updates, the paper proves that generated distributions follow the unique W2 geodesic and recover the Monge map.
- For imperfect updates it gives one-step deviation bounds conditional on externally bounded discriminator-gradient and generator-update errors.

Evaluation:

- The experiments compare 2D maps with discrete OT and several adversarial/barycentric baselines, then report high-dimensional image and domain-adaptation results.

Merits:

- It directly connects adversarial training dynamics to an OT map rather than using Wasserstein distance only as a loss name.
- It makes its ideal assumptions and conditional deviation quantities explicit.

Concerns:

- The practical training procedure does not establish that the perfect-discriminator and ideal-update errors are small.
- The paper leaves convergence of the regularized dual potential gradient to the true potential as an open problem.

Unresolved uncertainties:

- The high-dimensional optimal-map claim was not independently reproduced or checked against official code.
- Later evidence about stability and comparisons is unavailable.

Allowed source descriptions:

- The paper is a direct adversarial OT-map method with ideal-case W2-geodesic and Monge-map results.
- Its non-ideal analysis is a conditional deviation bound, not an unconditional finite-network convergence theorem.

Forbidden claims:

- Finite W2GAN training is proved to recover the exact Monge map in general.
- W2GAN universally outperforms prior high-dimensional OT methods.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:315`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:365`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:379`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:419`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:478`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:929`

Next action: Include as a direct method, separating ideal-case propositions, conditional non-ideal bounds, and empirical map comparisons.

## arxiv:2102.02992 - Learning High Dimensional Wasserstein Geodesics

Survey role: `DIRECT_METHOD`

Method:

- The paper derives a neural minimax formulation from dynamical OT, restricts the density path to geodesic pushforwards, and adds bidirectional consistency and optional W2 preconditioning.

Theory:

- For a smooth optimal potential and strictly convex Lagrangian, the reviewed theorem places the true dynamical-OT solution at a critical point of the restricted functional and recovers the optimal value.
- The theorem does not establish that neural saddle optimization reaches that critical point or a global optimum.

Evaluation:

- Experiments use Gaussian ground truth where available, POT comparisons otherwise, and qualitative color-transfer and MNIST examples; the stopping rule compares forward and reverse estimated costs.

Merits:

- It targets the full Wasserstein geodesic and produces distance and map outputs as by-products.
- It exposes the restricted path family, stability regularizer, neural parameterization, and stopping heuristic.

Concerns:

- Critical-point inclusion is weaker than convergence or correctness of the trained neural solution.
- Bidirectional consistency and equal forward/reverse cost estimates are heuristics and do not by themselves certify OT validity.

Unresolved uncertainties:

- Optimization reliability, sensitivity to the bidirectional weight and stopping threshold, and official-code behavior were not independently checked.
- Most non-Gaussian high-dimensional results do not have exact map ground truth in the reviewed text.

Allowed source descriptions:

- The paper is a direct neural dynamical-OT and Wasserstein-geodesic method for strictly convex costs.
- Its theorem identifies the true solution as a critical point under smoothness assumptions; it is not a neural optimization convergence theorem.

Forbidden claims:

- The bidirectional stopping criterion proves convergence to the exact OT map.
- The method is validated for arbitrary high-dimensional distributions or non-strictly-convex costs.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:141`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:343`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:423`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:448`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:460`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:696`

Next action: Use as a direct dynamical/geodesic method, stating the critical-point theorem separately from practical neural convergence and experiment evidence.

## arxiv:2205.15269 - Kernel Neural Optimal Transport

Survey role: `DIRECT_METHOD`

Method:

- The paper analyzes fake saddle-point maps for weak quadratic NOT and replaces the cost with a weak characteristic-kernel cost for stochastic neural OT.

Theory:

- For compact domains, continuous characteristic kernels, and positive gamma, it proves uniqueness of the optimal plan and that every optimal saddle-point map represents the optimal conditional plan.
- The discussion explicitly notes that the theorem assumes existence of an optimal dual maximizer and leaves precise conditions open.

Evaluation:

- It compares with discrete OT in 1D, gives qualitative 2D results where exact kernel-cost maps are unknown, and reports test FID and five-seed stability comparisons on selected image tasks.

Merits:

- It directly addresses a known ambiguity in the seed NOT saddle objective instead of treating training instability only empirically.
- The characteristic-kernel theorem cleanly separates the proposed cost from the bilinear weak-quadratic special case.

Concerns:

- The theorem's optimal-dual-existence assumption is not fully characterized in the paper.
- Kernel or shared-feature selection is task dependent, image experiments are expensive, and FID results do not establish OT correctness or universal superiority.

Unresolved uncertainties:

- Official code/checkpoints and the reported multi-GPU runs were not audited or reproduced.
- Ground-truth optimal maps are unavailable for the reviewed 2D kernel-cost examples.

Allowed source descriptions:

- The paper is a direct weak-cost neural OT extension that analyzes fake saddle maps and proposes characteristic-kernel costs.
- Under its compactness, characteristic-kernel, gamma, and optimal-potential assumptions, every optimal saddle map corresponds to the unique optimal plan.

Forbidden claims:

- Kernel NOT is proved free of practical optimization failures or fake finite-training solutions.
- Its FID results prove scientific superiority, general OT correctness, or suitability across heterogeneous domains.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:411`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:520`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:585`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:642`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:721`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:760`

Next action: Include as a direct seed-method extension and failure-analysis source, preserving its optimal-potential and kernel assumptions and bounded empirical scope.
