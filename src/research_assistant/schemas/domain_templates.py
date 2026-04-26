from __future__ import annotations

from copy import deepcopy
from typing import Any

from research_assistant.schemas.artifact import SCHEMA_VERSION

REQUIRED_TEMPLATE_FIELDS = {"template_id", "domain", "concepts", "claims", "checklist"}

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


def list_domain_templates() -> list[dict[str, Any]]:
    return [
        {
            "template_id": template["template_id"],
            "domain": template["domain"],
            "concept_count": len(template["concepts"]),
            "claim_count": len(template["claims"]),
            "checklist_count": len(template["checklist"]),
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
    for field in ("concepts", "claims", "checklist"):
        if not template.get(field):
            errors.append(f"{field} must not be empty")
    return errors
