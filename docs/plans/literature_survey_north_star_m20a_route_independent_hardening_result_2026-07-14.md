# M20A Route-Independent Hardening Result

Date: `2026-07-14`
Status: `PASSED_ROUTE_INDEPENDENT_LOCAL_ENGINEERING_OFFICIAL_ROUTE_CONTRACT_PENDING_M20B_DO_NOT_EXECUTE`
Milestone: `M20_live_discovery_and_citation_frontier`

## Outcome

The route-independent M20A state-machine, accepted-body, identity, frontier,
inventory, and replay engineering passes its local evidence contract. The
round-5 substantive test gap was repaired without changing runtime code: one
deterministic test now evaluates the full `6 x 7 x 7 = 294` composition space,
accepts all `40` permitted states through real producers, and rejects all `254`
forbidden states.

The current repository policy retires hash-bound approval-token machinery for
trusted local research. The canonical automaton JSON remains a useful
diagnostic snapshot, but its SHA-256 is not execution authority. The historical
five-round blocker and `REVISE` verdict are preserved rather than rewritten.

This result does not complete M20A. No checked local official OpenAlex/arXiv
route documentation exists, so route-dependent adapters remain unimplemented.
No documentation URL, provider API, source/PDF/full-text route, GPU, credential,
Git mutation, push, or release action ran in this local repair.

## Skeptical Audit

The focused repair passed the pre-execution audit:

- baseline: the M19 result and frozen route-independent runtime were unchanged;
- promotion criterion: exhaustive state rejection is an engineering invariant,
  not a proxy for provider quality or M20 completion;
- stop conditions: runtime failure, cumulative regression, or unexpected scope
  change would have stopped the repair;
- environment: all commands were deliberate CPU-only and no-network;
- artifact fitness: the test directly exercises the runtime validator over the
  complete declared state space;
- hidden assumption: official route semantics remain explicitly unchecked and
  cannot be inferred from the local state machine.

## Evidence

| Artifact | Evidence |
| --- | --- |
| Baseline HEAD | `ad4e2d52ab9df7198547b3cb98d8acbd1b9680a5` |
| Runtime candidate | `src/research_assistant/survey/discovery_capability.py`, SHA-256 `ceea83a8efcfb21d40533b0f42ff75e8b4cc0d0131916fb080a77ca2278189ba`; unchanged by this repair |
| Exhaustive tests | `tests/unit/test_literature_survey_m20_discovery.py`, SHA-256 `50a78d05365ad6660533916e071675cba233a07c04605ebd2be9149d9d5029ff` |
| Canonical automaton | Canonical JSON digest `4ef966fd41b7544e30e76fb5a51595c49bdf97167fffab47cff06ca89f756775`; diagnostic only |
| M20 focused file | `72 passed in 0.31s`; includes one full 294-state matrix test |
| M19+M20 cumulative gate | `128 passed in 4.92s`; JUnit SHA-256 `476ab53aa6afc12793813ac3cb9da5a60811dcd7cbdf8c7605c1d6992378919d` |
| Affected M16/M17 gate | `262 passed in 105.47s`; JUnit SHA-256 `223a192e4edaaf14b05704c822f003602e1f0d3ed113c95454e61414cfe0c8f8` |
| Evidence root | `docs/validation/literature_survey_m20_local_hardening_2026-07-14/` |

The candidate automaton file reparses to the exact runtime-generated canonical
object. Its file-byte SHA-256 differs from the canonical digest because the
stored file has presentation whitespace; no semantic mismatch exists.

## Decision Table

| Decision | Primary criterion status | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Pass route-independent M20A engineering | Met: all 294 composition states are classified and cumulative gates pass | No local runtime, replay, inventory, or regression veto fired | Official OpenAlex/arXiv route and field semantics are not checked locally | Acquire a bounded official documentation snapshot, inspect it, then implement only supported routes under a refreshed local plan | M20A completion, M20B authority, provider quality, citation recall, source support, product readiness, or north-star completion |

## Inference Status

| Evidence class | Status |
| --- | --- |
| Hard veto screen | Local state-machine and cumulative gates pass; missing official route evidence still blocks route-dependent implementation. |
| Statistically supported ranking | Not applicable; no stochastic comparison or provider ranking ran. |
| Descriptive-only differences | Test counts, runtimes, and file sizes only. |
| Default readiness | Not established; no provider route or product default changed. |
| Next evidence needed | Checked official route documentation, a route-specific adapter/fixture repair, isolated local validation, and a bounded M20B campaign plan. |

## Post-Run Red Team

The strongest alternative explanation is that full Cartesian rejection merely
duplicates the permitted-set membership check. That duplication is deliberate:
it catches drift between declared state axes, producer-valid permitted states,
and fail-closed composition. It does not prove provider schema fidelity. A
checked official contract that contradicts the planned route or field meaning
would require plan and adapter repair before any live use.

## Handoff

Proceed only to the dedicated official-provider-contract acquisition subplan.
M20B, M21, provider API calls, source/PDF/full-text retrieval, and any M19 rerun
remain `DO_NOT_EXECUTE`.
