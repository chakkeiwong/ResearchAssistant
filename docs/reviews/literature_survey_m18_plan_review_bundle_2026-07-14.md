# M18 Reproducible Git Integration Material Plan Review Bundle

Date: `2026-07-14`
Status: `ROUND4_READY_FOR_FRESH_READ_ONLY_REVIEW`
Reviewer class: fresh Codex fallback after Claude export was policy-rejected

## Role Contract

Codex root is supervisor/executor. You are a fresh read-only reviewer. You may
passively inspect the listed repository files with read/search tools. Do not
edit files, execute project code, invoke any `prepare_integration.py` action,
compile, run tests, run Git commands, launch agents, or change state. Do not
authorize push, release, network/source/provider, human-decision, scientific,
product, privacy, credential, funding, or GPU boundaries.

The round-1 Codex reviewer returned useful findings but then ran the helper
`plan` action and compile checks despite its role. It was interrupted and is
disqualified from the converged verdict. Review the current packet afresh; do
not inherit round 1's verdict. The compliant round-2 reviewer found one
material retry-audit defect; that finding and its visible repair are included
below. Round 3 accepted the content-binding repair but found that first-parent
checks did not exclude merge commits; round 4 is confined to that final lineage
repair.

## Exact Question

Is the repaired M18 plan correct, feasible, path-complete, non-destructive, and
capable of establishing only local Git/wheel/isolated-clone reproducibility
without absorbing six protected unrelated worktree paths or reading the dirty
checkout? Does its one-child repair design remain fail-closed, and do its
evidence claims stop at what the planned gates can establish?

## Review Surface

Read these exact files only as needed:

1. Plan:
   `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_subplan_2026-07-13.md`
   - objective/authority/entry conditions: lines 8-61;
   - intent, evidence, defaults, skeptical audit: lines 63-166;
   - payload, protected work, artifacts, budget: lines 168-261;
   - stage/commit/clone/wheel/gates/repair: lines 263-449;
   - result, review, nonclaims, handoff, stops: lines 451-540.
2. Staging/replay helper:
   `docs/validation/literature_survey_m18_2026-07-14/prepare_integration.py`
   - exact suites, whitespace set, controls, protected hashes: symbols at
     lines 34, 46, 54, 95, and 136;
   - canonical payload and generated controls: `_payload_manifest`,
     `_write_plan_artifacts`, `_reviewed_payload_manifest`;
   - exact stage and commit audits: `_stage`, `_audit_stage`,
     `_audit_candidate_commit`;
   - fail-closed repair: `_repair_row`, `_stage_repair`.
3. Generated payload:
   `docs/validation/literature_survey_m18_2026-07-14/payload_manifest.json`.
4. Dependency/mode/test audit:
   `docs/validation/literature_survey_m18_2026-07-14/dependency_audit.json`.
5. Diagnostic-only actual-commit proof:
   `docs/validation/literature_survey_m18_2026-07-14/disposable_preflight_record.json`.
6. Historical round-1 findings and role violation:
   `docs/reviews/literature_survey_m18_plan_review_verdict_2026-07-14.md`.
7. Round-2 material finding:
   `docs/reviews/literature_survey_m18_plan_review_verdict_round2_2026-07-14.md`.
8. Round-3 single-parent finding:
   `docs/reviews/literature_survey_m18_plan_review_verdict_round3_2026-07-14.md`.
9. Active governance migration:
   `docs/plans/literature_survey_north_star_policy_migration_2026-07-14.md`.

Out of scope: rereviewing all 1,684 payload members individually, redoing M17
semantic review, executing any command, evaluating live/provider/source
behavior, or deciding M19 execution.

## Frozen State And Hashes

- Real repository baseline:
  `1b36af06efc7e1c2c086934cd8800691ae8a6da7`.
- Real branch: `main`, one commit ahead of `origin/main`.
- Real Git index: empty. No real M18 commit, push, network/provider/source,
  GPU, release, or credential action has occurred.
- Plan SHA-256:
  `2d07094a60e6379598e1d48bfee32386498090aca0e78dff0ecf727a672df672`.
- Helper SHA-256:
  `bbb799f92835ff1eb3695d2601e92c7be883bdeb81a0b9d7f5c4ac2709c1a223`.
- Payload file SHA-256:
  `caaa7291729958755a11bddabe8470afa1d98d16c726fdacd3244511f68343e6`.
