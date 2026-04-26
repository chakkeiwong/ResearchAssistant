# Release Checklist

Run these bounded checks before sending a release candidate to colleagues:

```bash
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/run_packaging_smoke.sh
scripts/build_release_artifacts.sh
scripts/run_clean_install_smoke.sh
scripts/run_release_smoke.sh
ra --root /tmp/research-assistant-final-release init
ra --root /tmp/research-assistant-final-release release-report
```

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
- generated artifacts are review material and not accepted mathematical conclusions;
- known limitations are included in `ra release-report`.
- release notes and support instructions are present;
- any unvalidated platform or human onboarding trial is recorded as a pilot limitation rather than broad support.
