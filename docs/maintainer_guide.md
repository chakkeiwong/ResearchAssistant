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
- `src/research_assistant/survey/campaign_process.py`: pure source-first
  planning primitives. It validates the canonical `Paper -> SourceVersion ->
  Inspection -> Claim` snapshot and its caller-supplied coverage requirements,
  separates available evidence from access/omission work, and chooses a bounded
  next action. It never runs network, credential, PDF, or human-review actions.
- `src/research_assistant/survey/mission_plan.py`: read-only projection of the
  complete product workflow. It binds the current mission-control and
  next-action generation, exposes discovery through release stages, and never
  becomes mission authority.

## Supported And Historical Code

The active v0.1 contract is a local, single-user, Python 3.11 tool. Topic-only
missions may use the bounded credential-free OpenAlex metadata bootstrap;
explicit-seed source intake remains arXiv-first. OpenAlex-containing legacy
mission fixtures are still historical compatibility tests and do not authorize
credentials, source/PDF downloads, or unbounded provider work.

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

## Literature Survey Process

All public survey functions are topic-generic. Domain query profiles, coverage
matrices, and expected paper lists are regression fixtures only. Never add a
topic-name or vocabulary check that silently selects a specialized strategy.
If a survey needs domain-specific coverage cells, put them in that campaign's
validated snapshot; do not add them to `campaign_process.py`.

Every topic or explicit-seed mission can expose one operator-facing workflow
map:

```bash
scripts/ra-dev survey mission-plan --mission-root /path/to/mission
```

The command writes `mission_plan.json` beneath the mission root and is safe to
rerun as the mission advances. It performs no network, download, PDF,
credential, human-review, or claim-promotion action. `current_stage` is the
first incomplete stage; a blocked stage is an honest handoff, not a
completeness claim.

A selected topic mission must continue through the supported handoff rather
than through manually copied identifiers:

```bash
scripts/ra-dev survey continue-topic \
  --mission-root /path/to/selected-topic-mission \
  --out /path/to/fresh-explicit-seed-mission
```

`survey/topic_continuation.py` owns this transition. It replay-validates the
parent bootstrap authority, initializes the existing explicit-seed safe-local
supervisor with the exact selected identifiers, and writes
`topic_handoff.json` in the child. Parent and child roots must be disjoint.
The child keeps its own public-discovery confirmation; never copy the parent's
provider confirmation into it. The handoff is nomination provenance, not
source, technical, human-review, or release evidence.

Start a new survey with an explicit topic coverage contract and source
preflight rather than an unqualified high-citation crawl. The local process
planner is deterministic:

```bash
PYTHONPATH=src python3.11 -m research_assistant.cli survey process-plan \
  --snapshot /path/to/campaign_snapshot.json \
  --out /path/to/process-plan
```

The snapshot declares ordered `coverage_requirements`; each requirement has a
stable `cell_id`, human label, unique contiguous priority, and a
`direct_evidence_required` flag. Papers may reference only declared cells. The
planner prioritizes open must-cite risks and then unresolved cells in declared
order. It has no built-in RL, finance, card, medical, economics, or other
domain cell. A replacement source does not inherit technical support from the
unavailable paper.

The command is local and side-effect bounded. It does not claim completeness or
technical validity; those remain the existing source-inspection, safety-review,
claim-support, snowball, and hostile-review gates.

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

## Topic Discovery Strategies

The public topic bootstrap always loads
`src/research_assistant/survey/strategies/generic_topic.json`. The specialized
RL/finance profile lives in
`tests/fixtures/topic_seed_strategies/rl_financial_recommender.json`.
It is a named regression fixture and must not be activated by inspecting the
user's topic. The responsibilities are deliberately small:

- `topic_seed_strategy.py` validates and loads the declarative profile;
- `topic_seed_discovery.py` owns request budgeting, identity reconciliation,
  ranking, and bounded public-provider response handling. The generic topic
  profile is the only public default; domain profiles are explicit fixture data;
- `mission_state.py` owns mission-bound aggregate limits; and
- `orchestrate.py` binds the discovery result into the bootstrap artifacts.

To add an alias, keep the relevant term list unique and sorted. To add a query
layer, give it the next contiguous `priority`, use one of the validated
`purpose` and `sort` values, and keep the total number of strata within the
mission request budget. Unknown JSON fields fail validation by design.

Run the focused regression set after every profile or ranking change:

```bash
CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src python3.11 -m pytest -q \
  tests/unit/test_topic_seed_priority.py \
  tests/unit/test_cli_architecture.py
```

Inspect `descriptive.budget_consumption`, every `query_layers` status, identity
conflicts, and capped-frontier flags in the bootstrap outcome before using a
nomination. `candidate_status=metadata_nomination` and
`generic_topic_centrality_status=not_validated` are intentional. A selected
seed is metadata-only until its identity, topic fit, paper role, primary
technical source, source safety, and snowball evidence have been reviewed.
Citation counts and venue metrics are priority signals only; missing venue
metrics must stay `not_available`.

`centrality.py` owns the strict evidence bundle, hard-veto truth table,
deterministic assessment, and persisted-output replay validator.
`centrality_benchmark.py` is evaluator-only and must never be imported by
runtime selection. `topic_contract.py` owns topic scope and bounded generic
route planning; its behavior is included in the OpenAlex capability version.
`mission_plan.py` may project a replay-validated mission-local `centrality/`
artifact, but centrality must not become a prerequisite for source intake:
source inspection is required to construct centrality evidence.

The autonomous campaign is split by authority so a maintainer can change one
boundary without reading the entire workflow:

- `central_papers_observations.py` owns strict observation/capability schemas
  and the offline file adapter;
