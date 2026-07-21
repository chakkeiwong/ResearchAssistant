from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.survey.mission_state import MissionStateError
from research_assistant.survey.qualitative_assessment import (
    ASSESSMENT_SCHEMA,
    build_assessment,
    build_assessment_bundle,
    validate_assessment,
    validate_assessment_bundle,
    write_assessment,
    write_assessment_bundle,
)
from scripts.build_m22_qualitative_assessment_bundle import _assessments


def _assessment(**overrides: object) -> dict:
    values: dict[str, object] = {
        "subject_id": "arxiv:2201.12220v3",
        "assessment_type": "paper",
        "summary": "The source presents a concrete method and evaluation, but its scope is narrower than a general survey claim.",
        "merits": ["The method and evaluation are available in retained technical text."],
        "concerns": ["The evidence does not establish general performance beyond the reported setting."],
        "uncertainties": ["The retained source set does not establish how later work changed the result."],
        "evidence_refs": ["source_reading/2201_12220v3/README.md", "anchor:2201_12220v3:method"],
        "next_action": "Use qualified wording and inspect the cited method and evaluation sections.",
    }
    values.update(overrides)
    return build_assessment(**values)  # type: ignore[arg-type]


def test_assessment_is_exact_and_never_promotes() -> None:
    value = _assessment()
    assert value["schema_version"] == ASSESSMENT_SCHEMA
    assert value["claim_support_allowed"] is False
    assert value["ready_for_prose"] is False
    assert validate_assessment(value) == value


@pytest.mark.parametrize("field", ["summary", "next_action"])
def test_required_text_cannot_be_empty(field: str) -> None:
    with pytest.raises(MissionStateError) as exc:
        _assessment(**{field: " "})
    assert exc.value.code == "invalid_assessment_text"


@pytest.mark.parametrize("field", ["merits", "concerns", "uncertainties", "evidence_refs"])
def test_required_lists_must_have_bounded_text(field: str) -> None:
    with pytest.raises(MissionStateError) as exc:
        _assessment(**{field: []})
    assert exc.value.code == "invalid_assessment_list"
    with pytest.raises(MissionStateError) as exc:
        _assessment(**{field: ["x" * 501]})
    assert exc.value.code == "invalid_assessment_text"


def test_type_and_promotion_are_rejected() -> None:
    with pytest.raises(MissionStateError) as exc:
        _assessment(assessment_type="reviewer")
    assert exc.value.code == "invalid_assessment_type"
    value = _assessment()
    value["ready_for_prose"] = True
    with pytest.raises(MissionStateError) as exc:
        validate_assessment(value)
    assert exc.value.code == "invalid_assessment_promotion"


def test_write_assessment_is_canonical(tmp_path: Path) -> None:
    path = tmp_path / "assessment.json"
    result = write_assessment(assessment=_assessment(), output_path=path)
    assert result["status"] == "qualitative_assessment_written"
    assert json.loads(path.read_text())["assessment_type"] == "paper"


def test_bundle_requires_unique_replayable_assessments(tmp_path: Path) -> None:
    bundle = build_assessment_bundle(
        topic="Neural Optimal Transport",
        source_scope="Seven retained sources plus aggregate omission frontiers.",
        assessments=[_assessment()],
    )
    assert validate_assessment_bundle(bundle) == bundle
    path = tmp_path / "bundle.json"
    result = write_assessment_bundle(bundle=bundle, output_path=path)
    assert result["assessment_count"] == 1
    duplicated = {**bundle, "assessments": [bundle["assessments"][0], bundle["assessments"][0]]}
    with pytest.raises(MissionStateError) as exc:
        validate_assessment_bundle(duplicated)
    assert exc.value.code == "invalid_qualitative_bundle"


def test_production_assessment_evidence_files_and_source_lines_resolve() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    for assessment in _assessments():
        for reference in assessment["evidence_refs"]:
            parts = reference.split(":")
            path = None
            suffix: list[str] = []
            for index in range(len(parts), 0, -1):
                candidate = repository_root / ":".join(parts[:index])
                if candidate.is_file():
                    path = candidate
                    suffix = parts[index:]
                    break
            assert path is not None, reference
            if len(suffix) == 1 and suffix[0].isdigit() and path.suffix.casefold() not in {".json", ".csv"}:
                assert int(suffix[0]) <= sum(
                    1 for _ in path.open(encoding="utf-8", errors="replace")
                ), reference
