from __future__ import annotations

from copy import deepcopy
from typing import Any

from research_assistant.schemas.artifact import SCHEMA_VERSION

REQUIRED_TEMPLATE_FIELDS = {
    "template_id",
    "domain",
    "concepts",
    "claims",
    "checklist",
    "concept_taxonomy",
    "claim_taxonomy",
    "assumption_classes",
    "notation_registry",
    "theorem_roles",
    "equation_roles",
    "method_families",
    "audit_rubric",
}

DOMAIN_TEMPLATES: dict[str, dict[str, Any]] = {
    "hmc_mcmc": {
        "template_id": "hmc_mcmc",
        "schema_version": SCHEMA_VERSION,
        "domain": "HMC/MCMC",
        "concepts": ["target density", "proposal kernel", "Hamiltonian flow", "acceptance correction"],
        "claims": ["invariance", "ergodicity", "bias source", "computational scaling"],
        "checklist": ["state exactness assumptions", "identify discretization error", "record diagnostics required"],
    },
    "smc_particle_filtering": {
        "template_id": "smc_particle_filtering",
        "schema_version": SCHEMA_VERSION,
        "domain": "SMC/particle filtering",
        "concepts": ["particles", "weights", "resampling", "proposal distribution"],
        "claims": ["unbiased likelihood estimate", "filter stability", "path degeneracy control"],
        "checklist": ["record resampling schedule", "check effective sample size", "state model assumptions"],
    },
    "variational_inference": {
        "template_id": "variational_inference",
        "schema_version": SCHEMA_VERSION,
        "domain": "Variational inference",
        "concepts": ["variational family", "objective", "divergence", "amortization"],
        "claims": ["bound validity", "gradient estimator", "posterior approximation quality"],
        "checklist": ["state objective direction", "check estimator bias", "record calibration experiment"],
    },
    "macro_finance_structural": {
        "template_id": "macro_finance_structural",
        "schema_version": SCHEMA_VERSION,
        "domain": "Macro-finance structural models",
        "concepts": ["state variables", "equilibrium conditions", "pricing kernel", "identification"],
        "claims": ["structural interpretation", "policy counterfactual", "moment fit"],
        "checklist": ["state identifying assumptions", "record calibration targets", "separate model from estimate"],
    },
    "state_space_econometrics": {
        "template_id": "state_space_econometrics",
        "schema_version": SCHEMA_VERSION,
        "domain": "State-space/econometric estimators",
        "concepts": ["latent state", "transition", "measurement equation", "likelihood"],
        "claims": ["filter correctness", "estimator consistency", "simulation recovery"],
        "checklist": ["check likelihood normalization", "record recovery design", "state missing-data handling"],
    },
    "stochastic_control_dp": {
        "template_id": "stochastic_control_dp",
        "schema_version": SCHEMA_VERSION,
        "domain": "Stochastic control/dynamic programming",
        "concepts": ["state", "action", "Bellman operator", "policy"],
        "claims": ["optimality", "contraction", "approximation error"],
        "checklist": ["state boundary conditions", "record discretization", "verify policy improvement"],
    },
    "neural_transport_flows": {
        "template_id": "neural_transport_flows",
        "schema_version": SCHEMA_VERSION,
        "domain": "Neural transport/flows",
        "concepts": ["base density", "map", "Jacobian", "invertibility"],
        "claims": ["density correctness", "transport objective", "sampling efficiency"],
        "checklist": ["check log determinant", "state invertibility mechanism", "record target preservation"],
    },
    "diffusion_score_models": {
        "template_id": "diffusion_score_models",
        "schema_version": SCHEMA_VERSION,
        "domain": "Diffusion/score models",
        "concepts": ["forward process", "score", "reverse sampler", "noise schedule"],
        "claims": ["score consistency", "sampler bias", "likelihood or ELBO relation"],
        "checklist": ["record schedule", "state discretization", "separate generation metric from proof"],
    },
    "llm_bayesian_deep_learning": {
        "template_id": "llm_bayesian_deep_learning",
        "schema_version": SCHEMA_VERSION,
        "domain": "LLM/Bayesian deep learning",
        "concepts": ["prior", "posterior approximation", "uncertainty estimate", "evaluation set"],
        "claims": ["calibration", "epistemic uncertainty", "out-of-distribution behavior"],
        "checklist": ["record model policy", "check calibration", "state data and privacy constraints"],
    },
}