- Canonical payload digest:
  `0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318`.
- Payload: 1,684 sorted unique paths: all 1,671 M17 rows, 13 exact test
  inputs, candidate CLI decoupling, and the Phase 10 test portability repair.
- Dependency audit SHA-256:
  `2814512556d88178b2336961d67353661a48c7c8a47a16df459151eab2d90ceb`.
- Disposable preflight record SHA-256:
  `82402781806c55af938d866f341c4594046f78302e6944e844c06c1e5a826594`.
- Historical round-1 record SHA-256:
  `870d3bf89b0566151863b5025906fa7ce661d1bbe8d8f68fe6ec75efa599a1c8`.
- Round-2 verdict SHA-256:
  `3348b9ffc2bd62dc171fbcca0e3b2c494e0008060ff980692f4e216b6ee484cd`.
- Round-3 verdict SHA-256:
  `304cbfcdd7b797575ef110e28158b87eb4ecf9aafac613a7de627c7de98f35b4`.
- Policy migration SHA-256:
  `54dfc3d9f9456909dc3fb8c2ec2009e785a4aa7c71609712f7ed0eb1d6817e5d`.
- Exact controls: 40 paths after adding the separate round-4 verdict path;
  their final bytes are bound atomically by the later `stage_record.json` and
  are intentionally outside the payload digest to avoid a self-hash cycle.

## Round-1 Repairs

1. Git modes: preserve `source_mode_octal`; normalize regular files to Git
   permission classes; replay tree/index mode and executable-bit class instead
   of umask-dependent read/write bits.
2. Exact staging: canonical recomputation must equal the reviewed manifest;
   every non-self row is bound by path, mode, SHA-256, size, and blob OID;
   audit permits exactly 17 frozen historical whitespace diagnostics and no
   others.
3. Attempt 2: `stage-repair` requires a direct-child failed candidate, exact
   repair rows, hashed failure/focused-check/supervisor evidence, unchanged
   boundaries, an empty index, and exact three-part stage coverage. It rejects
   protected/reserved paths and wrong parents.
4. Dirty-checkout leak: the Phase 10 test validates frozen absolute suffixes
   but rebases reads to the supplied clone-local output. A regression makes
   original-checkout reads fail.
5. Interpreter/suites: ten cumulative unit paths and five script paths are
   frozen; every pytest gate uses the attempt venv's `python -m pytest`; the
   script suite is 12 tests.
6. Closeout self-reference: tracked closeout evidence records candidate/parent
   provenance and a self-hash nonclaim; actual closeout hash is post-commit
   `/tmp` evidence only.
7. Trace scope: all authoritative commands run in the platform's
   network-restricted sandbox. Full suites use untraced JUnit. Targeted syscall
   traces cover payload replay, installed CLI smokes, and path-sensitive Phase
   10 tests. No universal absence-of-attempted-socket claim is made for
   untraced suites.

## Round-2 Repair

Round 2 found that the original `audit-candidate` accepted only a direct child
of the baseline, so a valid repair child could never pass post-commit audit.
The helper now uses one lineage-aware `audit-candidate` action:

- a direct baseline child is revalidated against its original
  `stage_record.json` exactly as before;
- exactly one repair child is accepted only when its grandparent is the
  baseline and its parent independently passes the original-candidate audit;
- committed `repair_attempt02.json` and `repair_stage_record.json` must bind
  that exact parent, failure class, unchanged boundary set, evidence-reference
  schemas, sorted repair rows, exact stage paths, and manifest SHA-256;
- every repair row is checked against committed Git mode, blob OID, SHA-256,
  size, and the committed repair manifest;
- protected deltas, deeper descendants, extra/missing paths, repair-only
  whitespace findings, and any cumulative whitespace set other than the frozen
  17 records fail closed.

Focused disposable proof with the updated helper:

- valid child `ee0f5fb4465fb9cd646b2b5f4fb7577bbf0643d6`: passed,
  1,724 final paths, one repair row, 17 frozen findings;
- deeper child `0f53d8516800aa46aae1750bbbc26a7c07def753`: rejected at
  the single-repair-child lineage gate;
- tampered-record sibling `e154b20eef0daa236ea3f163f31b3accda7e83d4`:
  rejected because the commit path set differed from stage authority;
