# M22 Qualitative Scholarly Assessment

Topic: Neural Optimal Transport

Source scope: Twelve retained source-inspected papers plus grouped omission frontiers from M20-M22; fifty identifier-bearing rows and 195 identifier-free units remain unresolved, and forward citations are unavailable and non-blocking.

These are system-generated draft assessments grounded in the retained local technical text. They are meant for researcher inspection and revision. They do not authorize claims or establish prose readiness.

## arxiv:2201.12220v3

The seed paper is a direct neural optimal-transport method: it derives a maximin formulation for strong and weak costs, parameterizes a stochastic map and potential with neural networks, and evaluates deterministic and one-to-many transport. Its own analysis limits how broadly the learned saddle-point map can be called optimal.

Merits:

- It directly targets transport maps and plans, rather than using only an OT cost as a training loss.
- It proves a neural-network universal approximation result for stochastic transport maps under stated compactness and moment conditions.
- It reports toy weak-OT checks, unpaired image translation, and an explicit variance-similarity control through the weak-cost parameter gamma.

Concerns:

- The paper states that not every saddle-point minimizer T* is an optimal stochastic OT map.
- For strong costs, the learned stochastic map may become noise-independent, producing conditional collapse.
- Application results do not establish that the method is suitable for every unpaired task; task-specific transport costs remain a design requirement.

Uncertainties:

- The retained source has not been independently reproduced in this M22 assessment.
- Forward-citation evidence about later corrections, comparisons, or failures is unavailable in the bounded campaign.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2201_12220v3/unpacked/main.tex:153`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2201_12220v3/unpacked/main.tex:486`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2201_12220v3/unpacked/main.tex:504`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2201_12220v3/unpacked/main.tex:523`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2201_12220v3/unpacked/main.tex:650`

Next action: Use it as the central direct-method source, but qualify optimality claims by the saddle-point and strong-cost limitations and anchor each claim to the relevant theorem, algorithm, experiment, or limitation passage.

## arxiv:1902.07197

This is a direct 2-Wasserstein approximation and map-learning paper based on restricting convex potentials, especially with input-convex neural networks. It provides substantial theory and a small controlled comparison with regularization-based OT, but it computes a restricted approximation whose meaning depends on the chosen function class.

Merits:

- It connects Brenier structure to a computational restriction over convex potentials and map gradients.
- It analyzes discriminative power, moment matching, statistical generalization, and restricted duality rather than presenting only an empirical algorithm.
- Its Gaussian-mixture experiment compares map error and runtime against a regularization-based approach with similar networks and the same epoch count.

Concerns:

- The computed object is a restricted approximation to W2 and the OT map; it is not automatically the exact unrestricted OT problem.
- Hand-picking the function class can reduce expressiveness and determines which moments or distributions the approximation distinguishes.
- The practical nested optimization uses an approximate inner loop whose structured gradient bias may harm convergence in harder cases.

Uncertainties:

- The retained experiment is narrow and does not establish broad large-scale superiority.
- The target-specific adequacy of the chosen ICNN/restriction class is not established for the current survey's applications.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1902_07197/OT-arxiv-main.tex:98`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1902_07197/OT-arxiv-main.tex:119`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1902_07197/OT-arxiv-main.tex:123`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1902_07197/OT-arxiv-main.tex:486`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1902_07197/OT-arxiv-main.tex:492`

Next action: Use it as a direct theoretical comparator for convex-potential OT, stating explicitly that its guarantees and approximation quality are relative to the selected restriction class.

## arxiv:2003.06635

This is a direct large-scale OT framework that models a stochastic Kantorovich map with a neural network, enforces the target marginal adversarially, and uses one- or two-sided cycle consistency to encourage Monge maps or bijections. It combines propositions with broad application experiments, but the implemented objective is a penalized adversarial approximation rather than an exact constrained solve.

Merits:

- It distinguishes Kantorovich, Monge, and bijective transport and exposes different neural solvers for those targets.
- It gives a proposition connecting one-sided cycle consistency to determinism under stated exact conditions.
- It reports synthetic, domain-adaptation, image-translation, and color-transfer comparisons against several baselines.

Concerns:

