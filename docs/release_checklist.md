# Release Checklist

Run these bounded checks before sending a release candidate to colleagues:

```bash
scripts/ra-agent fast-tests
scripts/ra-agent focused-tests
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/ra-agent pytest tests/integration/test_individual_release_cli.py -q
scripts/run_packaging_smoke.sh
scripts/build_release_artifacts.sh
WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl scripts/run_clean_install_smoke.sh
scripts/run_release_smoke.sh
scripts/run_individual_git_release_gate.sh
ra --root /tmp/research-assistant-final-release init
ra --root /tmp/research-assistant-final-release release-report
ra --root /tmp/research-assistant-final-release repository-hygiene check --strict
ra --root /tmp/research-assistant-final-release individual-git-release validation-substitutes
ra --root /tmp/research-assistant-final-release individual-git-release fixture-rehearsal
ra --root /tmp/research-assistant-final-release individual-git-release performance --synthetic-count 100
ra --root /tmp/research-assistant-final-release individual-git-release performance --tier synthetic_git_1000 --synthetic-count 1000 --timeout-seconds 600
ra --root /tmp/research-assistant-final-release individual-git-release validation-report
ra --root /tmp/research-assistant-final-release individual-git-release gate-build
```

The performance commands are not optional bookkeeping for the release gate.
Run them before `validation-report` and `gate-build` so
`representative_workspace_performance` is recorded in the validation evidence.

Maintainers should also read `docs/maintainer_guide.md` before changing
release-gate, repository-hygiene, backup/restore, or workspace-merge behavior.

Release gates:
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
- release notes and support instructions are present;
- any unvalidated platform or human onboarding trial is recorded as a pilot limitation rather than broad support.
