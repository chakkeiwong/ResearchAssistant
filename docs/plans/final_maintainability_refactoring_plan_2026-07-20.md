# Final Maintainability Refactoring Plan - 2026-07-20

## Status

`EXECUTED_VALIDATED_READY_TO_PUSH`

## Objective

Complete the next safe maintainability slice for a junior IT maintainer by
decomposing the two largest CLI action routers and extracting pure orchestration
decision construction, while preserving the exact Python 3.11 product, CLI,
artifact, replay, source-safety, and release contracts.

The completed release-hardening and CLI-registration work in the dirty tree is
the baseline. This plan will be committed together with that accumulated work
after final validation, then pushed to `origin/main` as explicitly requested.

## Baseline

- `cmd_surveybench()` is 304 lines with 18 action branches.
- `cmd_survey()` is 241 lines with 16 action branches and one protected-output
  guard shared by every action.
- `survey/orchestrate.py` is 3,467 lines. `_next_action()` is a 335-line pure
  decision constructor; `_dispatch_safe_local_stage()` is a 225-line mutating
  stage executor; `MissionStateManager` remains a 1,331-line durability class.
- Existing tests monkeypatch CLI-level service names and orchestration dispatch
  functions. Those are real testability seams that must remain stable.
- The current release evidence applies only to source fingerprint
  `c6e5b10fcba98d84e0e5b394e9fda32b751c7da8feff9f0ef123569173ea92f9`.
  Any implementation edit makes it stale.

## Planned Changes

### Phase 1 - Characterize Dispatch Contracts

- Pin the complete survey and SurveyBench action-to-handler inventories.
- Add direct router tests for unknown actions and representative success/failure
  status mapping.
- Retain the existing 951-record parser schema fingerprint as the exact public
  CLI comparator.

### Phase 2 - Decompose CLI Action Execution

- Add `cli_actions/survey.py` and `cli_actions/surveybench.py`.
- Give each action a small named handler and expose explicit immutable dispatch
  maps.
- Keep `cmd_survey()` and `cmd_surveybench()` in `cli.py` as stable facades.
- Inject CLI-level services into the action modules so existing monkeypatches,
  output formatting, return codes, and path redaction remain unchanged.
- Keep the survey protected-output guard in the facade so no action can bypass
  it.

### Phase 3 - Extract Pure Orchestration Decisions

- Move `_next_action()`, gate summaries, safe-command construction, and
  reviewed-blocker command construction to a cohesive
  `survey/next_action.py` module.
- Keep compatibility wrappers in `survey/orchestrate.py` for current internal
  callers and tests.
- Inject the UTC timestamp so deterministic characterization can compare exact
  payload bytes.
- Do not move `_dispatch_safe_local_stage()`, `_run_safe_local_supervisor()`, or
  `MissionStateManager` in this plan.

### Phase 4 - Documentation And Static Boundaries

- Update the maintainer guide with CLI action ownership and orchestration
  decision ownership.
- Add the new stable action/decision modules to the existing mypy scope.
- Record remaining mutable workflow and durability refactoring as future work.

### Phase 5 - Validation, Commit, And Push

- Run focused CLI action, survey orchestration, replay, crash-recovery, and
  architecture tests.
- Run static checks and the complete eight-command release-candidate gate.
- Validate fresh evidence against the final source fingerprint and verify
  `release-report` has zero blockers/warnings.
- Commit the complete accumulated release and maintainability changes without
  generated `build/`, `dist/`, private, or ignored bulk artifacts.
- Push `main` to `origin` and verify the remote branch head.

## Skeptical Plan Audit

### Wrong Baseline

The prior release gate is not evidence for the new bytes. It is the behavioral
comparator only. Promotion requires a fresh fingerprinted gate after all source
and test edits.

### Proxy Metrics

Shorter functions, more modules, and dispatch-map coverage are structural
diagnostics. They do not establish correctness. Promotion requires exact parser
schema parity, CLI output/return-code tests, survey replay/crash tests, packaging,
clean install, and source-bound release evidence.

### Hidden Coupling

- Tests monkeypatch names in `research_assistant.cli`; moving service lookup
  directly into new modules would silently break those seams. Services will be
  injected from the stable facade at call time.
- Tests monkeypatch `orchestrate._dispatch_safe_local_stage`; that wrapper will
  not move or change.
- `_next_action()` includes a timestamp. Exact parity tests require an injected
  clock rather than deleting or normalizing the field.
- Restricted SurveyBench workspaces generate their own minimal CLI runtime and
  do not copy the full application CLI, so application action modules must not
  expand that restricted source closure.

### Environment Mismatch

The release target remains Python 3.11.x on Linux/WSL. Tests are deliberate
CPU-only. No network, provider, credential, PDF download, GPU, publication, or
scientific campaign is required or authorized.

### Semantic Vetoes

Stop or revise if any of these occur:

