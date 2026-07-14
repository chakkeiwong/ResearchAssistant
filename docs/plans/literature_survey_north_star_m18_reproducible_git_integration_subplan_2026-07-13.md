# M18 Reproducible Git Integration Subplan

Date: `2026-07-14`
Status: `EXECUTION_READY_PENDING_MATERIAL_PLAN_REVIEW`
Milestone: `M18_reproducible_git_integration`
Closes: `G1_reproducible_git_integration`

## Phase Objective

Convert the cumulative reviewed M16+M17 dirty-tree local alpha into a
non-destructive identified Git commit, build and install its wheel without
network access, and reproduce the explicit-seed and idea/topic local workflows
from an isolated clone without reading the dirty source checkout or absorbing
unrelated user work.

This phase establishes local Git/install reproducibility only. It does not run
providers, retrieve sources, make human decisions, push, release, or establish
scientific or product readiness.

## Active Governance And Authority

The current repository `AGENTS.md` supersedes the legacy setup requirement for
hash-bound natural-language approval tokens and mandatory review of every
procedural artifact. The migration is recorded in
`docs/plans/literature_survey_north_star_policy_migration_2026-07-14.md`.

The user's repeated `execute` and crash-resume requests authorize this reviewed
trusted-local, non-destructive M18 campaign: exact staging, local commits,
local `/tmp` clones and environments, wheel build/install, and CPU-only checks.
No push, public release, destructive/history-rewriting action, credentials,
network/provider/source action, paid or expanded compute, privacy change,
product/scientific direction change, or genuine human decision is authorized.

## Entry Conditions Inherited From M17

All entry conditions are satisfied before plan review:

| Authority | SHA-256 / value | Status |
| --- | --- | --- |
| Baseline Git commit | `1b36af06efc7e1c2c086934cd8800691ae8a6da7` | `main`, ahead of `origin/main` by one |
| M17 result | `027cb69cbac7052d26acd5e3c64585b0f1d4549fa2832c7791502f9e6e9ff9bb` | `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING` |
| M17 primary code verdict | `ef34e1ac7fbcfccd6d014c94c71a5922822ae71ed0b5d4f27887de43be9d4a2d` | Claude Opus/max `AGREE` |
| M17 closure verdict | `ebd7bd7fc460eb92a057c48a791823a4bd17068645da3cd1c8f4620cb8d2982d` | fresh Codex fallback `AGREE`; second Claude export was policy-rejected |
| M17 successor manifest file | `46fd3d4e444fc5fd43b9d10f05dce110980c75bd13b98b345ae459a5b4277571` | `1,671` rows |
| M17 successor payload | `163f9ca026e18903d219690ed88647c1bc26ae7f45cd0752aa05a9cb891d485f` | replay passed, zero mismatch |
| M17 replay file | `774eebfd5325a97025fca4a41d0e0fcd0fa04b943771888b18397a94b45ee72e` | all `1,671` rows |
| M17 pre-edit snapshot manifest | `752b3d72c50d7e3eb45ba47a19528308e0c69faa5692bb49a6dedf85c1d5c340` | all 10 paths replayed |
| M17 run manifest | `e3aff4e7e64ec60833214d0cf5af48830f0a5a9a6066583c76bac7a9bae34930` | CPU-only; no Git/live action in M17 |

M17 final evidence contains all `1,137` Phase 10 inventory members (`1,136`
files and one intentional absolute-target symlink), all `38` direct logical
rows, six JUnit records totaling `2,117` passing tests, and a `13/13`
persistent matrix. These values are dirty-tree engineering evidence, not this
phase's clean-install conclusion.

At entry the Git index is empty. Eight tracked files differ from `HEAD`:
`src/research_assistant/cli.py` and
`tests/integration/test_cli_commands.py` are cumulative survey-program paths;
the six paths under Protected Unrelated Work are excluded. No submodules exist.
Git LFS is unavailable and unused. `pyproject.toml` is the only packaging
manifest; there is no lockfile, `MANIFEST.in`, or extra setup metadata.

## Research Intent Ledger

