# M17 Idea And Topic Bootstrap Result

Date: `2026-07-14`
Status: `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`
Milestone: `M17_idea_topic_bootstrap`

## Outcome

The local engineering target is implemented. The public command now accepts a
topic without an initial paper seed:

```bash
ra survey run-public-source-workflow --topic "<topic>" --out <mission-dir>
```

Omitting `--seed` creates a distinct topic-input mission. It does not reinterpret
the topic as a title or identifier, and an explicit `--seed ""` remains invalid.
Existing explicit-seed missions retain the M16 V2 schema family and behavior.

The primary Claude Opus/max code/semantics review returned `AGREE` with no
material finding. A subsequent supervisor audit found that the first successor
manifest bound the Phase 10 inventory record but not all 1,137 evidence members
listed by it. That artifact-coverage gap was repaired locally, and a fresh
Codex read-only fallback review returned `AGREE` with no material finding.

## Claimed Target And Quantity Produced

| Item | Result |
| --- | --- |
| Claimed target | Start the one-command workflow from an idea/topic without a fabricated paper identity, persist confirmation before bootstrap, distinguish closed outcomes, and expose derived effective seeds only through selected immutable authority. |
| Quantity produced | Sibling topic fingerprint V3, GENESIS V2, mission-contract V3, mission-control V3, public-result V3, a deterministic capability contract, and an at-most-once immutable bootstrap journal/set/pointer state machine. |
| Relationship | Correct for the deterministic local engineering contract. Live provider quality and clean-checkout reproducibility remain untested. |
| Baseline preserved | Explicit-seed M16 V2 vectors, resume, migration, confirmation, CLI, and terminal behavior. |

## Implementation

M17 changed these preexisting product paths, each captured before edit in the
immutable snapshot:

| Path | Entry SHA-256 | Current SHA-256 |
| --- | --- | --- |
| `src/research_assistant/cli.py` | `50e1369dcde963e87f5fecc15ad31b791f83576cc27ae1b89a37b3b164f3509f` | `f29025639bf48b56dcf90979f2a9d24b63876deda4c23600d497c67fa054137c` |
| `src/research_assistant/survey/mission_state.py` | `5c731c88fe55969d7e4af12155681a72ca691dcb80d42e6d4ca4610c3591a00b` | `7303218e913df02d9bda7574fde74b5379931ce80e10e144dc03b4363bf11a2f` |
| `src/research_assistant/survey/orchestrate.py` | `25f6118d5faaa8c478861e677cfeb66d1eccfb2d37d1408f98ca565d48797014` | `9c7a54c0565448eb449f3b92ca7b2aa46d73718397e91e9f95094912199f5fde` |
| `src/research_assistant/survey/build.py` | `14a79e6f648f94bf9ebbb33040010e488e6d0f17c6e7ea98e9d8f0d8b2430875` | `a5407e8d0b93fe0faff4260cd4a7ce5ea952ca22cc57124d60f42949e0964862` |
| `src/research_assistant/survey/source_intake.py` | `fc7c1981e2e9373d5ed2e4f2859c644b544812a6cb1bc964acc4cd1964c421e1` | `63d31b156af84be684b914147f7fd15d8a1a161c9b130738dee89ba723b27ae5` |

New implementation/test paths are:

- `src/research_assistant/survey/bootstrap.py`;
- `tests/unit/test_literature_survey_m17.py`;
- `tests/fixtures/literature_survey_m17/*.json`;
- `scripts/literature_survey_m17_local_validation.py`; and
- `docs/validation/literature_survey_m17_2026-07-13/generate_close_artifacts.py`.

Allowlisted optional paths that were not required remained byte-identical at
their M17 entry hashes. The preexisting CLI integration test also remained
byte-identical; the new behavior is covered by the dedicated M17 unit/CLI tests.

## Identity And Authority

- Topic missions use explicit input mode
  `idea_or_topic_without_initial_paper_seed` and preserve an empty original
  seed list.
- Selected candidates never enter GENESIS, the fingerprint payload, or
  `normalized_initial_seeds`.
- Confirmation is durably checkpointed before the capability call.
- Outcomes are exactly `selected`, `empty`, `ambiguous`, `unavailable`, and
  `capped`.
- The capability lifecycle is `intent -> call_started -> result_recorded ->
  prepared -> selected`.
- A durable `call_started` without complete authority blocks ordinary retry as
  `terminal_blocked_bootstrap_call_indeterminate`.
- Prepared evidence remains non-authoritative. Effective seeds and bootstrap
  authority appear only after a valid pointer plus selected/reconciled journal
  row.
- Default topic CLI execution uses the local unavailable capability and makes
  no inherited provider call. Selected fixtures can build only a local
  bootstrap-bound skeleton. Source intake stops before capability use without
  later metadata authority.

## Entry And Preservation Evidence

The immutable pre-edit snapshot remains valid:

| Check | Result |
| --- | --- |
| Frozen Phase 10 roots | `4/4` exact hashes |
| Phase 10 direct manifest | `38/38` rows |
| Phase 10 scoped inventory | `1,137/1,137`, tree `b6d5ddb4f52238abadaa07b5bd80ed74e478dab64088efa65eac3c7fd6c09d41` |
| Accepted M16 source manifests | `9/9` exact hashes |
| Preexisting M17 edit candidates | `10/10` resolved, zero mismatch or ambiguity |
| Entry-cutoff-only exceptions | `0` |

