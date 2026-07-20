# Release Notes 0.1.0

Date: 2026-07-20

## Release Scope

This is a limited pilot release candidate for researchers who want a private local `research-assistant` workspace with Git-based sharing. It is not a shared department server, shared database, live collaboration system, hosted UI, SSO/RBAC system, or default live LLM/provider release.

The supported release is one researcher using Linux/WSL with Python 3.11.x. Tagging and publication remain separate release-owner actions.

Current local validation status for this candidate:
- Linux/Python 3.11 source and disposable-workspace checks: recorded locally;
- Linux parser command smoke: recorded locally as diagnostic evidence;
- external MCP setup trial: accepted on 2026-05-03 using the sanitized
  external-agent stdio result in
  `docs/validation/local_mcp_h1_external_trial_result_2026-05-03.md`.

Do not treat synthetic fixtures or maintainer-machine parser smoke as scientific
extraction-accuracy evidence.

## Primary Install Path

Recommended local path:

```bash
python -m pip install research_assistant-0.1.0-py3-none-any.whl
ra version
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor
```

Developer fallback:

```bash
python -m pip install .
```

The maintainer should build artifacts with:

```bash
scripts/build_release_artifacts.sh
```

The artifact manifest is regenerated at `dist/release_artifacts_manifest.json` and includes SHA256 hashes. Build outputs under `dist/` are not committed to Git.

Artifact hashes are intentionally not copied into this versioned document:
they change whenever the source tree changes. Build the final wheel and sdist
with `scripts/build_release_artifacts.sh`, then use the generated
`dist/release_artifacts_manifest.json` as the authoritative checksum record.
The release gate and publication check validate that manifest against the files
actually present in `dist/`.

## Supported Platforms

- Validated locally on Linux/WSL2 with Python 3.11.15 on 2026-04-27.
- Plain Linux with Python 3.11.x is the intended Tier 1 target but should still run the release gate on the target machine.
- Linux and WSL2 with Python 3.11.x are the only supported release targets.
- Python 3.10 and Python 3.12+ are not supported by this release.
- Windows through WSL is the supported Windows path. Native Windows shell-script workflow is unvalidated.

## Validation Summary

Release gate commands for this candidate. Run the performance commands before
`validation-report` and `gate-build`; the gate expects representative workspace
performance evidence to be recorded alongside the local fixture evidence.

```bash
scripts/run_fast_tests.sh
scripts/run_bounded_tests.sh
PYTHONPATH=src python -m pytest tests/integration/test_individual_release_cli.py -q
ra --root /tmp/research-assistant-final-release individual-git-release validation-local
ra --root /tmp/research-assistant-final-release individual-git-release fixture-rehearsal
ra --root /tmp/research-assistant-final-release individual-git-release performance --synthetic-count 100
ra --root /tmp/research-assistant-final-release repository-hygiene check --strict
ra --root /tmp/research-assistant-final-release individual-git-release validation-report
ra --root /tmp/research-assistant-final-release individual-git-release gate-build
scripts/run_packaging_smoke.sh
scripts/build_release_artifacts.sh
env WHEEL_PATH=dist/research_assistant-0.1.0-py3-none-any.whl timeout 300 scripts/run_clean_install_smoke.sh
scripts/run_release_smoke.sh
ra --root /tmp/research-assistant-final-release release-report
```

The exact command results for the current candidate are recorded in `docs/plans/reset_memo_2026-04-26.md`.

Local evidence now includes a validation schema under `local_research/governance/individual_git_release/validation/`, deterministic Git-sharing fixture rehearsal, strict repository hygiene, explicit-wheel clean install smoke, Linux parser smoke, and synthetic representative workspace performance through `synthetic_git_1000`. Release-owner approval is required only before tagging or publication.

## Showcase: source-first NeuTra chapter audit

This release was exercised on a realistic research task: auditing a
DSGE/HMC monograph chapter built around *NeuTra-lizing Bad Geometry in
Hamiltonian Monte Carlo Using Neural Transport*.