- undeclared-extra-path sibling `7c3619175c3fef0c883abd0c054da15c3be6474d`:
  rejected for the same exact-path-set mismatch.

## Round-3 Repair

Round 3 found that first-parent notation did not prove an exact single-parent
lineage. The helper now:

- resolves each permitted lineage edge through `git rev-list --parents -n 1`
  and rejects any commit with zero or more than one parent;
- requires the initial candidate's sole parent to equal the baseline and the
  repair child's sole parent to equal the independently validated initial
  candidate;
- rejects active `MERGE_HEAD`, cherry-pick, revert, rebase, sequencer, or bisect
  state before either initial or repair staging.

Focused proof with the updated helper:

- the valid single-parent repair child still passes;
- synthetic initial merge `fe622b488ddea850c5dce59b7cf09a41e6eac52f`
  with baseline first parent and a second distinct parent is rejected by
  `_single_parent`;
- synthetic repair merge `3d7ed6cdca8199aa9f3884231203ea00b1b3b2e4`
  with the original candidate first parent and a second distinct parent is
  rejected by `_single_parent`;
- a disposable baseline clone with `.git/MERGE_HEAD` is rejected by
  `_require_no_git_operation` before payload or staging work.

## Disposable Proof

The diagnostic proof used an actual disposable commit and a separate fresh
clone. It is not the real candidate and does not consume an authoritative
attempt.

- Candidate `c2614804fac8e0325dcb90328405a1ffd9ff5077` is a direct child of the
  real baseline with 1,721 exact committed paths and no protected delta.
- Candidate audit passed with the exact 17 frozen whitespace records.
- Payload replay passed 1,684/1,684 with zero mismatch.
- Wheel built with `PIP_NO_INDEX=1`; SHA-256
  `cf451adb51618708a21d07ac6c12e539f8a3875e15c164a4e056759fb74678ac`.
- All 48 imported `research_assistant` modules and the `ra` console script
  resolved under the fresh venv.
- Exact five-module script suite: 12 passed; JUnit SHA-256
  `08905d2a8fc7d672e26070f0964b99c26aa47ad2d541e37637056911bd5930e9`.
- Phase 10 portability tests: 2 passed; trace showed zero dirty-root paths and
  zero `socket`, `connect`, or `sendto` calls.
- Payload trace accessed the intentional absolute symlink through
  `lstat`/`readlink`; it did not open the target.
- Installed topic-only and explicit-seed CLI smokes exited 0 but both stopped
  at their recorded public-discovery confirmation gates with confirmation
  false and no provider/source action.
- Synthetic repair child `ee0f5fb4465fb9cd646b2b5f4fb7577bbf0643d6`
  committed exactly the repair row, manifest, and stage record. Wrong-parent
  and protected `.gitignore` probes both failed before staging and left their
  indexes empty.

Two attempted full-suite syscall traces terminated before JUnit. They are
diagnostic-only, intentionally not cited as pass evidence, and do not support a
universal syscall claim.

## Questions To Challenge

1. Can any unlisted or protected byte enter either the initial or repair commit
   despite the manifest equality, stage record, and post-commit audits?
2. Are source-mode provenance and Git checkout semantics now correctly
   separated for regular files and the one symlink?
3. Does the direct-descendant repair transaction work without rewind while
   preventing a generic second integration commit or semantic scope change?
4. Do the isolated wheel-origin, payload replay, targeted trace, pre/post status,
   and exact-suite gates answer local reproducibility without relying on a
   proxy count?
5. Are the abandoned full-suite traces and sandbox restriction described
   honestly, with no unsupported no-network/no-dirty-read inference?
6. Can the docs/evidence closeout child accidentally change code/test/product
   bytes or claim its own hash?
7. Are attempt budget, repair triggers, continuation vetoes, stop conditions,
   and M19 boundary handoff coherent under the active academic governance?

## Pass Criteria

Return `AGREE` only if no material correctness, feasibility, dependency,
partial-index, dirty-read, install-origin, retry, evidence, stop-condition, or
boundary defect remains. Treat formatting or optional hardening separately from
material blockers.

Return `REVISE` for a material issue and cite the exact file plus line/symbol.
Findings must distinguish candidate rejection from invalidation of the M18
question and must not require superseded approval-token ceremony.

## Requested Verdict

Findings first. End with exactly one line:

```text
VERDICT: AGREE
```

or

```text
VERDICT: REVISE
```