| Field | M18 contract |
| --- | --- |
| Main question | Can Git alone reproduce the cumulative local alpha without untracked or dirty-checkout dependencies? |
| Candidate/mechanism | Exact 1,684-path payload plus exact active controls, non-destructive commit, isolated clone, wheel install, and local gate replay. |
| Expected failure mode | A required file is omitted, unrelated work enters the commit, the inherited CLI calls an excluded dirty dependency, or the environment imports an older installed package. |
| Promotion criterion | An identified candidate commit builds/installs locally and passes all declared local gates from an isolated clone with verified wheel origins and no dirty-tree read. |
| Promotion veto | Missing payload; protected path staged; wrong commit; observed dirty source import/read; symlink dereference; failed required test; observed external network/GPU use; destructive Git action. |
| Continuation veto | The exact integration set cannot be separated, a required dependency cannot be committed lawfully, both full attempts are exhausted, or a repair changes scope/product semantics. |
| Repair trigger | Dependency-closure miss, wheel/import failure, unexpected test-generation write, candidate-only compatibility failure, or material independent `REVISE`. |
| Explanatory only | Commit size, path count, runtime, log size, wheel size, and total test count outside exact frozen suites. |
| Must not be concluded | Live behavior, source support, human review, scientific correctness, literature completeness, provider reliability, product/release readiness, or north-star completion. |

## Evidence Contract

| Field | Contract |
| --- | --- |
| Engineering question | Can the M17-passed local alpha be reproduced from an identified Git commit and installed wheel without the dirty workspace? |
| Baseline/comparator | M17 successor-manifest candidate on baseline commit `1b36af0...`, plus immutable historical M16 snapshot. |
| Primary pass criterion | Identified isolated clone builds and installs a wheel, resolves all RA imports under the fresh venv, and passes the declared topic/seed, cumulative, script, CLI, unit, payload-replay, and static gates. |
| Hard vetoes | Any protected unrelated path in the commit; omitted required path; wrong commit; observed dirty-checkout import/read; absolute negative-fixture target dereference; observed external network/GPU use; failed/errored/skipped required gate; destructive Git action. |
| Explanatory diagnostics | Included/excluded counts, commit/wheel size, wall times, and non-frozen aggregate counts. |
| Not concluded | Network/provider behavior, citation recall, source retrieval, human review, scientific validity, completeness, product or release readiness. |
| Preserving artifacts | Payload/dependency/stage manifests, candidate commit, isolated run root and logs, JUnit, wheel/origin manifest, payload replay, result, terminal review, closeout commit, and refreshed M19 subplan. |

## Default And Assumption Audit

| Choice | Provenance | Justification | Failure mode | Early diagnostic | Status |
| --- | --- | --- | --- | --- | --- |
| Baseline `1b36af0...` supplies unchanged tracked package bytes | Git and M17 manifest | M16/M17 changed only an exact overlay | Baseline module absent or incompatible | Import graph plus isolated focused tests | Baseline |
| M17 successor rows seed the payload | M17 closure `AGREE` | It is the latest reviewed dirty-tree authority | Final controls or test inputs omitted | Literal-read and documentation-reference audits | Reviewed baseline, repaired in M18 |
| Remove four optional arXiv plan-file CLI lines only in committed candidate | M17 pre-edit snapshot versus `HEAD` signatures | The CLI otherwise calls parameters implemented only in excluded dirty `arxiv_batch.py` | Removal damages survey CLI or hides a required M16 feature | Candidate compile/import, arXiv parse assertion, focused/full CLI | Integration repair |
| Add 13 canonical test inputs | Isolated preflight failures and literal-read audit | Selected tests require them | Broad diagnostic roots accidentally staged | Exact paths plus 12-test script replay, including the portability regression | Required dependency |
| Normalize regular-file modes to Git semantics | Git tree mode model plus independent review | Git preserves only the executable bit for regular files | Clean clones falsely fail against worktree-only `0444`/`0600` modes | Preserve `source_mode_octal`; replay Git tree `100644`/`100755` plus filesystem executable class after an actual commit and fresh clone | Required integration repair |
| `/tmp` venv uses `--system-site-packages` | Existing local pytest/build toolchain | Avoids network/package download | Older installed RA masks wheel | Force-install wheel and assert every RA origin lies under venv | Convenience, guarded |
| Test counts outside frozen suites are descriptive | Candidate excludes unrelated arXiv tests | Legitimate baseline reversion changes aggregate count | Count mismatch misclassified as regression | Zero failure/error/skip is primary | Required interpretation |
| Candidate and closeout commits, with at most one repair child | Git provenance and two-attempt budget | Code authority must be tested before close evidence exists | Retry requires rewind or absorbs undeclared work | Fail-closed exact descendant-repair transaction; closeout is a docs/evidence-only child of the final code authority | Reviewed local default |

