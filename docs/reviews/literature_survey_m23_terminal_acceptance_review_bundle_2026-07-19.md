# M23 Terminal Operational Acceptance Review Bundle

Status: `HISTORICAL_ROUND3_PACKET_REVIEW_RETURNED_REVISE`

## Role Contract

Codex primary remains supervisor and executor. The reviewing Codex agent is
read-only and advisory only. Do not edit files, run experiments, launch agents,
or change state.

Claude review was attempted through the approved compact review gate. The
environment rejected export of repository content to the external service. The
call was not retried or routed around; this packet is for the declared fresh
Codex read-only fallback.

## Question

Does the exact `_r7` evidence support closing M23 and the M17-M23 program as
`ACCOMPLISHED_WITHIN_RECORDED_LOCAL_EXPLORATORY_SCOPE`, or is there a material
correctness, scientific-boundary, privacy, packaging, replay, regression, or
documentation defect that must be repaired first?

## Scope

Review this packet and these exact local surfaces when needed:

- `src/research_assistant/survey/m23_operational_acceptance.py`, especially
  `_build_wheel_from_fresh_staging`, `_normalized_command_stdout`,
  `_resume_lineage_and_state_valid`, `_m22_replay_code`, `_validate_cases`,
  `replay_acceptance`, and `run_acceptance`;
- `tests/unit/test_literature_survey_m23_operational_acceptance.py`;
- `src/research_assistant/survey/m22_representative_missions.py` replay and
  `src/research_assistant/survey/m22_retained_reconciliation.py` explicit-root
  retained-evidence validation if needed;
- `docs/plans/literature_survey_north_star_m23_operational_acceptance_result_2026-07-19.md`;
- `docs/reviews/literature_survey_m23_terminal_fallback_review_round1_2026-07-19.md`;
- `docs/reviews/literature_survey_m23_terminal_fallback_review_round2_2026-07-19.md`;
- candidate root
  `docs/validation/literature_survey_north_star_m23_operational_acceptance_2026-07-19_r7/`.

Out of scope: public release, live provider/source calls, credentials, source
acquisition, scientific truth, literature completeness, human expertise,
publication-ready prose, and historical custom terminal-control ceremony.

## Objective And Evidence Contract

M23 asks whether a fresh local process can build and install the current
package from an offline wheel, run documented literature-survey commands from
outside the source repository, preserve honest topic/seed boundaries and
qualitative nonpromotion, replay canonical M22 evidence, reject a mutated copy,
and keep completed-state documentation consistent with capabilities and
limitations.

Pass requires all nine predeclared cases, derived replay, no source-worktree or
repository-build-scratch dependency, every installed-command cwd outside the
repository, no network/credential/PDF action, affected regressions passing, and
no claim/prose/completeness promotion.

## Prior Findings And Repairs

1. `_r5` fallback Review Round 1 found aggregate-trusting replay. `_r6` repaired
   exact command identity, stdout reparsing, predicate reconstruction,
   capability/documentation recomputation, and exact projection replay.
2. `_r6` fallback Review Round 2 found weak installed identity/help, unchanged
   resume, and M22 limitation predicates. The current source validates package
   `research-assistant` version `0.1.0`, required installed help boundary text,
   valid generation ancestry, unchanged gate/state, zero transitions, no prose
   promotion, and explicit forward/50-row/195-unit limitations. Focused
   false-pass mutations cover all three findings.
3. The expanded suite then exposed a repository-local setuptools scratch
   dependency. The runner now copies the declared wheel inputs into a unique
   external temporary staging tree and builds there. A focused test calls the
   helper twice, proves distinct external roots and byte-equal staged inputs,
   and preserves a repository-build sentinel.

Prior roots remain preserved and are not relabeled final evidence.

## Candidate Evidence

