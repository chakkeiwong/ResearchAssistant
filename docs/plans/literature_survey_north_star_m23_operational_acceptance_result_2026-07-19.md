# M23 Operational Acceptance And North-Star Close Result

Date: `2026-07-19`
Status: `PENDING_VERSIONED_CLEAN_CHECKOUT_CLOSE_AFTER_ROUND3_REVISE`
Plan: `docs/plans/literature_survey_north_star_m23_acceptance_and_operational_closeout_subplan_2026-07-13.md`
Terminal-review candidate root: `docs/validation/literature_survey_north_star_m23_operational_acceptance_2026-07-19_r7/`

## Outcome

The fresh `_r7` root passes the offline M23 operational matrix after the two
Round 2 predicate repairs and the external build-staging repair. All nine
predeclared cases pass; deterministic replay passes both in the source process
and in the installed wheel from `/tmp` with `PYTHONPATH` unset; the wheel embeds
the exact current M23 module; all captured stderr files are empty; and the
capability/documentation surfaces preserve the scientific limitations.

The wheel was built from a fresh external staging copy of `pyproject.toml`,
`README.md`, and `src/`. The runner did not use or mutate the inherited
repository `build/` scratch tree. Every installed command ran from
`/tmp/ra-m23-operator-3d82pi6p`, and the imported package came from the fresh
virtual environment's `site-packages`.

Fresh read-only Review Round 3 returned `REVISE`: `_r7` proves a dirty-worktree
operational pass, but the current commit does not contain the supporting
runtime, tests, scripts, active plans/results/reviews, and compact M22 evidence.
`_r7` is therefore not final terminal evidence.

## Case Results

| Case | Result |
| --- | --- |
| `install_and_command_discovery` | Passed; package `research-assistant`, version `0.1.0`, required help boundaries, external cwd, and isolated import all verified |
| `topic_confirmation_stop` | Passed with the exact unconfirmed arXiv-only boundary |
| `topic_unavailable_stop` | Passed with honest `terminal_blocked_bootstrap_unavailable` behavior |
| `explicit_seed_local_skeleton` | Passed without provider or source dispatch |
| `unchanged_resume` | Passed with valid ancestry, unchanged gate/state, zero transitions, and no prose promotion |
| `qualitative_assessment_command` | Passed with `claim_support_allowed=false` and `ready_for_prose=false` |
| `m22_report_replay` | Passed all nine M22 cases while exposing unavailable forward citations, 50 open identifier-bearing rows, and 195 open identifier-free units |
| `stale_or_corrupt_rejection` | Passed; copied mutation rejected as `derived_artifact_replay_mismatch` |
| `documentation_capability_consistency` | Passed against completed-state master/reset documents and active limitations |

## Repair Record

1. The first root failed before the matrix because install inherited source-path
   state and produced no installed distribution or `ra` script.
2. `_r2` exposed a false import predicate and installed replay's module-relative
   retained-evidence lookup.
3. `_r3` passed encoded cases but ran installed commands beneath the repository,
   contrary to the external-cwd contract.
4. `_r4` passed the repaired matrix. The affected gate exposed 14 stale
   integration fixtures that supplied historical OpenAlex authority against
   active arXiv-only defaults; the fixtures were narrowed without removing
   separate optional-provider coverage.
5. `_r5` passed completed-state replay, but fallback Review Round 1 found that
   replay trusted stored parsed JSON and aggregate projections.
6. `_r6` strengthened derived replay, but fallback Review Round 2 found three
   weak case predicates: installed identity/help, unchanged resume, and explicit
   M22 limitation reporting.
7. Those predicates and false-pass tests were repaired. The expanded suite then
   exposed reuse of a permission-contaminated repository `build/` directory.
   Wheel construction now uses a fresh external staging tree for every attempt;
   a two-build regression proves distinct staging and no repository-build
   mutation. Fresh `_r7` contains all repairs.
8. Fresh fallback Review Round 3 found that `_r7`'s dirty-worktree success does
   not establish versioned clean-checkout reproducibility. The master/reset
   accomplished claim was withdrawn; M23 now generates its M22 replay root
   inside each acceptance root; and the exact Git integration/clean-checkout
   subplan is active.

All prior roots remain preserved and are not relabeled successful final
evidence.

## Verification

- `_r7` classification: `M23_OPERATIONAL_ACCEPTANCE_PASSED`;
- exact acceptance cases: `9/9` passed;
- focused M23 suite: `11 passed`;
- exact affected M16/M17/M20/M22/M23/CLI command:
  `262 passed, 77 deselected`;
