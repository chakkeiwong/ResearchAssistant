from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from collections.abc import Iterator
from typing import Any

from research_assistant import cli


TOP_LEVEL_COMMANDS = (
    "init", "version", "config", "workspace", "backup", "doctor", "demo",
    "privacy", "release-report", "mcp", "repository-hygiene",
    "individual-git-release", "bounded-workflow", "performance",
    "parser-tool-matrix", "parser-benchmark-smoke", "survey", "surveybench",
    "arxiv-batch", "release-artifacts", "onboarding-report", "platform-status",
    "ingest", "find", "show", "export-context", "review-list", "review-show",
    "review-mark", "review-write", "link-add", "artifact-paths",
    "industrial-validate", "domain-templates", "derivation", "experiment",
    "graph-report", "review-meta", "benchmark-manifest", "synthesis",
    "governance", "job", "dashboard-export", "traceability", "model-policy",
    "collaboration", "artifact-index", "industrial-readiness", "full-scale-plan",
    "industrial-release", "tool-contract", "operations-policy", "sop",
    "audit-claim", "audit-note", "discover", "download-paper", "papers-citing",
    "papers-cited-by", "citation-neighborhood", "citation-graph-build",
    "citation-graph-show", "citation-graph-export",
    "graph-node-download-proposal", "inbox-list", "inbox-show",
    "literature-audit-propose", "literature-audit-show",
    "literature-audit-approve", "parse-pdf", "parser-preflight",
    "evidence-context", "source-fetch", "source-show", "source-sections",
    "source-equations", "source-theorems", "source-citations",
    "source-bibliography", "source-macros", "source-labels", "source-section",
    "source-refs", "source-equation", "source-theorem",
)

SURVEY_COMMANDS = (
    "build", "anchors", "packet", "coverage-ledgers",
    "compose-reviewed-final-packet", "hostile-review",
    "run-public-source-workflow", "import-claim-review",
    "import-source-safety-review", "import-omission-review",
    "import-workflow-blocker-review", "merge-reviewed-evidence",
    "prepare-human-review", "validate-human-attestation", "render-human-review",
    "qualitative-assessment",
)

CLI_SCHEMA_SHA256 = "807a9ce76cfaf6c85b47eb6c83d4e19562dcaf674d694463a06155bbcbc10d1b"


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    return next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )


def _stable_value(value: Any) -> Any:
    if callable(value):
        return {"callable": value.__name__}
    if isinstance(value, type):
        return {"type": value.__name__}
    return repr(value)


def _parser_schema(parser: argparse.ArgumentParser, path: tuple[str, ...] = ()) -> Iterator[dict[str, Any]]:
    yield {
        "path": path,
        "parser": {
            "prog": parser.prog,
            "description": parser.description,
            "epilog": parser.epilog,
            "defaults": {key: _stable_value(value) for key, value in parser._defaults.items()},
        },
    }
    for action in parser._actions:
        choices = action.choices
        row = {
            "path": path,
            "action": type(action).__name__,
            "dest": action.dest,
            "options": action.option_strings,
            "required": getattr(action, "required", None),
            "default": _stable_value(action.default),
            "choices": sorted(choices) if isinstance(choices, (list, tuple, set)) else None,
            "nargs": action.nargs,
            "const": _stable_value(action.const),
            "type": getattr(action.type, "__name__", None),
            "help": action.help,
            "metavar": action.metavar,
        }
        if isinstance(action, argparse._SubParsersAction):
            row["choices"] = list(action.choices)
            yield row
            for name, child in action.choices.items():
                yield from _parser_schema(child, (*path, name))
        else:
            yield row


def test_public_command_inventory_is_explicit() -> None:
    parser = cli.build_parser()
    top_level = _subparsers(parser)
    assert tuple(top_level.choices) == TOP_LEVEL_COMMANDS
    assert tuple(_subparsers(top_level.choices["survey"]).choices) == SURVEY_COMMANDS


def test_cli_parser_schema_changes_require_explicit_review() -> None:
    rows = list(_parser_schema(cli.build_parser()))
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str).encode()
    assert len(rows) == 951
    assert hashlib.sha256(payload).hexdigest() == CLI_SCHEMA_SHA256


def test_build_parser_remains_a_small_composition_root() -> None:
    source_lines, _ = inspect.getsourcelines(cli.build_parser)
    assert len(source_lines) <= 160, (
        "register new commands in the owning research_assistant.cli_registration "
        "module instead of growing build_parser()"
    )