Snapshot manifest SHA-256:
`752b3d72c50d7e3eb45ba47a19528308e0c69faa5692bb49a6dedf85c1d5c340`.

The repaired cumulative successor manifest binds `1,671` exact repository
files, including every one of the 1,137 canonical Phase 10 evidence members
and all remaining hash-bound direct Phase 10 controls after path
deduplication. Its
canonical payload SHA-256 is
`163f9ca026e18903d219690ed88647c1bc26ae7f45cd0752aa05a9cb891d485f`;
independent replay reports zero mismatches. It includes the CLI-reachable survey
and SurveyBench runtime, cumulative local-gate tests and fixtures, exact survey
scripts, inherited M16 authority, the immutable M17 entry snapshot, and final
M17 evidence. Mutable post-manifest controls and diagnostic attempts are
explicitly outside that digest cycle.

## Local Checks

All Python and pytest commands ran with `CUDA_VISIBLE_DEVICES=-1`; GPU devices
were intentionally hidden.

| Gate | Result | Artifact |
| --- | --- | --- |
| Focused M17 schemas/authority/crash matrix | `65 passed`, including 38 named crash points | `docs/validation/literature_survey_m17_2026-07-13/focused_final_schema_round2.xml` |
| Cumulative M16+M17 unit surface | `846 passed` | `docs/validation/literature_survey_m17_2026-07-13/cumulative_m16_m17_unit_round1.xml` |
| Persistent topic/explicit matrix | `13/13 passed` | `docs/validation/literature_survey_m17_2026-07-13/persistent_matrix_final2/summary.json` |
| Exact survey script tests | `11 passed` | `docs/validation/literature_survey_m17_2026-07-13/exact_scripts_final.xml` |
| Affected non-CLI integration | `20 passed` | `docs/validation/literature_survey_m17_2026-07-13/affected_non_cli_integration_final.xml` |
| Full unit retry after VS Code crash | `1,050 passed` | `docs/validation/literature_survey_m17_2026-07-13/full_unit_retry_after_vscode_crash.xml` |
| Full CLI retry after VS Code crash | `125 passed` | `docs/validation/literature_survey_m17_2026-07-13/full_cli_retry_after_vscode_crash.xml` |
| Authoritative JUnit aggregate | `2,117 passed`, zero failures/errors/skips | six JUnit files above |
| Compile/JSON/static/diff/whitespace | passed | `docs/validation/literature_survey_m17_2026-07-13/static_audit.json` |
| Repaired successor artifact closure | `1,671/1,671`; all 1,137 Phase 10 members present | `docs/validation/literature_survey_m17_2026-07-13/successor_manifest_replay.json` |

The crash-interrupted `logs/full_unit_final.log` and `logs/full_cli_final.log`
are preserved as diagnostic only. Neither is used as completed evidence. Two
ad hoc close-audit commands initially assumed stale JSON/JUnit field names;
corrected read-only audits passed and did not change implementation or test
artifacts.

## Decision Table

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Candidate local engineering pass | Passed | No local hard veto remains | Fixture contract may not predict a real provider; clean checkout untested | Terminal read-only review, then M18 refresh | Live quality, source support, human/scientific validity, product or mission completion |

Engineering correctness is locally supported by deterministic state-machine,
crash, lineage, boundary, and regression checks. Live evidence remains absent.
Scientific interpretation is not applicable: no paper relevance, ranking,
importance, or completeness claim was tested.

## Post-Run Red Team

The strongest alternative explanation is that M17 proves a carefully specified
local state machine, not a usable production discovery capability. The weakest
evidence is the absence of a live provider and isolated installation. A replay
that changes mission identity after selection, permits a second indeterminate
call, exposes prepared authority, or fails because of an omitted clean-checkout
dependency would overturn the relevant local or handoff conclusion.

## Boundaries And Nonclaims

M17 performed no network/provider, source/PDF/full-text, GPU, package install,
credential, Git mutation, or release action. It does not establish live
bootstrap quality, paper relevance or importance, literature completeness,
source support, genuine human review, scientific correctness, clean-checkout
reproducibility, product readiness, release readiness, or north-star mission
completion.

## Review And Handoff

The bounded primary code review used Claude Opus at max effort after a successful
trusted health probe. It inspected identity, confirmation, immutable authority,
crash/replay, downstream lineage, explicit-seed compatibility, successor
summary, and claim scope, and returned `VERDICT: AGREE` with no material
code/semantics finding. No fallback or product repair was needed.

Review verdict:
`docs/reviews/literature_survey_m17_terminal_implementation_review_verdict_2026-07-14.md`.

A supervisor audit then found and repaired an artifact-coverage omission in the
first successor manifest. The repaired 1,671-row manifest and focused replay
received a fresh read-only fallback `VERDICT: AGREE` with no material finding.
The fallback provenance is explicit because the second Claude export was
policy-rejected and was not retried or routed around.

Artifact-closure verdict:
`docs/reviews/literature_survey_m17_artifact_closure_repair_review_verdict_2026-07-14.md`.

M17 closes as `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`. M18 receives
the immutable snapshot, passing matrices, repaired successor manifest, result,
and complete review trail. This handoff grants no live, source, human,
scientific, product, release, or push authority.