- compile checks: passed;
- all `_r7` JSON artifacts parse: passed;
- all command stderr files empty: passed;
- installed `_r7` replay from `/tmp` with `PYTHONPATH` unset: `passed`;
- current source and wheel-embedded M23 module SHA-256 equality:
  `926df6f8af8087a8c7d66262f7322d510203b7c14c5233640ae05994428b5b97`;
- network dispatch: `false`;
- credential access: `false`;
- PDF fallback: `false`;
- deliberate CPU-only environment: `CUDA_VISIBLE_DEVICES=-1`;
- observed platform: Linux WSL2, Python `3.11.14`;
- run wall time: `5.406698` seconds;
- `git diff --check`: passed before packet refresh.

## Exact Evidence Hashes

| Artifact | SHA-256 |
| --- | --- |
| wheel | `311d7b5b62b3fc677786f8a7f63e2a123beac6a2b058e61184202b548e4356ba` |
| terminal result | `49fc9e76dcb68604408f6937c102bae3ab1a5952da75fe0f70f1dc1c1b4e693b` |
| case results | `831697e02fd928da51a6725f85bf66269029fbbfcef8eae2492b8fb5169d5fb9` |
| offline replay | `3d19d8dc975f20c5bc91debb20b1dbbd891f97c68242c752f17ea5716bd50699` |
| run manifest | `4fd9d18deecff839a886199617e4d9b5c72b6bab7b3e834ecab7812c7eb8941e` |
| command ledger | `a230fafbe0ad99aadbaa821d198609e741577201c66ae4b7c0a7fcecaee8b304` |
| capability matrix | `872b426de8f9c2c9cacb065bdd6f2213392734c7af5f720b1c95b6d15a9ecb9f` |
| documentation report | `aa08188c6fca5cebbf6186dd03957f58c46996561205fc1e44f4e68fc4309aa4` |
| artifact inventory | `faf819737499d3eb3297acc0b9ad227eb05ab7c77200ac44881e209541bdc7af` |

## Decision Table

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Preserve `_r7` as a dirty-worktree operational pass; do not close M23 | Operational cases and affected regressions passed, but the versioning/clean-checkout completion criterion failed | Untracked-runtime and clean-checkout veto fired in Round 3 | Exact compact evidence/include closure must still be committed and reproduced | Execute the versioned clean-checkout close subplan after Git authorization | Literature completeness, claim truth, live topic quality, prose/publication readiness, product or release readiness |

## Inference Status

| Evidence class | Status |
| --- | --- |
| Hard veto screen | Passed for the declared local operational scope |
| Statistically supported ranking | Not applicable; no stochastic candidates are ranked |
| Descriptive-only differences | Wall time, artifact size, and platform identity are descriptive |
| Default readiness | Active local arXiv-only defaults are operationally consistent; no broad product default claim |
| Next evidence needed | Terminal review for this scope; separate programs for live topic quality, broader sources, forward coverage, claim promotion, cross-platform support, or release |

## Post-Run Red Team

The strongest engineering alternative explanation was that wheel success
depended on source-checkout state: first through cwd/import leakage and later
through inherited repository build scratch. `_r7` runs installed commands from
`/tmp`, removes `PYTHONPATH`, imports from the fresh virtualenv, and builds the
wheel from a distinct external staging tree. The source and wheel M23 module
hashes are identical.

The weakest scientific evidence remains coverage, not operational behavior:
forward citations are unavailable, 50 identifier-bearing rows have title
context only, 195 identifier-free units remain unresolved, and publication or
retraction status is not comprehensively checked. Those limitations prevent
scientific or publication promotion but do not invalidate M23's operational
question.

## Boundaries

The result can establish local offline installability, installed command
behavior, deterministic M22 replay, tamper rejection, and documentation
consistency. It cannot establish literature completeness, scientific truth,
live topic-discovery quality, provider reliability, publication safety,
publication-ready prose, autonomous expert judgment, human usability,
cross-platform support, product readiness, or release readiness.

## Review Provenance

Claude review was attempted through the approved compact read-only gate, but
the environment rejected repository-content export to the external service.
The call was not retried or routed around. Fresh Codex fallback Round 1 and
Round 2 returned `REVISE`; both findings and their repairs are preserved in
`docs/reviews/literature_survey_m23_terminal_fallback_review_round1_2026-07-19.md`
and
`docs/reviews/literature_survey_m23_terminal_fallback_review_round2_2026-07-19.md`.
Fresh fallback Review Round 3 returned `REVISE` on the unversioned
dirty-worktree dependency. The verdict is preserved in
`docs/reviews/literature_survey_m23_terminal_fallback_review_round3_2026-07-19.md`.
The active next plan is
`docs/plans/literature_survey_north_star_m23_versioned_clean_checkout_close_subplan_2026-07-19.md`.