DOMAIN_EXTENSIONS: dict[str, dict[str, Any]] = {
    "hmc_mcmc": {
        "concept_taxonomy": ["measure-preserving dynamics", "Markov kernels", "accept-reject correction"],
        "claim_taxonomy": ["exactness", "mixing", "scaling", "diagnostic validity"],
        "assumption_classes": ["differentiable target", "integrator reversibility", "irreducibility"],
        "notation_registry": {"pi": "target density", "H": "Hamiltonian", "epsilon": "step size"},
        "theorem_roles": ["invariance theorem", "ergodicity condition"],
        "equation_roles": ["target density", "Hamiltonian", "acceptance probability"],
        "method_families": ["HMC", "NUTS", "Riemannian HMC", "transport-assisted HMC"],
        "audit_rubric": ["verify invariant distribution", "record integrator assumptions", "require diagnostics"],
    },
    "smc_particle_filtering": {
        "concept_taxonomy": ["sequential importance sampling", "resampling", "proposal adaptation"],
        "claim_taxonomy": ["unbiasedness", "filter stability", "variance control"],
        "assumption_classes": ["state transition model", "observation likelihood", "resampling scheme"],
        "notation_registry": {"x_t": "latent state", "w_t": "particle weight", "N": "particle count"},
        "theorem_roles": ["unbiased likelihood result", "consistency result"],
        "equation_roles": ["weight update", "resampling criterion", "proposal density"],
        "method_families": ["bootstrap filter", "auxiliary particle filter", "SMC sampler"],
        "audit_rubric": ["check ESS diagnostics", "state resampling trigger", "record degeneracy risks"],
    },
    "variational_inference": {
        "concept_taxonomy": ["optimization objective", "approximation family", "gradient estimator"],
        "claim_taxonomy": ["bound validity", "bias", "calibration", "scalability"],
        "assumption_classes": ["variational support", "differentiability", "stochastic estimator"],
        "notation_registry": {"q": "variational distribution", "ELBO": "evidence lower bound", "phi": "variational parameters"},
        "theorem_roles": ["bound derivation", "gradient identity"],
        "equation_roles": ["objective", "reparameterization", "score estimator"],
        "method_families": ["mean-field VI", "amortized VI", "black-box VI"],
        "audit_rubric": ["state divergence", "check estimator bias", "record posterior calibration"],
    },
    "macro_finance_structural": {
        "concept_taxonomy": ["equilibrium", "pricing kernel", "policy counterfactual"],
        "claim_taxonomy": ["identification", "counterfactual", "moment fit"],
        "assumption_classes": ["preferences", "market clearing", "shock process", "identifying restriction"],
        "notation_registry": {"m": "stochastic discount factor", "s": "state", "theta": "structural parameter"},
        "theorem_roles": ["equilibrium existence", "identification argument"],
        "equation_roles": ["Euler equation", "pricing equation", "law of motion"],
        "method_families": ["DSGE", "asset pricing", "heterogeneous-agent macro-finance"],
        "audit_rubric": ["separate structural assumptions", "record calibration", "check counterfactual scope"],
    },
    "state_space_econometrics": {
        "concept_taxonomy": ["latent dynamics", "measurement model", "likelihood evaluation"],
        "claim_taxonomy": ["filter correctness", "estimator consistency", "recovery"],
        "assumption_classes": ["transition density", "measurement density", "initial state"],
        "notation_registry": {"x_t": "latent state", "y_t": "observation", "p(y|x)": "measurement density"},
        "theorem_roles": ["filter recursion", "consistency condition"],
        "equation_roles": ["transition equation", "measurement equation", "likelihood"],
        "method_families": ["Kalman filter", "particle filter", "state-space MLE", "Bayesian state-space"],
        "audit_rubric": ["check likelihood sanity", "record missing-data handling", "run simulation recovery"],
    },
    "stochastic_control_dp": {
        "concept_taxonomy": ["Bellman recursion", "policy", "state/action constraints"],
        "claim_taxonomy": ["optimality", "convergence", "approximation error"],
        "assumption_classes": ["contraction", "compactness", "boundary condition"],
        "notation_registry": {"V": "value function", "a": "action", "T": "Bellman operator"},
        "theorem_roles": ["Bellman optimality", "contraction proof"],
        "equation_roles": ["Bellman equation", "policy update", "transition law"],
        "method_families": ["dynamic programming", "reinforcement learning", "stochastic control"],
        "audit_rubric": ["state boundary conditions", "check policy improvement", "record discretization"],
    },
    "neural_transport_flows": {
        "concept_taxonomy": ["pushforward", "invertible map", "Jacobian correction"],
        "claim_taxonomy": ["density correctness", "target preservation", "efficiency"],
        "assumption_classes": ["invertibility", "differentiability", "support coverage"],
        "notation_registry": {"T": "transport map", "J": "Jacobian", "z": "base variable"},
        "theorem_roles": ["change-of-variables result", "exactness condition"],
        "equation_roles": ["pushforward density", "log determinant", "training objective"],
        "method_families": ["normalizing flows", "transport maps", "neural samplers"],
        "audit_rubric": ["verify log determinant", "state invertibility", "record target correction"],
    },
    "diffusion_score_models": {
        "concept_taxonomy": ["forward noising", "score matching", "reverse dynamics"],
        "claim_taxonomy": ["score consistency", "sampler bias", "likelihood relation"],
        "assumption_classes": ["noise schedule", "score approximation", "discretization"],
        "notation_registry": {"s_theta": "score model", "beta_t": "noise schedule", "x_t": "diffused state"},
        "theorem_roles": ["reverse process identity", "score matching objective"],
        "equation_roles": ["SDE", "reverse update", "training loss"],
        "method_families": ["DDPM", "score SDE", "diffusion posterior samplers"],
        "audit_rubric": ["state schedule", "record discretization", "separate sample quality from proof"],
    },
    "llm_bayesian_deep_learning": {
        "concept_taxonomy": ["posterior approximation", "calibration", "evaluation protocol"],
        "claim_taxonomy": ["uncertainty quality", "OOD behavior", "calibration"],
        "assumption_classes": ["data policy", "model policy", "evaluation representativeness"],
        "notation_registry": {"theta": "model parameters", "D": "data", "p(theta|D)": "posterior"},
        "theorem_roles": ["Bayesian update approximation", "calibration argument"],
        "equation_roles": ["posterior", "predictive distribution", "calibration metric"],
        "method_families": ["Bayesian neural networks", "ensembles", "Laplace approximation", "LLM evaluation"],
        "audit_rubric": ["record provider policy", "check calibration", "state privacy constraints"],
    },
}