In that workflow, the researcher used `research-assistant` to:
- create a private local workspace;
- ingest the NeuTra paper by arXiv ID;
- fetch the arXiv LaTeX source;
- inspect structured sections, equations, and citations from source rather
  than relying only on PDF heuristics;
- compare the paper's explicit claims with local code and chapter text;
- export reviewed context for downstream writing.

Representative commands:

```bash
ra --root /tmp/ra-neutra-audit init
ra --root /tmp/ra-neutra-audit ingest --arxiv-id 1903.03704 --query "NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport"
ra --root /tmp/ra-neutra-audit source-fetch --arxiv-id 1903.03704
ra --root /tmp/ra-neutra-audit find --query "NeuTra"
ra --root /tmp/ra-neutra-audit source-sections --paper-id paper_arxiv_1903_aa33312a
ra --root /tmp/ra-neutra-audit source-equations --paper-id paper_arxiv_1903_aa33312a
ra --root /tmp/ra-neutra-audit source-show --paper-id paper_arxiv_1903_aa33312a
```

What this showed in practice:
- source-first inspection is already useful for mathematical literature
  audits;
- structured source outputs make chapter/code verification easier than
  PDF-only review;
- human judgment is still required for interpretation and for related-work
  selection.

What it did not show:
- automatic survey writing;
- automatic mathematical certification;
- or reliable open-ended literature discovery without human review.

Release takeaway: `research-assistant` is already strong as a local,
source-grounded evidence tool for known-paper audits. It should currently be
presented that way, rather than as automatic literature intelligence.

## Git Sharing

Researchers share by exchanging Git repositories or workspace snapshots. The workflow is:

```bash
ra repository-hygiene check --strict
ra workspace merge --source /path/to/other/repo --target /path/to/my/repo
ra workspace merge --source /path/to/other/repo --target /path/to/my/repo --apply --confirm-merge
ra workspace rebuild-derived
```

See `docs/workflows/git_sharing_walkthrough.md`.

## Privacy

Default workflows are offline and provider-disabled. The demo, release-report, parser diagnostics, backup/restore checks, and synthetic performance smoke do not require sending papers or notes to external providers.

## Local MCP

Optional local MCP support is available through `research-assistant[mcp]` and
the `ra-mcp` stdio entrypoint. It is local-only, not a hosted service, shared
database, HTTP API, SSO/RBAC system, or live collaboration server.

The first MCP surface is read-only by default. Grant-bound explicit-ID arXiv
source intake can be run from the CLI after a bounded local grant is created,
and its output remains review material.

Current MCP limitations:
- offline pinned arXiv candidate-file planning is available, but live
  query-based arXiv discovery is not MCP-enabled;
- PDF batch policy checks are available, but PDF batch downloads are not
  enabled;
- review-write is a CLI-only confirmation prototype with proposal counts and
  expired-proposal cleanup; it is not exposed through MCP;
- live explicit-ID arXiv source intake passed bounded public-ID scale tests at
  25, 50, and 100 attempted records on 2026-05-03; this validates H2 source
  intake only, not query discovery or PDF downloads.

## Backup And Restore

Create a backup before relying on a workspace or changing install versions:

```bash
ra --root ~/research-assistant-workspace backup create
```

Restore defaults to dry-run. A real restore requires `--no-dry-run --confirm-restore`; overwriting existing files additionally requires `--allow-overwrite` and creates a safety backup by default.

## Known Limitations

- Generated derivations, experiments, synthesis, traceability, governance, and readiness reports are review material, not mathematical approval.
- Parser quality depends on local optional tools and source/PDF quality.
- Parser-tool availability and degradation are checked, but parser scientific accuracy is not certified.
- This release does not claim support for macOS or native Windows.
- Linux parser-tool smoke is diagnostic and does not certify scientific extraction accuracy.
- Git-sharing merge/import performance has been measured through `synthetic_git_1000` and does not certify real personal libraries.
- Local MCP external setup and live explicit-ID arXiv 25/50/100 source intake
  have bounded accepted evidence. Query discovery, PDF batch execution, and MCP
  review-write remain gated.
- Tagging and artifact publication require explicit release-owner approval.

See `docs/known_limitations.md` and `docs/support.md`.