- The marginal constraint is enforced through GAN training and gradient penalties, so finite optimization does not guarantee the exact pushforward constraint.
- Cycle consistency changes the objective and may impose unnecessary structure; the paper itself reports slight degradation when it is not needed.
- Claims of superior performance are based on the paper's selected tasks and metrics and are not a universal method ranking.

Uncertainties:

- The exact robustness to adversarial-training instability and hyperparameter choice was not independently checked here.
- The proposition's zero-loss and exact-pushforward assumptions may not hold in trained finite networks.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06635/large_scale_ot_via_cycle_consistency_with_adversarial_training.tex:70`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06635/large_scale_ot_via_cycle_consistency_with_adversarial_training.tex:123`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06635/large_scale_ot_via_cycle_consistency_with_adversarial_training.tex:225`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06635/large_scale_ot_via_cycle_consistency_with_adversarial_training.tex:319`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06635/large_scale_ot_via_cycle_consistency_with_adversarial_training.tex:487`

Next action: Use it as a direct neural OT comparator, separating exact propositions from the penalized finite-training implementation and keeping task-specific performance claims bounded to reported experiments.

## arxiv:1709.08894

This paper is an indirect but technically relevant comparator: it studies how to enforce the Lipschitz constraint in Wasserstein GAN critics and proposes a one-sided penalty. It informs regularization choices around OT-based adversarial training, but it does not compute an OT map or plan.

Merits:

- It identifies a mismatch between coupled-pair theory and the independent marginal sampling used by WGAN-GP training.
- It gives a concrete one-sided Lipschitz penalty and a proposition comparing optimal regularized losses as lambda changes.
- It reports repeated toy and image experiments and explicitly studies hyperparameter sensitivity.

Concerns:

- Its target is stable WGAN critic training, not recovery of an optimal transport map or plan.
- The empirical superiority statements depend on the tested datasets, architectures, and penalty weights.
- The proposal remains a soft constraint whose finite-network enforcement is approximate.

Uncertainties:

- How the penalty interacts with the seed paper's different maximin transport-map objective was not tested here.
- Later comparative evidence is unavailable in the bounded source set.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1709_08894/main.tex:99`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1709_08894/main.tex:105`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1709_08894/main.tex:650`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1709_08894/main.tex:728`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1709_08894/main.tex:751`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1709_08894/main.tex:1013`

Next action: Cite it for Lipschitz-regularization context or as an indirect training comparator, not as evidence that a neural method recovers OT maps or plans.

## arxiv:1805.07277

XOGAN is an indirect one-to-many unpaired image-translation comparator. It introduces an auxiliary latent variable with adversarial and cycle-consistency losses to generate diverse outputs, but it is not formulated as an optimal-transport method.

Merits:

- It addresses a real one-to-many translation failure mode that deterministic cycle-consistent models do not represent.
- It provides an explicit generator/loss construction and experiments on edges-to-objects and CelebA.
- Its conclusion openly notes that learned variation is mainly color-related and that the Gaussian prior may be too simple.

Concerns:

- The evidence is largely qualitative against limited baseline variants and does not establish OT optimality.
- The latent code's learned semantics are constrained and may not represent complex structural variation.
- Cycle consistency and adversarial losses define a different objective from the seed paper's strong/weak transport costs.

Uncertainties:

- No independent reproduction or statistical uncertainty analysis was inspected.
- The extent to which XOGAN is a fair comparator for weak-OT diversity is task dependent.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1805_07277/paper.tex:97`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1805_07277/paper.tex:238`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1805_07277/paper.tex:343`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1805_07277/paper.tex:538`

Next action: Use it as a one-to-many translation baseline and motivation for conditional diversity, while stating that it is not OT evidence and that its demonstrated variations are limited.

## arxiv:2003.06788

GMM-UNIT is an indirect multi-domain, multi-modal image-translation comparator. It models domain attributes with a Gaussian mixture and reports quality/diversity and few/zero-shot experiments. It is relevant to the application context but does not solve or analyze an optimal-transport problem.

Merits:

- It unifies multi-domain and multi-modal translation in one content-attribute architecture.
- It reports FID, LPIPS, parameter counts, ablations, and multiple datasets rather than relying only on sample images.
- Its continuous attribute representation gives an explicit mechanism for interpolation and few/zero-shot generation.