for template_id, extension in DOMAIN_EXTENSIONS.items():
    DOMAIN_TEMPLATES[template_id].update(extension)


def list_domain_templates() -> list[dict[str, Any]]:
    return [
        {
            "template_id": template["template_id"],
            "domain": template["domain"],
            "concept_count": len(template["concepts"]),
            "claim_count": len(template["claims"]),
            "checklist_count": len(template["checklist"]),
            "method_family_count": len(template["method_families"]),
        }
        for template in sorted(DOMAIN_TEMPLATES.values(), key=lambda row: row["template_id"])
    ]


def get_domain_template(template_id: str) -> dict[str, Any]:
    if template_id not in DOMAIN_TEMPLATES:
        raise KeyError(f"unknown domain template {template_id}")
    return deepcopy(DOMAIN_TEMPLATES[template_id])


def validate_domain_template(template: dict[str, Any]) -> list[str]:
    errors = []
    missing = REQUIRED_TEMPLATE_FIELDS - set(template)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
    for field in (
        "concepts",
        "claims",
        "checklist",
        "concept_taxonomy",
        "claim_taxonomy",
        "assumption_classes",
        "notation_registry",
        "theorem_roles",
        "equation_roles",
        "method_families",
        "audit_rubric",
    ):
        if not template.get(field):
            errors.append(f"{field} must not be empty")
    return errors