## Skeptical Plan Audit

Audit scope: wrong baseline, proxy promotion, missing stop conditions, unfair
comparison, stale context, environment mismatch, hidden dependency, unrelated
work overlap, and artifacts that would not answer the question.

Findings and repairs before execution:

1. The old shell required special Git approval wording that current policy
   retires. The migration note now makes ordinary local authority explicit.
2. The M17 manifest omitted final mutable controls by design. M18 separately
   enumerates exact controls without placing them in a self-hash cycle.
3. Three SurveyBench tests required prompt inputs outside M17. Exact paths were
   added and `22` focused tests passed in a disposable clone.
4. The exact Phase 7 script test required the 10-file canonical Phase 6 packet.
   Those files were added; the focused repair passed. The inherited suite
   passed `11/11` before the later portability repair; the current frozen suite
   contains `12` tests and must pass from the disposable committed clone.
5. M17 inherited four optional arXiv plan-file CLI lines whose implementation
   exists only in excluded unrelated `arxiv_batch.py`. The candidate removes
   exactly those lines without modifying worktree bytes. Candidate compile,
   import, arXiv parser compatibility, `65` M17 tests, and `8` focused CLI tests
   passed in the disposable clone.
6. The machine has an older installed `research_assistant`. The authoritative
   lane force-installs the candidate wheel and asserts import/console origins.
7. The canonical negative symlink points into the dirty checkout. Payload
   replay uses `lstat`/`readlink`; `strace` must show no open of its target.
8. A single commit cannot contain evidence generated after testing itself.
   Candidate and docs/evidence closeout commits are separated without amend.
9. M17 recorded 436 regular files as `0600` and 14 as `0444`, while Git tree
   mode stores non-executable regular files as `100644`; checkout read/write
   bits remain umask-dependent. The payload preserves original values as
   `source_mode_octal`, validates them against M17 before normalization, and
   binds canonical Git-replay permission classes into the digest. Replay checks
   Git index mode, filesystem executable class, bytes, size, and kind rather
   than claiming ambient read/write bits. An actual disposable commit and
   fresh-clone replay must pass before the real index is touched.
10. The original retry prose required a descendant repair while the staging
    helper accepted only the baseline. Attempt 2 now requires a fixed
    `repair_attempt02.json`: the failed attempt-1 commit, one permitted local
    failure class, unchanged campaign-boundary booleans, failure and focused
    check evidence, and unique sorted exact replacement rows with hash, size,
    kind, and Git mode. `stage-repair` verifies the direct-parent relation,
    original stage authority, clean index, protected hashes, and exact staged
    set before one index transaction. It cannot delete, rewind, or restage the
    original payload generically. Both stage actions reject active merge,
    rebase, cherry-pick, revert, bisect, or sequencer state; post-commit audit
    requires exactly one parent at each permitted lineage edge.
11. Frozen Phase 10 CLI records contain absolute paths rooted at the historical
    checkout. The M18 test-only repair validates their canonical suffix and
    artifact-specific decision-set shape, then reads solely below the supplied
    Phase 10 output root. A regression with a different root makes any original
    checkout read fail. Historical JSON remains byte-identical, and the exact
    script gate plus trace must include this regression.
12. Every authoritative pytest gate runs as `<attempt-venv>/bin/python -m
    pytest`; no ambient `pytest` executable is permitted. Exact suite paths and
    external JUnit destinations are frozen below.
