#!/usr/bin/env python3
"""Build the five-paper M22 omission-frontier source inspection record."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from research_assistant.survey.source_inspection import (
    ROW_SCHEMA_VERSION,
    SCHEMA_VERSION,
    validate_source_inspection_bundle,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = "docs/validation/literature_survey_north_star_m22_omission_source_campaign_2026-07-19"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / (
    "docs/validation/literature_survey_north_star_m22_omission_frontier_triage_2026-07-19"
)
CAMPAIGN_ROOT = REPOSITORY_ROOT / CAMPAIGN
TRIAGE_ROOT = REPOSITORY_ROOT / (
    "docs/validation/literature_survey_north_star_m22_omission_frontier_triage_2026-07-19"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(candidate: str, member: str, line: int) -> str:
    return f"{CAMPAIGN}/candidates/{candidate}/source_members/{member}:{line}"


def _row(**values: object) -> dict[str, object]:
    return {
        "schema_version": ROW_SCHEMA_VERSION,
        "source_status": "LOCAL_ARXIV_TECHNICAL_SOURCE_AVAILABLE",
        "inspection_status": "METHOD_THEORY_EVALUATION_LIMITATIONS_INSPECTED",
        "source_support_status": "PRIMARY_TECHNICAL_TEXT_INSPECTED",
        "official_code_status": "NOT_CHECKED",
        "publication_retraction_status": "NOT_CHECKED",
        "forward_citation_status": "UNAVAILABLE_OUT_OF_SCOPE_NONBLOCKING",
        "claim_support_allowed": False,
        "ready_for_prose": False,
        **values,
    }


def build_bundle() -> dict[str, object]:
    rows = [
        _row(
            candidate_id="arxiv:1902.02934",
            title="Mode Collapse and Regularity of Optimal Transportation Maps",
            source_role="COMPARATOR_OR_FAILURE_ANALYSIS",
            method_findings=[
                "The paper links quadratic-OT map singularities to a continuous-generator mismatch and proposes computing a continuous Brenier potential with a discrete Brenier/AE-OT construction.",
            ],
            theory_findings=[
                "It states regularity conditions for Brenier maps and uses non-convex or disconnected targets to motivate discontinuities on singular sets.",
                "The step from OT-map discontinuity to a general explanation of GAN non-convergence or mode collapse is the paper's argument, not a universal theorem covering arbitrary GAN objectives and architectures.",
            ],
            evaluation_findings=[
                "The empirical support is a qualitative 25-mode comparison and a CelebA latent interpolation used as a hypothesis test; no broad replicated ranking is established.",
            ],
            merits=[
                "It makes regularity and map discontinuity visible as a concrete failure mechanism rather than treating mode collapse only as an optimizer symptom.",
                "It distinguishes the continuous Brenier potential from its potentially discontinuous gradient map.",
            ],
            concerns=[
                "The statement that DNNs cannot approximate the relevant maps and therefore cause GAN failure is broader than the checked regularity theorem itself.",
                "One unrealistic CelebA interpolation does not establish that real-data latent supports are generally non-convex or that this mechanism dominates practical mode collapse.",
            ],
            unresolved_uncertainties=[
                "The algorithm and reported speed/accuracy were not independently reproduced.",
                "Official code, later corrections, and publication or retraction status were not checked.",
            ],
            allowed_source_descriptions=[
                "The paper proposes an OT-regularity explanation of GAN mode collapse and a discrete Brenier-potential alternative.",
                "Under the paper's stated density and support conditions, the reviewed text discusses singular sets and discontinuous Brenier maps for non-convex targets.",
            ],
            forbidden_claims=[
                "OT-map discontinuity is the universal or proved fundamental cause of mode collapse in all GANs.",
                "The method is generally more accurate, efficient, or superior to GAN alternatives.",
            ],
            evidence_refs=[
                _ref("1902_02934", "main.tex", 325),
                _ref("1902_02934", "main.tex", 346),
                _ref("1902_02934", "main.tex", 497),
                _ref("1902_02934", "main.tex", 511),
                _ref("1902_02934", "main.tex", 526),
                _ref("1902_02934", "main.tex", 550),
            ],
            next_action="Use as a scoped failure-analysis source, with the theorem conditions and empirical hypothesis status stated explicitly.",
        ),
        _row(
            candidate_id="arxiv:1905.10812",
            title="Regularity as Regularization: Smooth and Strongly Convex Brenier Potentials in Optimal Transport",
            source_role="REGULARIZED_DIRECT_METHOD",
            method_findings=[
                "The paper defines smooth strongly-convex nearest-Brenier potentials by minimizing the W2 discrepancy between a regularized pushforward and the requested target.",
                "For discrete measures it reduces estimation to alternating a convex QCQP and a discrete OT problem, with a QCQP for out-of-sample map evaluation.",
            ],
            theory_findings=[
                "It proves the finite-dimensional QCQP characterization and strong consistency only when the true Brenier potential lies in the chosen global regularity class.",
                "The paper explicitly states that the induced transport value is not a metric to the original target and that local partitions need not give a globally optimal map.",
            ],
            evaluation_findings=[
                "Experiments cover controlled global/local regularity, domain adaptation, and color transfer; the paper reports an accuracy-computation trade-off as the partition changes.",
            ],
            merits=[
                "It states the modified target precisely instead of hiding regularization behind the name of exact OT.",
                "It provides both formal characterization and out-of-sample evaluation for the regularized potential.",
            ],
            concerns=[
                "The computed map generally targets the nearest admissible pushforward, not the original target distribution exactly.",
                "Consistency fails under regularity misspecification, and the theoretical convergence rate is left outside the paper's scope.",
            ],
            unresolved_uncertainties=[
                "How to select smoothness, strong-convexity, and partition parameters for the survey's target tasks remains unestablished.",
                "Official code and current solver reproducibility were not checked.",
            ],
            allowed_source_descriptions=[
                "The paper is a direct regularized Brenier-map method with an explicitly modified nearest-pushforward objective.",
                "Its consistency result is conditional on the true potential belonging to the declared regularity class.",
            ],
            forbidden_claims=[
                "SSNB always computes the exact OT map to the requested target.",
                "Its induced value is a Wasserstein metric between the original measures or is dimension-free in total statistical error.",
            ],
            evidence_refs=[
                _ref("1905_10812", "sections/regasreg.tex", 20),
                _ref("1905_10812", "sections/regasreg.tex", 40),
                _ref("1905_10812", "sections/regasreg.tex", 47),
                _ref("1905_10812", "sections/estimation.tex", 19),
                _ref("1905_10812", "sections/estimation.tex", 43),
                _ref("1905_10812", "sections/experiments.tex", 13),
            ],
            next_action="Use as a direct regularized-map comparator and name the changed target, regularity assumptions, and misspecification risk every time.",
        ),
        _row(
            candidate_id="arxiv:1906.09691",
            title="Adversarial Computation of Optimal Transport Maps",
            source_role="DIRECT_METHOD",
            method_findings=[
                "W2GAN trains a generator against a discriminator approximating the squared 2-Wasserstein objective and interprets generator updates through a functional-gradient rule.",
            ],
            theory_findings=[
                "Under absolute continuity, a perfect discriminator, and ideal infinite-capacity updates, the paper proves that generated distributions follow the unique W2 geodesic and recover the Monge map.",
                "For imperfect updates it gives one-step deviation bounds conditional on externally bounded discriminator-gradient and generator-update errors.",
            ],
            evaluation_findings=[
                "The experiments compare 2D maps with discrete OT and several adversarial/barycentric baselines, then report high-dimensional image and domain-adaptation results.",
            ],
            merits=[
                "It directly connects adversarial training dynamics to an OT map rather than using Wasserstein distance only as a loss name.",
                "It makes its ideal assumptions and conditional deviation quantities explicit.",
            ],
            concerns=[
                "The practical training procedure does not establish that the perfect-discriminator and ideal-update errors are small.",
                "The paper leaves convergence of the regularized dual potential gradient to the true potential as an open problem.",
            ],
            unresolved_uncertainties=[
                "The high-dimensional optimal-map claim was not independently reproduced or checked against official code.",
                "Later evidence about stability and comparisons is unavailable.",
            ],
            allowed_source_descriptions=[
                "The paper is a direct adversarial OT-map method with ideal-case W2-geodesic and Monge-map results.",
                "Its non-ideal analysis is a conditional deviation bound, not an unconditional finite-network convergence theorem.",
            ],
            forbidden_claims=[
                "Finite W2GAN training is proved to recover the exact Monge map in general.",
                "W2GAN universally outperforms prior high-dimensional OT methods.",
            ],
            evidence_refs=[
                _ref("1906_09691", "main.tex", 315),
                _ref("1906_09691", "main.tex", 365),
                _ref("1906_09691", "main.tex", 379),
                _ref("1906_09691", "main.tex", 419),
                _ref("1906_09691", "main.tex", 478),
                _ref("1906_09691", "main.tex", 929),
            ],
            next_action="Include as a direct method, separating ideal-case propositions, conditional non-ideal bounds, and empirical map comparisons.",
        ),
        _row(
            candidate_id="arxiv:2102.02992",
            title="Learning High Dimensional Wasserstein Geodesics",
            source_role="DIRECT_METHOD",
            method_findings=[
                "The paper derives a neural minimax formulation from dynamical OT, restricts the density path to geodesic pushforwards, and adds bidirectional consistency and optional W2 preconditioning.",
            ],
            theory_findings=[
                "For a smooth optimal potential and strictly convex Lagrangian, the reviewed theorem places the true dynamical-OT solution at a critical point of the restricted functional and recovers the optimal value.",
                "The theorem does not establish that neural saddle optimization reaches that critical point or a global optimum.",
            ],
            evaluation_findings=[
                "Experiments use Gaussian ground truth where available, POT comparisons otherwise, and qualitative color-transfer and MNIST examples; the stopping rule compares forward and reverse estimated costs.",
            ],
            merits=[
                "It targets the full Wasserstein geodesic and produces distance and map outputs as by-products.",
                "It exposes the restricted path family, stability regularizer, neural parameterization, and stopping heuristic.",
            ],
            concerns=[
                "Critical-point inclusion is weaker than convergence or correctness of the trained neural solution.",
                "Bidirectional consistency and equal forward/reverse cost estimates are heuristics and do not by themselves certify OT validity.",
            ],
            unresolved_uncertainties=[
                "Optimization reliability, sensitivity to the bidirectional weight and stopping threshold, and official-code behavior were not independently checked.",
                "Most non-Gaussian high-dimensional results do not have exact map ground truth in the reviewed text.",
            ],
            allowed_source_descriptions=[
                "The paper is a direct neural dynamical-OT and Wasserstein-geodesic method for strictly convex costs.",
                "Its theorem identifies the true solution as a critical point under smoothness assumptions; it is not a neural optimization convergence theorem.",
            ],
            forbidden_claims=[
                "The bidirectional stopping criterion proves convergence to the exact OT map.",
                "The method is validated for arbitrary high-dimensional distributions or non-strictly-convex costs.",
            ],
            evidence_refs=[
                _ref("2102_02992", "a_paper.tex", 141),
                _ref("2102_02992", "a_paper.tex", 343),
                _ref("2102_02992", "a_paper.tex", 423),
                _ref("2102_02992", "a_paper.tex", 448),
                _ref("2102_02992", "a_paper.tex", 460),
                _ref("2102_02992", "a_paper.tex", 696),
            ],
            next_action="Use as a direct dynamical/geodesic method, stating the critical-point theorem separately from practical neural convergence and experiment evidence.",
        ),
        _row(
            candidate_id="arxiv:2205.15269",
            title="Kernel Neural Optimal Transport",
            source_role="DIRECT_METHOD",
            method_findings=[
                "The paper analyzes fake saddle-point maps for weak quadratic NOT and replaces the cost with a weak characteristic-kernel cost for stochastic neural OT.",
            ],
            theory_findings=[
                "For compact domains, continuous characteristic kernels, and positive gamma, it proves uniqueness of the optimal plan and that every optimal saddle-point map represents the optimal conditional plan.",
                "The discussion explicitly notes that the theorem assumes existence of an optimal dual maximizer and leaves precise conditions open.",
            ],
            evaluation_findings=[
                "It compares with discrete OT in 1D, gives qualitative 2D results where exact kernel-cost maps are unknown, and reports test FID and five-seed stability comparisons on selected image tasks.",
            ],
            merits=[
                "It directly addresses a known ambiguity in the seed NOT saddle objective instead of treating training instability only empirically.",
                "The characteristic-kernel theorem cleanly separates the proposed cost from the bilinear weak-quadratic special case.",
            ],
            concerns=[
                "The theorem's optimal-dual-existence assumption is not fully characterized in the paper.",
                "Kernel or shared-feature selection is task dependent, image experiments are expensive, and FID results do not establish OT correctness or universal superiority.",
            ],
            unresolved_uncertainties=[
                "Official code/checkpoints and the reported multi-GPU runs were not audited or reproduced.",
                "Ground-truth optimal maps are unavailable for the reviewed 2D kernel-cost examples.",
            ],
            allowed_source_descriptions=[
                "The paper is a direct weak-cost neural OT extension that analyzes fake saddle maps and proposes characteristic-kernel costs.",
                "Under its compactness, characteristic-kernel, gamma, and optimal-potential assumptions, every optimal saddle map corresponds to the unique optimal plan.",
            ],
            forbidden_claims=[
                "Kernel NOT is proved free of practical optimization failures or fake finite-training solutions.",
                "Its FID results prove scientific superiority, general OT correctness, or suitability across heterogeneous domains.",
            ],
            evidence_refs=[
                _ref("2205_15269", "main.tex", 411),
                _ref("2205_15269", "main.tex", 520),
                _ref("2205_15269", "main.tex", 585),
                _ref("2205_15269", "main.tex", 642),
                _ref("2205_15269", "main.tex", 721),
                _ref("2205_15269", "main.tex", 760),
            ],
            next_action="Include as a direct seed-method extension and failure-analysis source, preserving its optimal-potential and kernel assumptions and bounded empirical scope.",
        ),
    ]
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "status": "five_primary_sources_inspected",
        "paper_count": len(rows),
        "rows": rows,
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "what_is_not_concluded": [
            "publication or retraction safety", "official-code faithfulness",
            "independent reproduction", "forward-citation coverage",
            "method ranking", "literature completeness", "prose readiness",
        ],
    }
    validate_source_inspection_bundle(bundle, repository_root=REPOSITORY_ROOT)
    return bundle


def _markdown(bundle: dict[str, object]) -> str:
    lines = [
        "# M22 Omission-Frontier Source Inspection",
        "",
        "Five predeclared primary arXiv sources were inspected across method, theory, evaluation, and limitations. The record supports scoped source descriptions only; it does not authorize final prose or universal claims.",
        "",
    ]
    for row in bundle["rows"]:  # type: ignore[index]
        lines.extend([
            f"## {row['candidate_id']} - {row['title']}",
            "",
            f"Survey role: `{row['source_role']}`",
            "",
            "Method:", "", *[f"- {item}" for item in row["method_findings"]], "",
            "Theory:", "", *[f"- {item}" for item in row["theory_findings"]], "",
            "Evaluation:", "", *[f"- {item}" for item in row["evaluation_findings"]], "",
            "Merits:", "", *[f"- {item}" for item in row["merits"]], "",
            "Concerns:", "", *[f"- {item}" for item in row["concerns"]], "",
            "Unresolved uncertainties:", "", *[f"- {item}" for item in row["unresolved_uncertainties"]], "",
            "Allowed source descriptions:", "", *[f"- {item}" for item in row["allowed_source_descriptions"]], "",
            "Forbidden claims:", "", *[f"- {item}" for item in row["forbidden_claims"]], "",
            "Evidence:", "", *[f"- `{item}`" for item in row["evidence_refs"]], "",
            f"Next action: {row['next_action']}", "",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    bundle = build_bundle()
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "source_inspection.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (args.output_root / "SOURCE_INSPECTION.md").write_text(
        _markdown(bundle), encoding="utf-8"
    )
    inspection_path = args.output_root / "source_inspection.json"
    route = json.loads((CAMPAIGN_ROOT / "route_ledger.json").read_text())
    manifest = {
        "schema_version": "ra-survey-source-inspection-build-manifest-v1",
        "status": "passed",
        "inspection_sha256": _sha(inspection_path),
        "inspection_queue_sha256": _sha(TRIAGE_ROOT / "inspection_queue.json"),
        "provisional_classification_sha256": _sha(
            TRIAGE_ROOT / "provisional_classification.json"
        ),
        "campaign_terminal_result_sha256": _sha(CAMPAIGN_ROOT / "terminal_result.json"),
        "campaign_route_ledger_sha256": _sha(CAMPAIGN_ROOT / "route_ledger.json"),
        "source_packages": [{
            "candidate_id": f"arxiv:{row['arxiv_id']}",
            "size_bytes": row["source_bytes"],
            "sha256": row["source_sha256"],
        } for row in route["rows"]],
        "claim_support_allowed": False,
        "ready_for_prose": False,
    }
    (args.output_root / "source_inspection_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": bundle["status"],
        "paper_count": bundle["paper_count"],
        "claim_support_allowed": False,
        "ready_for_prose": False,
        "inspection_sha256": manifest["inspection_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
