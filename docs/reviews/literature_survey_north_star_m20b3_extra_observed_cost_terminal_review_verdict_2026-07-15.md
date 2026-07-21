# M20B3 Extra Observed-Cost Terminal Review Verdict

Date: `2026-07-15`
Reviewer: fresh Codex read-only fallback
Verdict: `AGREE`

Claude export was policy-rejected before invocation because repository content
would leave the private workspace. No workaround was attempted. The approved
fresh Codex read-only fallback reviewed the exact frozen bytes.

## Frozen Bytes

| File | SHA-256 |
| --- | --- |
| `src/research_assistant/survey/m20_live_worker.py` | `ef873948aa3c61dea87a82a0af9d85154f7e8a2762961c4274dc941da1129157` |
| `tests/unit/test_literature_survey_m20_live_worker.py` | `10d3b2f018d24d84a99eb1b4a0c788b6a0e2a6a9c6a20d89484842291fe28040` |
| `src/research_assistant/survey/m20_live_supervisor.py` | `96890d38f984bb579fdcc79eff1487dd39925a198d5d955980099a6ba7a30fb6` |
| `tests/unit/test_literature_survey_m20_live_supervisor.py` | `f7013e5229aa29b9288aabc5789ce0cd0eadb87f2afd83668fc35cf815ea8c7e` |

## Review Result

No material findings remain. The replay predicate matches producer-reachable
observed-cost shapes:

- null-only for dispatch, response-type, credential-echo, and response-cost
  failures;
- canonical finite nonnegative decimal unequal to prediction for
  `cost_contradiction`;
- canonical finite nonnegative decimal for post-parse state failures; and
- exact predicted cost for `campaign_cost_cap_exceeded`.

The mutation helper rebinds both the request-ledger digest and final summary
cost state, so rejection is attributable to the repaired predicate. Focused
worker tests passed `54/54`; the cumulative M20 set passed `227/227`.

This verdict closes only the observed-cost replay blocker. It does not itself
authorize M20B4, a real credential, a provider call, source access, push,
release, or any completion claim. The previously authorized M20B3 local Git,
clone, wheel, installed synthetic-validation, and packet-freeze gates may now
resume under the unchanged subplan.

`VERDICT: AGREE`