Concerns:

- The claim that it generalizes prior state-of-the-art models is architectural and does not establish general scientific superiority.
- FID and LPIPS are application diagnostics, not proof that learned mappings are optimal transports or scientifically correct.
- Some comparisons are against reimplemented or modified baselines, and reported rankings are bounded to the chosen datasets and metrics.

Uncertainties:

- The scientific validity of extrapolation to unseen domains beyond the reported examples was not independently checked.
- No direct relation between the GMM latent geometry and a declared transport cost is established in the inspected text.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06788/arxiv_version.tex:93`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06788/arxiv_version.tex:156`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06788/arxiv_version.tex:189`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06788/arxiv_version.tex:308`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06788/arxiv_version.tex:374`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/2003_06788/arxiv_version.tex:625`

Next action: Use it for application-side comparison of diversity and multi-domain translation, not as support for OT map recovery or optimality claims.

## arxiv:1506.03365

LSUN is an evaluation-dataset source, not a neural OT method. It documents a human-in-the-loop labeling pipeline, dataset scale, label-precision checks, and classifier experiments. Its value to this survey is to describe the provenance and limitations of a dataset used by generative or translation experiments.

Merits:

- It explains the iterative labeling pipeline and reports explicit label-precision checks.
- It records dataset scale and the distinction between scene and object categories.
- It discusses dataset bias and noisy labels rather than treating the benchmark as ground truth without qualification.

Concerns:

- It provides no evidence about optimal transport theory, maps, plans, or neural OT correctness.
- Reported classifier gains are specific to the dataset construction and tested networks.
- Label precision around 90 percent and acknowledged dataset bias matter when downstream image metrics use LSUN data.

Uncertainties:

- The current status, later revisions, and downstream benchmark practices are not established by the retained 2015 source alone.
- The exact LSUN subset used by each retained method would need experiment-specific checking.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1506_03365/abstract.tex:1`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1506_03365/introduction.tex:75`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1506_03365/introduction.tex:86`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1506_03365/evaluation.tex:25`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1506_03365/evaluation.tex:60`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/source_reading/1506_03365/evaluation.tex:138`

Next action: Classify it as dataset/evaluation context and cite it only for documented LSUN construction, scale, precision, or bias, not for method claims.

## arxiv:1902.02934

This paper is primarily OT-based failure analysis for generative models. It argues that singularities of Brenier maps to non-convex or disconnected targets conflict with continuous generator classes, then proposes computing a continuous Brenier potential in a discrete AE-OT construction. The checked theorem conditions are narrower than the paper's broad explanation of practical GAN failure.

Merits:

- It makes map regularity and singular sets a concrete candidate mechanism for mode collapse and unrealistic interpolation.
- It separates the continuity of the Brenier potential from discontinuity of its gradient map.

Concerns:

- The checked OT regularity results do not prove that this mechanism is the universal or dominant cause of non-convergence and mode collapse across GAN objectives and architectures.
- The 25-mode and CelebA evidence is qualitative and does not establish general accuracy, speed, or superiority.

Uncertainties:

- The discrete AE-OT implementation and reported training-speed claim were not independently reproduced.
- Official code, publication safety, and later corrections or comparisons were not checked.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:325`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:346`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:497`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:511`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1902_02934/source_members/main.tex:550`

Next action: Use it as scoped failure-analysis context, stating the regularity assumptions and keeping the GAN-causation and empirical claims explicitly qualified.

## arxiv:1905.10812

This is a direct regularized Brenier-map method. It searches for a smooth strongly-convex potential whose pushforward is nearest to the requested target, reduces the discrete problem to alternating QCQP and OT steps, and supports out-of-sample map evaluation. Its target is deliberately modified and must not be described as exact OT to the original target without qualification.

Merits:

- It defines the changed nearest-pushforward target explicitly and gives a finite-dimensional QCQP characterization.
- It includes a conditional consistency result, controlled experiments, and out-of-sample evaluation.

Concerns:

- The induced map generally transports to the nearest admissible pushforward, not exactly to the requested target distribution.
- The induced value is not a metric to the original target; consistency fails when the true potential violates the selected regularity bound.

Uncertainties:

- Target-specific selection of smoothness, strong-convexity, and partition parameters remains unresolved.
- The theoretical convergence rate, official implementation, and current solver reproducibility were not checked.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/regasreg.tex:20`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/regasreg.tex:40`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/regasreg.tex:47`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/estimation.tex:43`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1905_10812/source_members/sections/experiments.tex:13`