13. Disposable exact staging exposed 17 trailing-blank-line diagnostics in
    M17-pinned historical evidence and SurveyBench replay fixtures. Rewriting
    those bytes would violate the reviewed payload. `audit-stage` and
    `audit-candidate` therefore requires exact equality with the sorted
    17-record path/line/diagnostic set and zero findings outside it; the stage
    record separately binds each affected blob hash and OID. On attempt 2 the
    same action revalidates the original direct child, the exact single repair
    child, both stage authorities, zero repair-only whitespace findings, and the
    unchanged cumulative 17-record set.

Disposition: `PASSED_AFTER_REPAIR_PENDING_MATERIAL_PLAN_REVIEW`. Disposable
committed-clone replay is diagnostic only; authoritative evidence starts after
plan agreement.

## Exact Payload And Classification

`docs/validation/literature_survey_m18_2026-07-14/payload_manifest.json`
contains `1,684` unique sorted repository paths with canonical payload SHA-256
`0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318`:

- all `1,671` M17 successor rows;
- 3 canonical SurveyBench prompt inputs;
- the 10-file canonical Phase 6 packet required by the exact script gate; and
- a candidate-only `src/research_assistant/cli.py` row with exactly four
  unsupported optional arXiv-plan lines removed; and
- a test-only Phase 10 row that rebases frozen path reads to clone-local output
  without changing historical JSON or product behavior.

Each row binds both the validated source-worktree mode and the Git-replay mode.
All `1,683` regular files are non-executable and therefore bind Git tree mode
`100644`; the one symlink binds `120000` and retains exact target text.
Filesystem replay verifies executable-bit class but does not claim
umask-dependent read/write bits. Source-mode provenance remains 14 `0444`, 436
`0600`, 1,233 `0644`, and one symlink `0777`.

`docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py`
verifies M17 authority, protected hashes, path canonicality, symlink-parent
safety, payload bytes, candidate CLI surgery, and an empty index. It creates
Git objects before one lock-protected index transaction and never rewrites
product or payload worktree bytes; it creates only the reviewed
`stage_record.json` control file. Its separate `stage-repair` action is usable
only from the declared failed direct child and stages the exact bounded repair
overlay plus its manifest and stage record.

The helper requires byte equality between canonical payload recomputation and
the reviewed on-disk manifest before staging. `stage_record.json` binds path,
Git mode, SHA-256, size, and Git blob OID for every staged payload/control row;
it explicitly excludes only its own recursive blob description.

Active/final controls are separately enumerated in the payload manifest's
`control_paths`. Their exact current bytes are staged by path after material
plan review; mutable controls are not falsely claimed as part of the M17
payload digest. The generated `stage_record.json` records the final staged set.

## Protected Unrelated Work

These current worktree bytes must remain unchanged and absent from both commits:

| Path | Current SHA-256 |
| --- | --- |
| `.gitignore` | `29344e75c13a1a6d4e9b1bb653d106156cafb02ee61b1c99701c9a32f5ec9074` |
| `docs/benchmark_plan.md` | `2395402f907a6d163979e37fa62d6975109c5e9ccfcb7322962b3a0a2e00a033` |
| `src/research_assistant/ingest/arxiv_batch.py` | `cda93366f622a8c52ed809570ad40b8062c309e29d8c9ab47aa8b971466152be` |
| `src/research_assistant/source/arxiv_source.py` | `5ae7f4bb1aea9ab7d999f8e915760f92ae0e2fffcc31af4cf3b3e4db780576d8` |
| `tests/integration/test_arxiv_batch_intake.py` | `bb9975537e134322449341bc1941a7582d714fc95b93fb9c86ce1beee712ce80` |
| `tests/unit/test_arxiv_source.py` | `21bfb200b0a75d9e4bd7b536bff2d6b953b2866fc59a17e196b368443f716f9d` |

Also excluded: the 901 unselected M17 diagnostic paths; crash-interrupted logs;
superseded persistent matrices/JUnit attempts; caches; compiled bytecode;
environments; credentials; `.claude_reviews`; unrelated historical plans and
validation roots; and every unlisted path. No wildcard or directory-wide stage
is allowed.

## Required Artifacts

- This reviewed execution subplan and plan verdict.
- `payload_manifest.json`, `dependency_audit.json`, and
  `prepare_integration.py`.
- `stage_record.json` and exact candidate commit.
- Disposable actual-commit/fresh-clone replay record with zero payload mismatch
  and unchanged protected baseline bytes.
