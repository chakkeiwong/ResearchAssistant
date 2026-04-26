from __future__ import annotations

from research_assistant.schemas.artifact import BASE_ARTIFACT_FIELDS, base_artifact, has_base_artifact_fields
from research_assistant.schemas.domain_templates import DOMAIN_TEMPLATES, validate_domain_template
from research_assistant.schemas.paper_record import PaperRecord


def test_paper_record_round_trip() -> None:
    rec = PaperRecord(id='p1', title='Test')
    data = rec.to_dict()
    restored = PaperRecord.from_dict(data)
    assert restored.id == 'p1'
    assert restored.title == 'Test'


def test_base_artifact_contract_carries_review_boundary() -> None:
    payload = base_artifact(artifact_type='test_artifact', artifact_id='a1', paper_id='p1')

    assert BASE_ARTIFACT_FIELDS.issubset(payload)
    assert has_base_artifact_fields(payload)
    assert payload['review_status'] == 'requires_human_review'
    assert payload['requires_human_review'] is True


def test_domain_templates_have_required_audit_fields() -> None:
    assert {
        'hmc_mcmc',
        'smc_particle_filtering',
        'variational_inference',
        'macro_finance_structural',
        'state_space_econometrics',
        'stochastic_control_dp',
        'neural_transport_flows',
        'diffusion_score_models',
        'llm_bayesian_deep_learning',
    }.issubset(DOMAIN_TEMPLATES)

    for template in DOMAIN_TEMPLATES.values():
        assert validate_domain_template(template) == []
        assert template['concepts']
        assert template['claims']
        assert template['checklist']
