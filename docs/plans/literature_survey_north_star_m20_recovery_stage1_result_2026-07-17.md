# M20 Recovery Stage 1 Result

Date: `2026-07-17`
Status: `PASSED_LOCAL_RECOVERY_INSTRUMENTATION`
Plan: `docs/plans/literature_survey_north_star_m20_recovery_campaign_plan_2026-07-17.md`

## Result

The recovery supervisor now binds a fresh packet schema and a separate atomic
launch-diagnostic path. The historical M20B4 packet cannot validate against
the new schema and remains consumed historical evidence.

Every post-argument launch branch records a bounded outcome without exception
text, environment enumeration, credential value/digest, request URL, header,
or provider response content. Failures before supervised execution establish
`provider_activity=false` and `cost_usd=0.00`. Once supervised execution starts,
provider activity and cost remain `not_established` until the live manifest and
ledgers reconcile them.

## Checks

All checks ran with `OPENALEX_API_KEY` removed,
`CUDA_VISIBLE_DEVICES=-1`, and bytecode writing disabled.

| Check | Result |
| --- | --- |
| Recovery supervisor focused tests | `18 passed` within the combined run |
| Unchanged M20 worker tests | `54 passed` within the combined run |
| Complete affected M20 matrix | `232 passed in 2.89s` |
| `py_compile` | passed |
| JSON milestone parse | passed |
| `git diff --check` | passed |

Covered diagnostic outcomes include missing execution flag, packet/preflight
failure, unexpected preflight failure, credential lookup failure, credential
unavailable, supervised return, and unexpected supervisor error. Synthetic
canaries do not appear in diagnostic records.

## Evidence And Boundary Status

| Question | Status |
| --- | --- |
| Historical packet rerun | false |
| Real credential inspected/read/used | false |
| Provider/network action | false |
| Source/PDF/full-text access | false |
| Product/scientific behavior changed | false |
| G3/M20 closed | false |

## Handoff

Proceed to Stage 2: make an exact-path local commit, reproduce it from an
isolated clone, build and extract an offline wheel, verify complete installed
member equality, and freeze a fresh recovery packet with versioned diagnostic
and live roots. No credential or provider action is authorized by this result.
