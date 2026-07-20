from __future__ import annotations

import argparse
import inspect

import pytest

from research_assistant import cli
from research_assistant.cli_actions.survey import SURVEY_ACTION_HANDLERS, execute_survey_action
from research_assistant.cli_actions.surveybench import (
    SURVEYBENCH_ACTION_HANDLERS,
    execute_surveybench_action,
)


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    return next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )


def test_action_dispatch_maps_cover_registered_commands_exactly() -> None:
    top_level = _subparsers(cli.build_parser())
    survey_actions = _subparsers(top_level.choices["survey"])
    surveybench_actions = _subparsers(top_level.choices["surveybench"])

    assert tuple(SURVEY_ACTION_HANDLERS) == tuple(survey_actions.choices)
    assert tuple(SURVEYBENCH_ACTION_HANDLERS) == tuple(surveybench_actions.choices)
    assert set(SURVEY_ACTION_HANDLERS) == set(cli.SURVEY_WRITE_OUTPUT_FIELDS)


def test_unknown_action_errors_remain_explicit() -> None:
    with pytest.raises(SystemExit, match="unknown survey action missing"):
        execute_survey_action(argparse.Namespace(survey_action="missing"), object())  # type: ignore[arg-type]
    with pytest.raises(SystemExit, match="unknown surveybench action missing"):
        execute_surveybench_action(
            argparse.Namespace(surveybench_action="missing"),
            object(),  # type: ignore[arg-type]
        )


def test_action_dispatch_maps_are_read_only() -> None:
    with pytest.raises(TypeError):
        SURVEY_ACTION_HANDLERS["missing"] = object()  # type: ignore[index, assignment]
    with pytest.raises(TypeError):
        SURVEYBENCH_ACTION_HANDLERS["missing"] = object()  # type: ignore[index, assignment]


def test_cli_facades_remain_small_and_inject_services_at_call_time(monkeypatch) -> None:
    observed = {}

    def survey_execute(args, services):
        observed["survey"] = services.build_survey_evidence_packet
        return 17

    def surveybench_execute(args, services):
        observed["surveybench"] = services.score_survey_task
        return 23

    replacement_survey = lambda **_kwargs: {"status": "replacement"}
    replacement_surveybench = lambda *_args, **_kwargs: {"status": "replacement"}
    monkeypatch.setattr(cli, "execute_survey_action", survey_execute)
    monkeypatch.setattr(cli, "execute_surveybench_action", surveybench_execute)
    monkeypatch.setattr(cli, "_guard_survey_write_paths", lambda _args: None)
    monkeypatch.setattr(cli, "build_survey_evidence_packet", replacement_survey)
    monkeypatch.setattr(cli, "score_survey_task", replacement_surveybench)

    assert cli.cmd_survey(argparse.Namespace(survey_action="build")) == 17
    assert cli.cmd_surveybench(argparse.Namespace(surveybench_action="run")) == 23
    assert observed == {
        "survey": replacement_survey,
        "surveybench": replacement_surveybench,
    }
    assert len(inspect.getsourcelines(cli.cmd_survey)[0]) <= 50
    assert len(inspect.getsourcelines(cli.cmd_surveybench)[0]) <= 35
