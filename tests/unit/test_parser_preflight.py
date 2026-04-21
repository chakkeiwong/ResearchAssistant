from __future__ import annotations

from research_assistant.ingest.parser_preflight import preflight_all


def test_preflight_returns_named_checks() -> None:
    checks = preflight_all()
    names = {c.parser_name for c in checks}
    assert 'pdftotext' in names
    assert 'grobid' in names
    assert 'mineru' in names


def test_preflight_statuses_are_actionable() -> None:
    checks = preflight_all()
    for check in checks:
        assert check.status in {'available', 'unavailable', 'misconfigured'}
        assert isinstance(check.messages, list)
        assert len(check.messages) >= 1