- `central_papers_capability.py` owns bounded OpenAlex graph expansion and arXiv
  source transport, but makes no topic-fit or centrality decision;
- `central_papers_evidence.py` owns technical-section selection, conservative
  topic/role inference, the six ledgers, omission risks, and evidence assembly;
- `central_papers.py` owns campaign contracts, checkpoint chains, resume/replay,
  snowball stop projection, reports, and terminal manifests.

Never move evaluator labels into observation fixtures or runtime modules, and
never infer a scholarly role from a discovery route. A provider-policy or
budget change requires a capability fingerprint update and a fresh output
root. Run the central-paper unit/CLI tests and the three-topic topic-input
benchmark after changing any of these four modules.

Run this focused set after changing any of those boundaries:

```bash
CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src python3.11 -m pytest -q \
  tests/unit/test_topic_contract.py \
  tests/unit/test_topic_seed_priority.py \
  tests/unit/test_centrality.py \
  tests/unit/test_snowball_round.py \
  tests/unit/test_centrality_benchmark.py \
  tests/unit/test_survey_mission_plan.py \
  tests/integration/test_centrality_cli.py \
  tests/integration/test_centrality_multitopic_benchmark.py \
  tests/integration/test_survey_mission_plan_cli.py
```

Start a fresh mission when a profile digest or aggregate budget changes. Do not
resume a mission into a different strategy and do not combine consumption from
multiple attempts as though each attempt reset the campaign ceiling.

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

## Literature Source Reconciliation

Topic discovery does not require a venue-metrics registry. The OpenAlex path
records citation counts and venue metrics as dated prioritization metadata; an
empty or absent registry is `not_available`, never zero and never a technical
evidence gate.

When a selected paper cannot be fetched, use
`research_assistant.survey.source_selection.select_available_sources()` (or
`build_source_selection_ledger()`). It keeps available selected candidates,
chooses a deterministic same-stratum replacement where possible, then uses a
shared declared purpose or stable nomination rank. It records unavailable
selections, fallback reasons, and unreplaced gaps. Availability is not claim
support.

Use `choose_preferred_source_version()` for multiple lawful copies. It prefers
published/version-of-record material, then accepted manuscripts, then the
latest lawful preprint, and records alternate versions and date mismatches.

## Multi-provider seed discovery

`survey seed-papers` is the retrieval-only boundary. Keep its modules separate:

- `seed_paper_providers.py` owns exact-host transport, strict provider response
  parsing, provider status, request/record/byte caps, and the raw observation
  bundle;
- `seed_papers.py` owns identity fusion, topic evidence, provider-local ranks,
  dispositions, replay, and the seed report/manifest;
- `topic_contract.py` owns bounded generic route planning.

`seed_continuation.py` owns replay-validated transfer into an explicit-seed
mission. It consumes only selected IDs whose rows are resolved and not
quarantined; it must never infer extra papers. `seed_handoff.json` binds the
on-disk parent campaign/report/manifest and child mission artifacts. Keep live
transport diagnostics in `scripts/run_seed_papers_live_smoke.py`; do not mix
live calls into the offline benchmark.

The runtime provider set is OpenAlex, Crossref, and Semantic Scholar. Google
Scholar scraping is intentionally unsupported because it has no stable public
API contract. Do not add a citation-count aggregate: provider counts and ranks
are incomparable and remain descriptive priority signals. Do not move
`must_find`, `must_reject`, case names, or fixture paths into runtime modules.

Run the focused seed gate after changing these boundaries:

```bash
CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src python3.11 -m pytest -q \
  tests/unit/test_seed_papers.py \
  tests/integration/test_seed_papers_cli.py \
  tests/integration/test_seed_papers_benchmark.py \
  tests/unit/test_cli_architecture.py
```

Regenerate the evaluator-owned raw-provider result with:

```bash
CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=src python3.11 \
  scripts/run_seed_papers_benchmark.py \
  --result-path docs/validation/robust_seed_papers_benchmark_result_2026-07-22.json
```

The six-topic benchmark starts from raw provider envelopes, not prepared
centrality evidence. It supports only the declared fixture retrieval gate;
passing it does not establish arbitrary-topic recall or scholarly centrality.
## Cooperative document boundary

The scholarly document workflow is owned by
`src/research_assistant/survey/document/`:

- `contracts.py` validates caller-facing evidence and document contracts;
- `planner.py` groups supported claims by mechanism and records reader-state
  transitions;
- `writer.py` defines the writer protocol and the scaffold-only baseline;
- `projection.py` projects replay-valid central campaigns or hostile-reviewed
  packets into the public document evidence contract;
- `dynaremcp_adapter.py` owns the optional subprocess/JSON boundary;
- `orchestrator.py` writes append-only run artifacts and final status.

`survey/literature_review.py` composes the existing central-paper campaign,
document projection, synthesis, optional LaTeX rendering, and optional
DynareMCP QA. It does not introduce a second discovery state machine.

Do not import DynareMCP Python modules into ResearchAssistant. The integration
must remain a CLI/file boundary so both projects are independently installable.
DynareMCP findings are structural candidates based on caller-supplied facts;
they are not source truth, claim review, or publication approval.

The public CLI is registered in `cli_registration/survey.py`, routed in
`cli_actions/survey.py`, and injected by `cli.py`. Keep new document logic out
of those three files. When changing the parser, review and update the explicit
CLI inventory and fingerprint in `tests/unit/test_cli_architecture.py`.

Run focused checks with:

```bash
pytest -q tests/unit/test_scholarly_document.py \
  tests/integration/test_scholarly_document_cli.py \
  tests/unit/test_cli_architecture.py
```

The cross-repository integration test invokes DynareMCP through a subprocess;
it must never add the DynareMCP source tree to the ResearchAssistant process.