| Evidence | Result |
| --- | --- |
| `_r7` terminal | `M23_OPERATIONAL_ACCEPTANCE_PASSED`; `9/9` |
| `_r7` offline replay | `passed` |
| installed module | `_r7/venv/lib/python3.11/site-packages/research_assistant/__init__.py` |
| installed command cwd | every row `/tmp/ra-m23-operator-3d82pi6p` |
| command stderr | all empty |
| command discovery | package `research-assistant`, version `0.1.0`, and installed help boundaries pass |
| unchanged resume | valid ancestry, unchanged gate/state, zero transitions, and no prose promotion pass |
| M22 replay | 9 cases pass; forward citations unavailable; 50 identifier-bearing rows and 195 identifier-free units open |
| copied tamper | rejected as `derived_artifact_replay_mismatch` |
| documentation | all completed-state consistency checks true |
| focused M23 suite | `11 passed` |
| complete affected gate | `262 passed, 77 deselected` |
| compile and JSON parsing | passed |
| source vs wheel M23 module | identical SHA-256 `926df6f8...5b97` |
| installed `_r7` replay from `/tmp` | passed with `PYTHONPATH` unset |

Run identity:

| Field | Value |
| --- | --- |
| Git commit | `15df2820aa7b0678c111211f48c7cbae454a114a`, dirty worktree recorded |
| Platform | Linux WSL2; Python 3.11.14 |
| CPU/GPU | deliberate CPU-only; `CUDA_VISIBLE_DEVICES=-1`; no framework import |
| Network/credentials/PDF | `false` / `false` / `false` |
| Wall time | `5.406698` seconds |
| Wheel SHA-256 | `311d7b5b62b3fc677786f8a7f63e2a123beac6a2b058e61184202b548e4356ba` |
| Terminal SHA-256 | `49fc9e76dcb68604408f6937c102bae3ab1a5952da75fe0f70f1dc1c1b4e693b` |
| Cases SHA-256 | `831697e02fd928da51a6725f85bf66269029fbbfcef8eae2492b8fb5169d5fb9` |
| Replay SHA-256 | `3d19d8dc975f20c5bc91debb20b1dbbd891f97c68242c752f17ea5716bd50699` |
| Manifest SHA-256 | `4fd9d18deecff839a886199617e4d9b5c72b6bab7b3e834ecab7812c7eb8941e` |
| Command ledger SHA-256 | `a230fafbe0ad99aadbaa821d198609e741577201c66ae4b7c0a7fcecaee8b304` |
| Documentation SHA-256 | `aa08188c6fca5cebbf6186dd03957f58c46996561205fc1e44f4e68fc4309aa4` |

## Scientific Boundary State

- New mission scope is arXiv-only; no OpenAlex prerequisite, credentials, or
  PDF fallback.
- Topic result is retained production replay, not live topic quality.
- Forward citations are unavailable, nonblocking, not zero, and not complete.
- 50 identifier-bearing omission rows remain title-context-only.
- 195 identifier-free units remain unresolved; unique paper count is unknown.
- Publication/retraction status and official code remain incompletely checked.
- `claim_support_allowed=false` and `ready_for_prose=false` remain authoritative.
- Publication and release remain separate human boundaries.

## Review Questions

1. Does external staging preserve every input that the declared setuptools
   wheel build needs while actually removing dependence on repository scratch?
2. Can any of the three repaired Round 2 predicates still false-pass after
   command-output reconstruction in `replay_acceptance()`?
3. Do case, terminal, inventory, documentation, or limitation projections rely
   on stored pass claims instead of recomputation?
4. Does any result or completed-state document cross the recorded local
   operational scope into scientific, human-usability, product, or release
   claims?

## Pass And Block Criteria

Pass only if the evidence supports local offline operational accomplishment and
no material implementation, replay, build isolation, regression,
documentation, privacy, or scientific-boundary defect remains.

Block if source checkout or repository build scratch can satisfy installed
checks; installed identity/help can false-pass; resume ancestry or zero-state
advancement can false-pass; the three M22 limitations can disappear; stored
aggregate claims can substitute for derived replay; stale/tampered or failed
artifacts can pass; or the result promotes truth, completeness, claim support,
prose readiness, human usability, product readiness, or release.

## Nonclaims

Even if this review passes, do not conclude literature completeness, scientific
truth, live topic-discovery quality, provider reliability, publication safety,
publication-ready prose, autonomous expert judgment, human usability,
macOS/native-Windows support, general product readiness, or release readiness.

## Requested Verdict

Findings first, with at most three material bullets. End with exactly:

`VERDICT: AGREE`

or

`VERDICT: REVISE`
