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

## Module Map

- `src/research_assistant/cli.py`: command-line entry point, command handlers,
  and parser registration. Keep `main(argv)` stable because integration tests
  call it directly.
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

Local fixture evidence can support limited pilot readiness. Broad release still
requires real fresh-reader onboarding, real macOS validation, real minimal
parser-tool machine validation, release-owner tag approval, and release-owner
publication approval.

Local substitutes must remain visibly separate from real external validation.
Do not mark manual gates as passed unless they actually happened.

## Common Validation Commands

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_industrial_platform_cli.py -q
timeout 120 scripts/run_fast_tests.sh
timeout 180 scripts/run_bounded_tests.sh
timeout 300 scripts/build_release_artifacts.sh
env WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh
GATE_ROOT=/tmp/research-assistant-maintainer-gate timeout 300 scripts/run_individual_git_release_gate.sh
git diff --check
git status --short --ignored
```

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
