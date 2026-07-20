# Release Checklist

Run these bounded checks before using a Linux local release candidate:

```bash
scripts/ra-agent fast-tests
scripts/ra-agent focused-tests
scripts/run_static_checks.sh
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/run_tests.sh
scripts/ra-agent pytest tests/integration/test_individual_release_cli.py -q
scripts/run_packaging_smoke.sh
CUDA_VISIBLE_DEVICES=-1 scripts/run_external_tool_tests.sh
scripts/build_release_artifacts.sh
PYTHONPATH=src python3.11 -m research_assistant.cli release-artifacts validate
WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl scripts/run_clean_install_smoke.sh
scripts/run_release_smoke.sh
CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src python3.11 scripts/run_release_candidate_gate.py
scripts/run_individual_git_release_gate.sh
ra --root /tmp/research-assistant-final-release init
ra --root /tmp/research-assistant-final-release release-report
ra --root /tmp/research-assistant-final-release repository-hygiene check --strict
ra --root /tmp/research-assistant-final-release individual-git-release validation-local
ra --root /tmp/research-assistant-final-release individual-git-release fixture-rehearsal
ra --root /tmp/research-assistant-final-release individual-git-release performance --synthetic-count 100
ra --root /tmp/research-assistant-final-release individual-git-release performance --tier synthetic_git_1000 --synthetic-count 1000 --timeout-seconds 600
ra --root /tmp/research-assistant-final-release individual-git-release validation-report
ra --root /tmp/research-assistant-final-release individual-git-release gate-build
```

Run the release-candidate gate with Python 3.11.x. It writes
`dist/release_gate_evidence.json`, including the exact Python version, commands,
return codes, wall times, artifact path, and a fingerprint of release-relevant
source. After all commands pass, it refreshes and hash-validates
`dist/release_artifacts_manifest.json`. `ra release-report` warns when this evidence is missing and blocks when
it is failed, malformed, or stale. Any source change after the gate requires a
fresh run.

The command set is closed: static, fast, bounded, active full-suite, packaging,
wheel build, clean-install, and release smoke checks must all be present and
passing. A partial evidence file is rejected.

The external parser benchmark is separate because installed tools vary by
machine. It deliberately sets `CUDA_VISIBLE_DEVICES=-1`; its synthetic parser
scores are availability/regression diagnostics, not scientific extraction
certification.

The active test and coverage runners also set `CUDA_VISIBLE_DEVICES=-1` before
Python import. `scripts/run_tests.sh` partitions the same complete unit,
integration, and script inventory so each failure is attributable and bounded;
every partition must pass. No GPU behavior is part of this private v0.1 release
gate.

The performance commands are not optional bookkeeping for the release gate.
Run them before `validation-report` and `gate-build` so
`representative_workspace_performance` is recorded in the validation evidence.

Maintainers should also read `docs/maintainer_guide.md` before changing
release-gate, repository-hygiene, backup/restore, or workspace-merge behavior.

Release gates:
- package metadata and runtime diagnostics accept Python 3.11.x only;
- `ra --help` and `ra version` work after install;
- `ra init` is idempotent;
- `ra doctor` reports optional tool and offline status;
- `ra doctor --matrix`, `ra parser-tool-matrix`, and `ra parser-benchmark-smoke` explain parser readiness;
- `ra demo setup` and `ra demo run` complete in a fresh root;
- `ra workspace validate` returns no blockers for the demo root;
- `ra backup create`, `backup inspect`, restore dry-run, and confirmed restore into a fresh root work;
- `ra privacy status` shows offline defaults;
- `ra bounded-workflow diagnostic` creates a timeout artifact;
- `ra performance smoke --include-industrial-artifacts --include-backup --include-export` completes on a small synthetic corpus;
- `scripts/build_release_artifacts.sh` produces `dist/release_artifacts_manifest.json`;
- `ra release-artifacts validate` verifies the expected versioned wheel, sdist,
  final gate evidence, file inventory, sizes, and SHA256 values;
- `ra platform-status` matches `docs/platform_support.md`;
- `ra repository-hygiene check` reports no unsafe private/generated files for a shareable workspace;
- `ra repository-hygiene check --strict` catches local build/cache/private roots and secret-like fields;
- `ra workspace merge` dry-run and `--apply --confirm-merge` pass on sanitized fixture repositories;
- `ra workspace rebuild-derived` regenerates local derived reports after merge;
- `ra individual-git-release validation-report` distinguishes local substitutes from real external validation;
- `ra individual-git-release performance --tier synthetic_git_1000 --synthetic-count 1000` completes or records a concrete smaller supported tier;
- `ra individual-git-release gate-build` reports database/service/RBAC/UI as deferred future-platform items, not current release blockers;
- generated artifacts are review material and not accepted mathematical conclusions;
- known limitations are included in `ra release-report`.
- `ra release-report` validates passing evidence for the exact source tree;
- release notes and support instructions are present;
- unsupported platforms and deferred product capabilities are recorded as limitations rather than support claims.