Next action: Use it as a direct regularized-map comparator, always naming the modified target, regularity assumptions, and misspecification risk.

## arxiv:1906.09691

W2GAN is a direct adversarial OT-map method. Under absolute continuity, a perfect discriminator, and ideal infinite-capacity updates, the paper proves that generator distributions follow the unique W2 geodesic and recover the Monge map. Its practical claims remain conditional because finite training does not establish that the discriminator and update errors satisfy the required bounds.

Merits:

- It directly connects generator dynamics to W2 geodesics and Monge maps rather than using Wasserstein terminology only as a loss label.
- It makes the ideal assumptions and conditional non-ideal deviation quantities explicit.

Concerns:

- The finite neural algorithm is not proved to satisfy the perfect-discriminator or ideal-update assumptions.
- The paper leaves convergence of the regularized dual-potential gradient to the exact Kantorovich potential as an open problem.

Uncertainties:

- The high-dimensional map results and stability were not independently reproduced or checked against official code.
- Later comparative or corrective evidence is unavailable in the active source boundary.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:315`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:365`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:379`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:419`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/1906_09691/source_members/main.tex:929`

Next action: Include it as a direct method while separating ideal-case propositions, conditional deviation bounds, and empirical comparisons.

## arxiv:2102.02992

This is a direct neural dynamical-OT method for learning Wasserstein geodesics. It derives a minimax formulation, restricts paths to geodesic pushforwards, and adds bidirectional consistency and optional W2 preconditioning. The checked theorem identifies the true smooth solution as a critical point of the restricted functional; it does not prove that neural saddle optimization reaches it.

Merits:

- It targets the full geodesic and provides distance and map outputs as by-products.
- It exposes the path restriction, bidirectional regularizer, neural parameterization, and stopping rule rather than hiding them as implementation details.

Concerns:

- Critical-point inclusion is weaker than global convergence or correctness of the trained neural solution.
- Agreement of forward and reverse estimated costs is a stopping heuristic, not an OT validity certificate.

Uncertainties:

- Sensitivity to the bidirectional weight, threshold, initialization, and neural capacity was not independently checked.
- Most non-Gaussian high-dimensional examples lack exact map ground truth in the inspected text.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:141`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:343`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:423`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:448`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:460`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2102_02992/source_members/a_paper.tex:696`

Next action: Use it as a direct geodesic method, stating its smooth critical-point theorem separately from practical optimization and experiment evidence.

## arxiv:2205.15269

Kernel Neural Optimal Transport is a direct extension and critique of weak-cost NOT. It analyzes fake saddle-point maps for the weak quadratic cost and proves that, under compactness, characteristic-kernel, positive-gamma, and optimal-potential assumptions, every optimal saddle map represents the unique optimal plan. Its finite-training and task-transfer behavior remains empirical.

Merits:

- It addresses ambiguity in the seed NOT objective with a formal failure analysis and a modified characteristic-kernel cost.
- It combines theory, discrete-OT toy checks, heldout image evaluation, and five-seed stability experiments.

Concerns:

- The main theorem assumes existence of an optimal dual maximizer, while precise existence conditions are left open.
- Kernel or shared-feature selection is task dependent; FID and qualitative examples do not prove OT correctness or universal superiority.

Uncertainties:

- Official code, checkpoints, and reported multi-GPU runs were not audited or reproduced.
- Ground-truth optimal maps are unavailable for the reviewed 2D kernel-cost examples.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:411`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:520`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:585`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:642`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:721`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/candidates/2205_15269/source_members/main.tex:760`

Next action: Include it as a direct seed-method extension and failure-analysis source, preserving its optimal-potential and kernel assumptions.

## omission_frontier:unused_identifier_bearing

All 55 deferred identifier-bearing references now have replayable title-context groups, and five predeclared high-risk papers have primary technical-source inspections. The remaining 50 are still provisional omission risks, not 50 equally important missing papers and not evidence of 50 independent survey failures.

Merits:

- Every candidate remains machine-accounted with a corrected title, identifier, bibliography key, provisional group, and explicit nonclaim boundary.
- The five inspected papers now have distinct direct-method, regularized-method, and failure-analysis roles grounded in technical text.

Concerns:

- Direct methods or foundational components may remain among the 50 title-context-only rows.
- The five-paper selection is a bounded scientific triage, not a completeness proof or importance ranking.

Uncertainties:

- Technical relevance has not been inspected for the remaining 50 rows.
- Forward influence, official-code behavior, and publication or retraction status remain unavailable or unchecked.

Evidence:

- `docs/validation/literature_survey_north_star_m22_omission_frontier_triage_2026-07-19/provisional_classification.json:1`
- `docs/validation/literature_survey_north_star_m22_omission_frontier_triage_2026-07-19/inspection_queue.json:1`
- `docs/validation/literature_survey_north_star_m22_omission_frontier_triage_2026-07-19/source_inspection.json:1`
- `docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19/terminal_result.json:1`

Next action: Use the grouped 50-paper residual frontier to choose the next smallest source-inspection batch only if a concrete survey claim or reviewer risk requires it.

## omission_frontier:identifier_free

The 195 identifier-free bibliography units are an unresolved parsing and identity frontier. Their aggregate count is important for accounting, but it cannot support paper-level relevance or omission conclusions.

Merits:

- The units are retained as an explicit aggregate instead of disappearing from coverage accounting.
- They may contain references recoverable later from bibliography text without any credentialed provider.

Concerns:

- Unknown identities can hide duplicates, foundational works, or direct competitors.
- The aggregate cannot be honestly closed as irrelevant without at least bounded identity recovery or sampling.

Uncertainties:

- The number of unique works represented by the 195 units is unknown.
- Their distribution across direct, background, dataset, and peripheral roles is unknown.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/human_review_packet.json:identifier_free_units:195`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/packet/omission_risk.json`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/retained_evidence/reconciliation_manifest.json`