- the parser schema fingerprint, command inventory, option/default/help surface,
  stdout JSON, output-file bytes, path redaction, or exit code changes;
- an action can bypass protected survey output checks;
- active arXiv-only defaults or nonclaims change;
- review, replay, hostile-review, source-safety, crash-recovery, lock, orphan,
  tamper, or canonical-artifact tests fail;
- restricted SurveyBench source closure expands;
- the refactor requires moving mutable stage execution or mission durability
  logic without new characterization; or
- final source-bound release evidence is missing, partial, failed, or stale.

### Pre-Mortem

- A dispatch map could omit an action. Earliest diagnostic: exact equality with
  parser action inventories and writer-guard inventories.
- A handler could return the right JSON with the wrong exit code. Earliest
  diagnostic: parameterized direct router tests plus existing CLI integration.
- Dependency injection could capture stale monkeypatch targets. Earliest
  diagnostic: existing monkeypatch-heavy integration files run before the full
  suite.
- Next-action extraction could alter one command string or required artifact.
  Earliest diagnostic: deterministic old/new characterization fixtures and the
  existing mission integration assertions.
- A broad orchestration move could break crash recovery while passing shallow
  tests. Prevention: mutable dispatch and mission-state code are explicitly out
  of scope.

The plan passes skeptical audit because it narrows the work to pure routing and
decision boundaries with direct comparators, preserves known testability seams,
and rejects mutation/durability movement whose risk is not yet proportionately
characterized.

## Verification

```bash
CUDA_VISIBLE_DEVICES=-1 scripts/ra-agent pytest \
  tests/unit/test_cli_architecture.py \
  tests/unit/test_cli_action_dispatch.py \
  tests/unit/test_survey_next_action.py \
  tests/integration/test_cli_surveybench_commands.py \
  tests/integration/test_cli_commands.py -q
CUDA_VISIBLE_DEVICES=-1 scripts/ra-agent pytest \
  tests/unit/test_literature_survey_m16_phase5.py \
  tests/unit/test_literature_survey_m16_phase6.py \
  tests/unit/test_literature_survey_m16_phase7.py \
  tests/unit/test_literature_survey_m16_phase8.py -q
scripts/run_static_checks.sh
git diff --check
CUDA_VISIBLE_DEVICES=-1 python3.11 scripts/run_release_candidate_gate.py
```

## Execution Record

The skeptical audit was completed before implementation. It found no material
baseline, semantic, coupling, environment, proxy-metric, or stop-condition flaw.
The plan was executed with the following final implementation boundaries:

- `cli_actions/survey.py` and `cli_actions/surveybench.py` own named action
  handlers behind immutable `MappingProxyType` dispatch maps.
- `cli.py` retains small protected-output facades and injects services at call
  time, preserving CLI-level monkeypatch seams and return-code behavior.
- `survey/next_action.py` owns pure base-gate, review-import, blocker, and
  final-packet decision helpers. `orchestrate.py` retains compatibility wrappers,
  mutable stage dispatch, and supervisor behavior.
- `MissionStateManager` was not moved. Its replay, crash-recovery, tamper,
  orphan, lock, and canonical-artifact boundaries remain in place.
- The maintainer guide and static-check mypy scope document these ownership
  boundaries.
- `scripts/run_tests.sh` now runs the complete active inventory in four bounded
  `setsid`-isolated partitions. This preserves process-group signal tests while
  avoiding the host's termination of a monolithic long-running pytest process.

The direct refactor characterization passed with `291 passed, 73 skipped`.
The complete CPU-only test inventory passed in four isolated partitions:
`1283 passed, 229 skipped` (unit), `89 passed` (large CLI integration),
`114 passed` (remaining integration), and `231 passed` (scripts), totaling
`1717 passed, 229 skipped`. The complete eight-command release gate returned
zero for every command after this harness change. Fresh evidence is source-bound
to:

```text
sha256: 9ea1e58b127958d35aaf95e9b1c0c77d92f83809672ccf3de8c7e87a86c70a14
files: 291
bytes: 5045337
python: 3.11.14
```

`validate_release_gate_evidence(Path.cwd())` returned `passed` with no issues.
A disposable initialized workspace ran init, demo setup, demo run, and
`release-report`; the report returned `ready_for_release_candidate_review` with
zero blockers and zero warnings. Ruff and mypy were not installed in this local
environment, so `run_static_checks.sh` executed compile and shell checks and
reported those two checks as unavailable; CI installs the Python 3.11 dev extra
and runs them.

## Remaining Deliberate Scope

The large mutable stage executor and `MissionStateManager` remain intentionally
in `survey/orchestrate.py` and `survey/mission_state.py`. Further movement should
start with characterization tests for mutation and durability invariants; it is
not required for this release pass. Cross-platform, hosted-service, scientific
correctness, literature-completeness, and full parser-quality claims remain
outside this engineering release evidence.
