# Release Checklist

Run these bounded checks before sending a release candidate to colleagues:

```bash
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
scripts/run_release_smoke.sh
scripts/run_packaging_smoke.sh
```

Release gates:
- `ra --help` and `ra version` work after install;
- `ra init` is idempotent;
- `ra doctor` reports optional tool and offline status;
- `ra demo setup` and `ra demo run` complete in a fresh root;
- `ra workspace validate` returns no blockers for the demo root;
- `ra backup create`, `backup inspect`, and restore dry-run work;
- `ra privacy status` shows offline defaults;
- `ra bounded-workflow diagnostic` creates a timeout artifact;
- `ra performance smoke` completes on a small synthetic corpus;
- generated artifacts are review material and not accepted mathematical conclusions;
- known limitations are included in `ra release-report`.