- If and only if attempt 2 is used: `repair_attempt02.json`,
  `repair_stage_record.json`, focused repair evidence, and the exact descendant
  repair commit.
- Versioned isolated attempt root under `/tmp`, retained through closeout.
- Wheel SHA-256, install/import/console-origin manifest, Git/OS/Python/tool
  manifest, payload replay, symlink/no-dirty-read audit, JUnit, and logs.
- M18 result with decision table and post-run red team.
- Terminal result-review bundle/verdict.
- Docs/evidence-only closeout commit and exact candidate-to-closeout diff.
- Refreshed M19 subplan bound to the actual code-authority commit and observed
  environment; M19 remains non-executable pending its live boundary.
- Updated milestone JSON, master, runbook, ledger, handoff, and reset memo.

## Compute, Attempt, And Output Budget

- Hardware: CPU only; every Python/test command sets
  `CUDA_VISIBLE_DEVICES=-1`. No GPU probe or use.
- Network: none; build/install set `PIP_NO_INDEX=1` and use only local bytes.
- Full candidate attempts: at most `2`.
- Total M18 authoritative wall-time budget: `120` minutes.
- Attempt 1 root:
  `/tmp/ra_m18_candidate_<candidate-commit>_attempt01/`.
- A repair retry uses exactly one new direct descendant commit and
  `/tmp/ra_m18_candidate_<new-commit>_attempt02/`; attempt 1 is preserved.
- No automatic retry for a semantic test failure. A localized dependency,
  packaging, harness, or serialization repair must be recorded first in the
  fixed attempt-2 manifest and pass focused checks.

## Exact Execution Procedure

### 1. Pre-Mutation Gate

1. Parse all JSON and compile `prepare_integration.py` with CPU-only Python.
2. Rerun `prepare_integration.py plan`; require payload count `1,684` and
   payload SHA-256 `0d225f29...`.
3. Require `git rev-parse HEAD` equals the baseline, index empty, protected
   hashes exact, no submodule, and no unexplained tracked overlap.
4. In a disposable baseline clone, copy the exact reviewed source overlay and
   controls, run the same `stage` action, commit, clone that commit with
   `--no-hardlinks --no-local`, and require payload replay `1,684/1,684`, zero
   mismatch. Verify the six protected paths retain baseline committed bytes.
5. Exercise `stage-repair` fail-closed mechanics on a disposable candidate
   using one synthetic documentation-row overlay; require the exact three-path
   diff (row, repair manifest, repair stage record), direct-parent binding, and
   a passing repair-aware `audit-candidate`; require rejection of an incorrect
   parent or protected path.
6. Require material plan `VERDICT: AGREE` or record reviewer unavailability
   under current advisory-review policy after local checks pass.

### 2. Exact Candidate Commit

Run only:

```bash
CUDA_VISIBLE_DEVICES=-1 python \
  docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py stage
CUDA_VISIBLE_DEVICES=-1 python \
  docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py audit-stage
git diff --cached --name-status
git commit -m "Integrate literature survey local alpha"
CUDA_VISIBLE_DEVICES=-1 python \
  docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py audit-candidate
```

The helper uses `git hash-object`/`git update-index`; it does not run `git add`
or alter worktree bytes. Verify immediately that protected paths are absent
from `HEAD^..HEAD`, the six protected worktree hashes remain exact, and the
index is empty after commit. `audit-stage` replays every index row and accepts
only the exact 17 frozen whitespace records. `audit-candidate` replays the
commit tree, payload, protected exclusion, and the same 17 records across
`BASELINE..C`. Do not amend.

### 3. Isolated Clone And Wheel

For candidate commit `C`, require a previously absent attempt root, then run:

