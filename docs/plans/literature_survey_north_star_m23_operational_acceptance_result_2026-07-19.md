# M23 Operational Acceptance And North-Star Close Result

Date: `2026-07-19`
Status: `ACCOMPLISHED_WITHIN_RECORDED_LOCAL_EXPLORATORY_SCOPE`
Plan: `docs/plans/literature_survey_north_star_m23_acceptance_and_operational_closeout_subplan_2026-07-13.md`
Authoritative clean-checkout root: `/tmp/research-assistant-m23-authoritative-acceptance/`

## Outcome

The authoritative clean-checkout root passes the offline M23 operational
matrix from commit `6149818ab25791ca01c9d84fbbbb580f1e121841`. All nine
predeclared cases pass; deterministic replay passes both in the source process
and in the installed wheel from `/tmp` with `PYTHONPATH` unset; the wheel embeds
the exact current M23 module; all captured stderr files are empty; and the
capability/documentation surfaces preserve the scientific limitations.

The wheel was built from a fresh external staging copy of `pyproject.toml`,
`README.md`, and `src/`. The runner did not use or mutate the inherited
repository `build/` scratch tree. Every installed command ran from
`/tmp/ra-m23-operator-1wkh0chl`, and the imported package came from the fresh
virtual environment's `site-packages`.

Fresh read-only Review Round 3 returned `REVISE` on `_r7` because the supporting
state was not versioned. The exact 101-path closure was then committed as
`6149818ab25791ca01c9d84fbbbb580f1e121841`, tree
`60467239d7ccfd5f035049f6ca6913a880d3ba23`. A detached clean checkout passed
the complete gate and generated the authoritative acceptance root. Fresh
fallback Review Round 4 returned `AGREE`; `_r7` remains historical rather than
being relabeled final evidence.

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
9. The corrected include manifest contains 101 exact paths, including the
   retained-source catching test and a narrow `.gitattributes` exemption that
   preserves verbatim upstream TeX whitespace. The real integration commit has
   the reviewed tree exactly. Its detached clean checkout passed all gates and
   terminal Review Round 4 returned `AGREE`.

All prior roots remain preserved and are not relabeled successful final
evidence.

## Verification

- authoritative classification: `M23_OPERATIONAL_ACCEPTANCE_PASSED`;
- exact acceptance cases: `9/9` passed;
- focused M22/M23 suite: `23 passed`;
- exact affected M16/M17/M20/M22/M23/CLI command:
  `263 passed, 77 deselected`;
- compile checks: passed;
- all `75` authoritative JSON artifacts parse: passed;
- all command stderr files empty: passed;
- installed authoritative replay from `/tmp` with `PYTHONPATH` unset: `passed`;
- current source and wheel-embedded M23 module SHA-256 equality:
  `14173a0f5dedfa9c7e087dfa1f880ad245fab7038ab6dd15ed6b75176903bc6b`;
- Git commit: `6149818ab25791ca01c9d84fbbbb580f1e121841`;
- Git tree: `60467239d7ccfd5f035049f6ca6913a880d3ba23`;
- clean-checkout dirty flag: `false`;
- network dispatch: `false`;
- credential access: `false`;
- PDF fallback: `false`;
- deliberate CPU-only environment: `CUDA_VISIBLE_DEVICES=-1`;
- observed platform: Linux WSL2, Python `3.11.14`;
- run wall time: `6.741677` seconds;
- `git diff --check`: passed.

## Exact Evidence Hashes

| Artifact | SHA-256 |
| --- | --- |
| wheel | `fdd58293702371e4f85efe1f667e5310e597073d35ca3a945b6b831d1cbe7899` |
| terminal result | `ed316d62ff267794be3663fa521240a195c3b4b5710aa7ff06ef251bc135a712` |
| case results | `7d6371d54ead28c9a5c4b2be2704b91918883244c157798ad61beb67274743cc` |
| offline replay | `9642387064bcb46215bff91c96bb7a499f22d8c459c6b7d83d0fe45698aee612` |
| run manifest | `e2b0cfc6ecbdca83ae8ad5770495bcb84d697584d4afca92c1f752dfb5c91f5f` |
| command ledger | `37c00668d5769311f3bc5bf385aa24299ce27658d90e64b5ae47cc3dbeab5f0c` |
| capability matrix | `872b426de8f9c2c9cacb065bdd6f2213392734c7af5f720b1c95b6d15a9ecb9f` |
| documentation report at integration commit | `b8941c0b081c4932b1790a9ac1a860667a948bbee8e7897b1ad6601a8c093a3a` |
| artifact inventory | `03ed356898925a41df0f5d63e03cd49c841ab4ebe105a93fca18c2e12ddeed3d` |

## Decision Table

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Close M23 and the M17-M23 program within recorded local exploratory scope | The exact versioned clean checkout passed all operational, replay, regression, documentation, and review criteria | No declared continuation veto remains | Scientific coverage and publication limitations remain open but are outside the operational close criterion | Preserve the close record; start a separate scoped program for any broader scientific or product claim | Literature completeness, claim truth, live topic quality, prose/publication readiness, product or release readiness |

## Inference Status

| Evidence class | Status |
| --- | --- |
| Hard veto screen | Passed for the declared local operational scope |
| Statistically supported ranking | Not applicable; no stochastic candidates are ranked |
| Descriptive-only differences | Wall time, artifact size, and platform identity are descriptive |
| Default readiness | Active local arXiv-only defaults are operationally consistent; no broad product default claim |
| Next evidence needed | None for this scoped program; separate programs for live topic quality, broader sources, forward coverage, claim promotion, cross-platform support, or release |

## Post-Run Red Team

The strongest engineering alternative explanation was that wheel success
depended on source-checkout state: first through cwd/import leakage and later
through inherited repository build scratch. The authoritative clean-checkout
run executes installed commands from `/tmp`, removes `PYTHONPATH`, imports from
the fresh virtualenv, and builds the wheel from a distinct external staging
tree. The source and wheel M23 module hashes are identical.

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
The exact versioned-close repair then passed. Fresh fallback Review Round 4
returned `AGREE`; its verdict is preserved in
`docs/reviews/literature_survey_m23_terminal_fallback_review_round4_2026-07-19.md`.
The close record is
`docs/plans/literature_survey_north_star_m23_versioned_clean_checkout_close_result_2026-07-19.md`.
