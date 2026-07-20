# Maintainer Guide

This guide is for developers maintaining `research-assistant` without the
project history in their head.

## Release Target

The current release is an individual local research tool. One researcher runs
the tool against a local filesystem workspace. Sharing happens through Git:
checkout another repository, inspect it, run hygiene checks, dry-run a merge,
apply only with confirmation, and rebuild derived artifacts.

The current release is not a shared database, hosted service, SSO/RBAC system,
real-time collaboration tool, or hosted UI. Those are future extensions.

The supported runtime is Python 3.11.x only. Keep `pyproject.toml`, CI,
platform diagnostics, release evidence, and release docs aligned; do not widen
the range without a separately validated compatibility decision.

## Module Map

- `src/research_assistant/cli.py`: small command facades and the command-line
  composition root. Keep `main(argv)` stable because integration tests call it
  directly. Do not add argument declarations or large action branches here.
- `src/research_assistant/cli_actions/`: survey and SurveyBench action execution.
  Each registered action has one named handler in an explicit dispatch map.
  Services are supplied by `cli.py` at call time to preserve test seams.
- `src/research_assistant/cli_registration/`: argument declarations grouped by
  lifecycle/release, survey, SurveyBench, local paper library, research/source,
  and future industrial scaffold. Add an option or subcommand to its owning
  module and inject the handler explicitly from `build_parser()`.
- `src/research_assistant/core_utils.py`: canonical JSON, hashing, UTC timestamp,
  and atomic byte-write primitives shared by stable artifact boundaries.
- `src/research_assistant/release_evidence.py`: source fingerprint and validation
  for the executed release-candidate gate.
- `src/research_assistant/individual_release.py`: local workspace lifecycle,
  configuration, backup/restore, diagnostics, demo workflow, release artifacts,
  and release report.
- `src/research_assistant/individual_git_release.py`: shareable workspace
  policy, repository hygiene, workspace merge/rebuild, validation evidence,
  fixture rehearsal, performance rehearsal, and the individual Git release
  gate.
- `src/research_assistant/industrial/`: local scaffold artifacts for future
  industrial platform work. These are not current multi-user production
  services.
- `src/research_assistant/source/`, `ingest/`, `query/`, and `summarize/`:
  source inspection, parser/adaptor, discovery, review, and summary workflows.
- `src/research_assistant/survey/next_action.py`: pure construction of the next
  supervised survey action. Mutable stage dispatch stays in
  `survey/orchestrate.py`; durable mission state stays in
  `survey/mission_state.py`.

## Supported And Historical Code

The active v0.1 contract is a local, single-user, Python 3.11 tool using public
arXiv paths. OpenAlex-containing canonical mission fixtures are historical
compatibility tests marked `legacy_provider`; they are intentionally visible
but are not an active release promise. Do not make those tests pass by silently
restoring credentials or broadening the provider contract.

The `industrial/` package and its CLI registration are future local scaffold
artifacts. Their presence does not mean that shared database, service, RBAC,
SSO, or hosted-UI behavior exists.

## Where To Make A Change

| Change | Implementation | Registration and primary tests |
| --- | --- | --- |
| Add or change a CLI option | Keep behavior in the owning service or `cli_actions/*` handler | Owning `cli_registration/*.py`; update `test_cli_architecture.py` only after reviewing the intentional public-contract change |
| Add or change a survey/SurveyBench action | Named handler and immutable map in `cli_actions/` | Owning `cli_registration/*.py`; `test_cli_action_dispatch.py` and matching CLI integration tests |
| Change workspace setup, backup, doctor, or release reporting | `individual_release.py` | `cli_registration/lifecycle.py`; `test_individual_release_cli.py` |
| Change Git sharing, hygiene, merge, or validation | `individual_git_release.py` | `cli_registration/lifecycle.py`; `test_individual_git_release_cli.py` |
| Change survey packet or mission behavior | Owning module under `survey/` | `cli_registration/survey.py`; `test_cli_commands.py` and the matching survey unit phase tests |
| Change survey next-action decisions | Pure helpers in `survey/next_action.py`; keep compatibility wrappers in `survey/orchestrate.py` | `test_survey_next_action.py` and matching Phase 5-8 tests |
| Change SurveyBench replay or scoring | Owning module under `benchmarks/` | `cli_registration/surveybench.py`; `test_cli_surveybench_commands.py` |
| Change paper ingest, local query, or review | `ingest/`, `query/`, or storage module | `cli_registration/library.py` or `research.py`; `test_cli_library_commands.py` |
| Change PDF parser execution | `ingest/parser_command.py` and the adapter | Parser command/adapter unit tests plus the separate external-tool gate |
| Change a stable JSON or hash boundary | Owning module and `core_utils.py` only when behavior is genuinely shared | Canonical-byte, replay, tamper, and release-evidence tests |

`tests/unit/test_cli_architecture.py` pins the public command inventory and the
full parser schema, including options, defaults, choices, help, and handlers.
When an intentional CLI change breaks its hash, inspect the schema difference
first; do not update the hash merely to make the test green.

Avoid large class hierarchies for dictionary-shaped artifact schemas. Prefer a
small dataclass or protocol at a stable boundary, explicit composition, and
pure helper functions. `MissionStateManager` and survey orchestration contain
replay, crash-recovery, and artifact-durability invariants; add focused
characterization tests before moving their logic between modules.

