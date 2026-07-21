from __future__ import annotations

import subprocess

from research_assistant.ingest.parser_command import (
    DEFAULT_PARSER_TIMEOUT_SECONDS,
    PARSER_TIMEOUT_ENV,
    ParserExecutionPolicy,
    run_parser_command,
)


def test_parser_execution_policy_reads_positive_environment_value(monkeypatch) -> None:
    monkeypatch.setenv(PARSER_TIMEOUT_ENV, "42")
    assert ParserExecutionPolicy.from_environment().timeout_seconds == 42


def test_parser_execution_policy_rejects_invalid_environment_value(monkeypatch) -> None:
    monkeypatch.setenv(PARSER_TIMEOUT_ENV, "invalid")
    assert ParserExecutionPolicy.from_environment().timeout_seconds == DEFAULT_PARSER_TIMEOUT_SECONDS


def test_parser_command_timeout_is_structured(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        assert kwargs["timeout"] == 3
        raise subprocess.TimeoutExpired(args[0], 3, output="partial", stderr="slow")

    monkeypatch.setattr("research_assistant.ingest.parser_command.subprocess.run", fake_run)

    result = run_parser_command(["parser", "paper.pdf"], policy=ParserExecutionPolicy(3))

    assert result.timed_out is True
    assert result.returncode is None
    assert result.stdout == "partial"
    assert result.stderr == "slow"
    assert result.error == "command timed out after 3 seconds"
    assert result.succeeded is False


def test_parser_command_os_error_is_structured(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("parser missing")

    monkeypatch.setattr("research_assistant.ingest.parser_command.subprocess.run", fake_run)

    result = run_parser_command(["missing-parser"], policy=ParserExecutionPolicy(5))

    assert result.error == "parser missing"
    assert result.returncode is None
    assert result.succeeded is False