```bash
git clone --no-hardlinks --no-local . /tmp/ra_m18_candidate_C_attempt01/repo
git -C /tmp/ra_m18_candidate_C_attempt01/repo rev-parse HEAD
CUDA_VISIBLE_DEVICES=-1 python -m venv --system-site-packages \
  /tmp/ra_m18_candidate_C_attempt01/venv
env -u PYTHONPATH CUDA_VISIBLE_DEVICES=-1 PIP_NO_INDEX=1 \
  /tmp/ra_m18_candidate_C_attempt01/venv/bin/python -m build \
  --wheel --no-isolation \
  --outdir /tmp/ra_m18_candidate_C_attempt01/wheelhouse \
  /tmp/ra_m18_candidate_C_attempt01/repo
env -u PYTHONPATH CUDA_VISIBLE_DEVICES=-1 PIP_NO_INDEX=1 \
  /tmp/ra_m18_candidate_C_attempt01/venv/bin/python -m pip install \
  --no-index --no-deps --force-reinstall \
  /tmp/ra_m18_candidate_C_attempt01/wheelhouse/research_assistant-*.whl
```

Assert `research_assistant`, `research_assistant.cli`, and
`research_assistant.survey.bootstrap` resolve under the attempt venv, not the
dirty checkout or host system package. Assert the `ra` console script uses the
attempt venv and exposes `survey run-public-source-workflow` help.

### 4. Authoritative Local Gates

Run from the isolated clone using the attempt venv, `env -u PYTHONPATH`,
`CUDA_VISIBLE_DEVICES=-1`, and logs/JUnit outside the clone:

1. M18 payload replay using `prepare_integration.py replay --target <clone>`:
   `1,684/1,684`, zero mismatch.
2. Candidate compile/import and arXiv decoupling assertion.
3. Focused M17: exact `65` pass from
   `tests/unit/test_literature_survey_m17.py`.
4. Cumulative M16+M17 exact `846` pass from these ten unit paths:
   `test_literature_survey_m16.py`, `test_literature_survey_m16_phase2.py`
   through `test_literature_survey_m16_phase9.py`, and
   `test_literature_survey_m17.py`, all under `tests/unit/`.
5. M17 persistent validation script: exact `13/13` pass in a fresh `/tmp`
   output root.
6. Exact `12` pass from these five modules under `tests/scripts/`:
   `test_literature_survey_benchmark_feedback_summary.py`,
   `test_literature_survey_m16_phase10_offline_e2e.py`,
   `test_literature_survey_phase5_command_validation.py`,
   `test_literature_survey_phase6_boundary_validation.py`, and
   `test_literature_survey_phase7_validation_harness.py`.
7. Full `tests/unit`: zero failures/errors/skips; total is descriptive because
   excluded unrelated arXiv tests revert to `HEAD`.
8. Full `tests/integration/test_cli_commands.py`: exact `125` pass.
9. Baseline `tests/integration/test_arxiv_batch_intake.py`: zero
   failures/errors/skips and explicit parser compatibility; count descriptive.
10. `test_surveybench_restricted_trial.py` plus
    `test_surveybench_agent_trial.py`: zero failures/errors/skips.
11. JSON/JUnit parse, repeat `audit-candidate` with its exact 17-record frozen
    whitespace set, path uniqueness, package/wheel member audit, and
    protected-exclusion audit. Do not apply an unqualified zero-whitespace gate
    to the M17-pinned historical evidence.
12. Topic-only default-unavailable CLI and explicit-seed CLI smokes through the
    installed `ra`, each writing only under the attempt root.
13. Run every authoritative command inside the platform's network-restricted
    sandbox with no provider/source action. Use `strace -f -e
    trace=file,network` around payload replay, installed CLI, frozen Phase 10
    validation, and its path-rebasing regression; require no access to the dirty
    repository, no `open*` of the historical symlink target, and no socket,
    `connect`, or `sendto` syscall in those targeted traces. M18 does not infer
    universal absence of attempted socket calls in untraced suites.

Every pytest command has this exact shape, with `<V>` the attempt venv, `<R>`
the isolated clone, and `<A>` the preserved attempt root:

```bash
env -u PYTHONPATH CUDA_VISIBLE_DEVICES=-1 \
  <V>/bin/python -m pytest -q <exact-path-list> \
  --junitxml=<A>/junit/<gate>.xml
```

No ambient `pytest` executable is allowed. Use the exact path lists above for
focused, cumulative, scripts, unit, CLI, arXiv, and the two SurveyBench gates.
Run the persistent matrix only as:

