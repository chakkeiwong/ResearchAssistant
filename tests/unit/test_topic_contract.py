from __future__ import annotations

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.topic_contract import (
    build_topic_contract,
    plan_discovery_routes,
    topic_contract_sha256,
    validate_topic_contract,
)


@pytest.mark.parametrize(
    "topic",
    [
        "Neural Optimal Transport",
        "Particle filtering for nonlinear state-space models",
        "Federated learning and privacy",
    ],
)
def test_generic_topic_contract_and_routes_are_bounded(topic: str) -> None:
    contract = build_topic_contract(topic)
    routes = plan_discovery_routes(contract)
    assert contract["required_facets"]
    assert routes["topic_contract_sha256"] == topic_contract_sha256(contract)
    assert 5 <= routes["route_count"] <= 12
    assert [row["priority"] for row in routes["routes"]] == list(range(1, routes["route_count"] + 1))
    assert {row["purpose"] for row in routes["routes"]} >= {
        "direct_method", "foundational_or_high_citation", "recent_follow_up", "survey_or_tutorial"
    }


def test_explicit_contract_preserves_scope_data_without_domain_code() -> None:
    contract = build_topic_contract(
        "Learning for decisions",
        required_facets=["decision making", "learning"],
        optional_facets=["offline evaluation"],
        aliases=["sequential decision"],
        exclusions=["classroom education"],
        scope_note="Methods rather than educational applications.",
    )
    assert contract["required_facets"] == ["decision making", "learning"]
    assert plan_discovery_routes(contract)["route_count"] == 9


def test_topic_contract_rejects_overlap_and_unknown_fields() -> None:
    with pytest.raises(MissionStateError, match="must not overlap"):
        build_topic_contract("Topic", required_facets=["same"], exclusions=["same"])
    value = build_topic_contract("A valid topic")
    value["unknown"] = True
    with pytest.raises(MissionStateError, match="fields are not exact"):
        validate_topic_contract(value)