## Testing Decision Tree

1. Run the nearest unit test for the edited module.
2. For a CLI registration or handler change, run
   `tests/unit/test_cli_architecture.py` and the matching `test_cli_*_commands.py`.
3. For survey state, replay, serialization, or artifact changes, run the matching
   survey phase tests and `tests/integration/test_cli_commands.py`.
4. For parser adapters, run normal mocked unit tests first. Run
   `scripts/run_external_tool_tests.sh` separately because installed tools vary
   by machine.
5. Before handing off a release candidate, run
   `python scripts/run_release_candidate_gate.py`. Any source edit invalidates
   prior `dist/release_gate_evidence.json` evidence.

Use `CUDA_VISIBLE_DEVICES=-1` for deliberate CPU-only validation. These tests do
not need a GPU.

## Trust Boundaries

Generated artifacts are review material. Parser outputs, benchmark results,
derivation worksheets, traceability reports, synthesis proposals, readiness
reports, and validation records do not certify mathematical correctness or
scientific parser accuracy.

Accepted human review conclusions must stay explicit. A merge or generated
proposal must not silently overwrite accepted `technical_audit` content.

## Git Sharing Rules

The shareable workspace policy lives in
`docs/release/shareable_workspace_policy.json` and is mirrored by default policy
constants in `individual_git_release.py`.

Forbidden content includes private PDFs, raw/extracted papers, backup archives,
credentials, provider keys, tokens, `.codex`, `.claude`, caches, `build/`,
`dist/`, and bytecode.

Merge is dry-run by default. Real copy requires `--apply --confirm-merge`.
Conflicts and accepted-audit disagreements block apply. After apply, run
`ra workspace rebuild-derived`.

## Release Gate Model

The supported release contract is one researcher using Linux/WSL with Python
3.11.x. Local fixture and parser evidence support this contract; external-user
and macOS validation are out of scope. Release-owner approval is required only for
tagging or publication, not for local use.

Parser smoke remains diagnostic and must not be presented as scientific
extraction-accuracy evidence.

The private v0.1 candidate additionally requires
`dist/release_gate_evidence.json` from
`python scripts/run_release_candidate_gate.py`. The evidence is valid only for
the exact source fingerprint and Python 3.11.x runtime that produced it.
Release artifact builds use the already provisioned Python 3.11 build tools
with `--no-isolation`, so the otherwise offline gate does not download build
dependencies.

## Common Validation Commands

From a source checkout, prefer `scripts/ra-dev` and `scripts/ra-agent` so
maintainers and agents do not need to remember `PYTHONPATH=src`:

```bash
scripts/ra-agent pytest tests/integration/test_individual_release_cli.py -q
scripts/ra-agent pytest tests/integration/test_industrial_platform_cli.py -q
scripts/ra-agent fast-tests
scripts/run_static_checks.sh
timeout 600 scripts/run_bounded_tests.sh
timeout 1800 scripts/run_tests.sh
CUDA_VISIBLE_DEVICES=-1 timeout 600 scripts/run_external_tool_tests.sh
timeout 300 scripts/build_release_artifacts.sh
env WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh
GATE_ROOT=/tmp/research-assistant-maintainer-gate timeout 300 scripts/run_individual_git_release_gate.sh
scripts/ra-agent diff-check
scripts/ra-agent status
python scripts/run_release_candidate_gate.py
```

`scripts/run_static_checks.sh` runs compile and shell checks and uses Ruff and
mypy when the Python 3.11 development extra is installed. The CI workflow
installs that extra. `scripts/run_coverage.sh` records a branch-coverage
baseline but coverage percentage is diagnostic until a reviewed threshold is
declared. `scripts/run_tests.sh` runs the complete active inventory in four
independent CPU-only partitions, reports each partition separately, and fails
if any partition fails or times out.

The helpers remove source-checkout friction only. Live network commands,
review-write apply, PDF download execution, restore, merge apply, and
destructive operations still require explicit user approval, explicit CLI
confirmation, or a bounded local grant.

Use a clean local clone for final release-gate reproduction.

## LaTeX Report

The tracked release report source is
`proposal/research_development_assistant_design.tex`. The tracked PDF is
`proposal/research_development_assistant_design.pdf`.

The report should describe the implemented individual local/Git release first.
Multi-user database/service/RBAC/hosted UI work belongs in a future extension
section.

If rebuilding the PDF, run the TeX command from `proposal/` and do not commit
`.aux`, `.log`, `.out`, `.toc`, `.fdb_latexmk`, `.fls`, or similar temporary
files.

## What Not To Commit

Do not commit `.codex`, `.claude/`, `.pytest_cache/`, `build/`, `dist/`,
bytecode, generated temp workspaces, backup archives, private papers, private
paths, credentials, provider keys, or tokens. Files under ignored
`docs/plans/` must be force-staged only when they are intentionally part of the
handoff record.

Do not hand-edit generated release artifacts or evidence under `build/` and
`dist/`. Recreate them with the documented scripts. Do not edit mission
`.artifact_state` files to repair a workflow; use the supported resume/repair
path so lineage and replay checks remain meaningful.
