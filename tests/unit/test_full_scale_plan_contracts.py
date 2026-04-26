from __future__ import annotations

from pathlib import Path

from research_assistant.industrial.full_scale import PHASE_CONTRACTS, get_phase_contract, list_phase_contracts


def test_full_scale_phase_contracts_cover_all_phases() -> None:
    phases = list_phase_contracts()

    assert len(phases) == 16
    assert phases[0]['phase_id'] == 'phase_00_architecture_baseline'
    assert phases[-1]['phase_id'] == 'phase_15_scalable_ingestion'

    required_fields = {
        'phase_id',
        'title',
        'subsystem',
        'goal',
        'milestone_status',
        'dependencies',
        'implementation_contracts',
        'tests',
        'usefulness_verification',
        'acceptance_criteria',
        'stop_conditions',
        'governed_integration_required',
    }
    for phase in phases:
        assert required_fields.issubset(phase)
        assert phase['implementation_contracts']
        assert phase['tests']
        assert phase['usefulness_verification']
        assert phase['acceptance_criteria']


def test_governed_phases_have_stop_conditions() -> None:
    governed = [phase for phase in PHASE_CONTRACTS if phase.governed_integration_required]

    assert governed
    for phase in governed:
        assert phase.stop_conditions
        assert phase.milestone_status in {'m0_contract_complete', 'blocked_for_governed_integration'}
        assert phase.dependencies


def test_phase_lookup() -> None:
    phase = get_phase_contract('phase_09_llm_governance')

    assert phase['title'] == 'LLM Governance And Evaluation'
    assert phase['governed_integration_required'] is True
    assert 'live credentials or provider access required' in phase['stop_conditions']


def test_architecture_documents_and_adrs_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    architecture = root / 'docs' / 'architecture' / 'industrial_platform_architecture.md'
    adr_dir = root / 'docs' / 'architecture' / 'adr'

    assert architecture.exists()
    text = architecture.read_text()
    for heading in ['## Trust Boundary', '## Subsystems', '## Execution Milestones', '## Stop Conditions']:
        assert heading in text

    expected_adrs = {
        '0000-adr-template.md',
        '0001-storage-backend.md',
        '0002-identity-and-rbac.md',
        '0003-background-jobs.md',
        '0004-search-and-indexing.md',
        '0005-llm-provider-policy.md',
        '0006-deployment-model.md',
    }
    assert expected_adrs.issubset({path.name for path in adr_dir.glob('*.md')})