```bash
env -u PYTHONPATH CUDA_VISIBLE_DEVICES=-1 \
  <V>/bin/python \
  <R>/scripts/literature_survey_m17_local_validation.py \
  --output <A>/persistent_matrix
```

Capture `git status --porcelain=v2 --untracked-files=all` before and after the
gates. Clone-local script output roots are expected disposable writes, not
committed inputs and not canonical M18 evidence; record and exclude them. Run
the exact 12-test script gate untraced through venv Python, then separately
trace the frozen-candidate Phase 10 test and its path-rebasing regression.
Require zero dirty-checkout paths and zero socket/connect/sendto syscalls in the
targeted trace. Preserve the failed full-file and network-only trace attempts as
harness diagnostics: ptrace terminated the multiprocessing-heavy suite before
JUnit, so they are not pass evidence and are not retried.

On failure, preserve the attempt and classify it as exactly one of:
`dependency_closure` (a required local file was omitted), `packaging` (the
unchanged candidate was not assembled/installed correctly), `harness` (the
validation command or path was wrong), `serialization` (evidence could not be
written/read without changing its meaning), or non-retryable. Only the first
four permit attempt 2, with evidence that target, product semantics, test
assertions, hardware, network boundary, and budget remain unchanged. A product
implementation failure, semantic test failure, invalid target/artifact, or
changed scientific/product conclusion is a continuation veto unless concrete
evidence shows it belongs solely to one of those four local engineering classes.

If attempt 2 is justified, first create
`docs/validation/literature_survey_m18_2026-07-14/repair_attempt02.json` with
schema `ra-literature-survey-m18-repair-attempt-v1`. It must bind attempt `2`,
the full failed attempt-1 commit, exactly one failure class from
`dependency_closure`, `packaging`, `harness`, or `serialization`, nonempty
   failure-evidence path/hash rows, nonempty successful focused checks with
   artifact hashes, a hash-bound supervisor audit of the exact repair paths and
   unchanged scope, all five unchanged
campaign-boundary booleans, and unique sorted exact repair rows containing only
`kind`, Git `mode_octal`, `path`, `sha256`, and `size_bytes`. Then run only:

```bash
CUDA_VISIBLE_DEVICES=-1 python \
  docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py stage-repair
git diff --cached --name-status
git commit -m "Repair literature survey local integration"
CUDA_VISIBLE_DEVICES=-1 python \
  docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py audit-candidate
```

The helper requires `HEAD` to equal the declared failed candidate and that
candidate to be a direct child of the M18 baseline with the original stage
record. It rejects protected/reserved/hidden paths, deletions, unbound bytes,
changed campaign boundaries, a dirty index, and any staged path outside the
declared rows plus the two repair records. The new commit must be a direct child
of attempt 1. No reset, restore, amend, or other rewind is permitted. The entire
authoritative gate suite then runs once from the fresh attempt-2 clone.
`audit-candidate` accepts no deeper chain: it revalidates the original
candidate against `stage_record.json`, binds the repair child to its committed
manifest and `repair_stage_record.json`, checks every repair path/mode/OID/hash/
size, rejects protected deltas, requires no repair-only whitespace finding, and
requires the cumulative finding set to remain exactly the frozen 17 records.
Both the initial candidate and repair child must have exactly one parent; merge
commits are rejected even if their first-parent and resulting tree appear valid.
Before commit, inspect the exact repair-only cached diff and require no
whitespace finding in those newly introduced paths; the frozen 17 historical
exceptions remain in the parent and are not part of the repair overlay.

Before `stage-repair`, Codex must inspect the actual diff and write the declared
supervisor audit only if every repair row is necessary for the classified
failure and leaves target, data, product semantics, hardware, network boundary,
and budget unchanged. The helper verifies that audit plus every referenced
failure/focused-check artifact as a regular non-symlink file below the preserved
attempt-1 root with exact SHA-256. A self-attested manifest alone is insufficient.

### 5. Result, Review, And Closeout Commit

After an authoritative pass:

1. Copy only canonical logs/JUnit/JSON summaries into the M18 validation root.
2. Write the M18 result, decision table, run manifest, and post-run red team.
3. Define `C` as the passing attempt-1 candidate or its single passing repair
   child. Refresh M19 with `C`, environment, exact inherited
   transport surfaces, and its still-ungranted live boundary.