Next action: Run a credential-free local bibliography normalization and deduplication pass, then inspect a stratified sample before deciding whether full recovery is scientifically necessary.

## omission_frontier:source_parse_gap:1412.6980

The retained source for arXiv 1412.6980 is an includepdf wrapper, so the technical content was not inspected. The paper cannot support or refute a survey claim from the current artifact.

Merits:

- The source-format failure is recorded explicitly rather than being mistaken for an irrelevant or empty paper.

Concerns:

- Metadata or citation context could be incorrectly promoted into a technical description if the parse gap is ignored.
- Its role in the seed paper's experimental details remains unresolved.

Uncertainties:

- The underlying PDF text and technical sections were not available under the no-PDF-fallback campaign scope.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/human_review_packet/human_review_packet.json:source_parse_gap:1412.6980`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/source_intake/source_intake_outcomes.json`

Next action: Keep it as a source gap unless a later, separately authorized source route provides inspectable primary text; do not infer its contents from title or metadata.

## omission_frontier:forward_citations

Forward-citation coverage is unavailable and permanently out of scope for this credential-free campaign. This limits awareness of later corrections, replications, and competitors but does not invalidate the completed backward-reference and source-inspection work.

Merits:

- The limitation is recorded honestly and is non-blocking under the revised M20/G3 contract.
- Backward-reference extraction and primary-source checking still provide meaningful scientific evidence.

Concerns:

- Recent follow-up work, negative results, and corrections may be absent from the current survey frontier.
- The survey must not describe unavailable forward coverage as zero citations or complete literature coverage.

Uncertainties:

- The magnitude and scientific importance of missing later work are unknown.

Evidence:

- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/packet/omission_risk.json:forward_coverage`
- `docs/validation/literature_survey_north_star_m22b0_production_reconciliation_2026-07-18/packet/build_manifest.json:forward_coverage`

Next action: Carry this as a visible non-blocking limitation in all survey outputs and revisit only if a future credential-free forward source becomes genuinely available.