4. Request one terminal material review of code/evidence/claims. Fix material
   local issues within the attempt budget; reviewer-only procedural objections
   do not override local evidence.
5. Stage by exact path only the result, selected M18 evidence, terminal review,
   refreshed M19, and updated controls. Verify the candidate-to-closeout diff
   contains no product/test/source change and no protected path.
6. Commit non-interactively as
   `Document reproducible literature survey integration`. Do not amend or push.
7. In a fresh local clone of the closeout commit, replay the candidate payload,
   verify the parent/code-authority relationship, and rerun import origin plus
   installed CLI help/topic smoke. The closeout commit contains candidate/parent
   provenance and an explicit self-hash nonclaim. Record its actual hash only in
   `/tmp/ra_m18_closeout_record.json` after commit; no tracked artifact claims
   to contain its own commit hash, and no third self-reference commit is created.

## Required Reviews

- One material M18 plan review before staging. Claude Opus/max is preferred
  when policy permits; a fresh Codex read-only reviewer is the fallback.
- One terminal result review after candidate validation and before closeout.
- Reviewers are advisory and read-only. They cannot authorize Git push,
  network/source/human/scientific/product/release boundaries.
- A fixable material finding triggers visible repair and focused rerun. Stop
  after five review rounds on the same material blocker, but the execution
  attempt budget remains two.

## Forbidden Claims And Actions

- No wildcard/bulk staging, `git add -A`, directory-wide add, amend, reset,
  restore, clean, stash, rebase, force, history rewrite, deletion, or push.
- Do not change or stage any protected unrelated path.
- Do not let the isolated lane import from the dirty checkout, inherited
  `PYTHONPATH`, editable install, or older host `research_assistant`.
- Do not dereference or rewrite the intentional absolute symlink; it is
  historical negative evidence, not a portable runtime fixture.
- Do not add diagnostics merely to inflate evidence or stage generated caches,
  environments, credentials, wheel binaries, or raw trace logs containing
  irrelevant host paths.
- Do not treat test counts, commit size, or a successful install as live,
  scientific, product, release, or mission-completion evidence.
- Do not run network/provider/source/PDF/full-text/model-worker/GPU actions.

## Exact Next-Phase Handoff Conditions

M19 becomes the active planning lane only when:

1. Candidate code commit `C` contains exactly the reviewed integration payload
   and controls, plus only the declared exact repair overlay if attempt 2 was
   needed; it excludes all protected/unlisted work and has no missing dependency.
2. The isolated wheel install and every required M18 gate pass without failure,
   error, or skip; origin and targeted traces show no dirty-source read or
   symlink-target dereference; the network-restricted lane and targeted traces
   show no observed external network or GPU use.
3. M18 result and terminal review support only local Git/install
   reproducibility.
4. A docs/evidence-only closeout child commit contains the result/review/handoff
   and no product/test/protected delta.
5. M19 is refreshed with actual candidate/closeout provenance, environment,
   transport surfaces, hashes, no-network hardening work, attempt budget, and
   exact live-approval boundary.
6. M19 remains `DO_NOT_EXECUTE_LIVE` until its material plan converges and the
   user authorizes the actual frozen live attempt.

## Stop Conditions

Stop with a blocker result when the exact integration set cannot be separated,
a protected path changes unexpectedly, a destructive/history-rewriting action
would be required, a dependency cannot lawfully be committed, a semantic
product change outside M18 is needed, the second full attempt fails, the
120-minute budget is exhausted, criteria would need post-result change, or the
same material review blocker fails to converge after five rounds.

Do not stop merely because a first candidate exposes a missing file, packaging
issue, local import leak, harness path error, or serialization defect that can
be repaired inside the unchanged payload question and remaining budget.

## End-Of-Phase Sequence

Run local gates; write the M18 result/close record; refresh M19 from actual
artifacts; review M19 for consistency, correctness, feasibility, artifact
coverage, inherited conditions, and boundary safety as part of the terminal
M18 review; update milestone JSON, master, runbook, ledger, handoff, and reset
memo; create the docs/evidence-only closeout commit; stop before live action if
M19 lacks its explicit runtime authority.
