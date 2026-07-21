# M20 Recovery V3 Repair Result

Date: `2026-07-17`
Status: `PASSED_LOCAL_REPAIR_FRESH_INTEGRATION_PENDING`
Plan: `docs/plans/literature_survey_north_star_m20_recovery_campaign_plan_2026-07-17.md`

## Migration And Decision

The current repository policy retires the earlier packet-level launch ceremony
as execution authority while preserving its artifacts as historical evidence.
The unexecuted recovery v2 packet, wheel, install, and review packet under
`docs/validation/literature_survey_m20_recovery_campaign_2026-07-17/` are now
superseded proposals and must not be executed. The consumed historical M20B4
packet remains immutable and must never be rerun.

The skeptical audit passed for local repair. The baseline remains the reviewed
five-route M20 workflow, not the dirty worktree; request yield and latency
remain explanatory only; unknown provider or cost state remains a continuation
veto; and no command in this repair used a real credential or network.

## Material Repairs

| Prior finding | Repair and catching evidence |
| --- | --- |
| Diagnostic publication was a single point of failure | A credential-blind outer intent is atomically published before child start. Failure prevents launch. Primary and fallback terminal records bind the intent hash; total terminal publication failure leaves the intent as an explicit hard-stop artifact. |
| Diagnostic transitions and exits were underconstrained | Closeout requires exact diagnostic transitions, manifest presence, outer reconciliation, and `completed -> 0`; every other supervisor classification requires exit `2`. |
| Lifecycle-error histories did not mirror the producer | Supervisor manifest schema v2 records the exact lifecycle stage. Closeout accepts only stage/signal combinations reachable from initial wait, post-TERM wait, post-KILL wait, final-reap timeout, and cleanup. |
| Timing was not classification/deadline coherent | Soft, hard, final-reap, lifecycle, and cleanup stages have classification-specific elapsed-time floors, including preservation of the final-reap floor through cleanup reclassification. |
| Completed inventory ignored empty directories and hardlinks | Closeout requires the exact producer directory set, exact file set, exact size/hash rows, no symlinks/special files, and link count one for every retained file. |
| Replay could use ambient code | The isolated interpreter reports all six runtime module origins and hashes from inside the replay process; closeout compares them exactly and verifies that the interpreter belongs to the installed environment. |
| Campaign attempt/cost state was not automatic | One normalized predecessor/successor schema records attempts, provider-capable launches, reconciled/remaining cost, lineage, retry permission, and continuation veto. Supervisor preflight validates the state before credential lookup. |

Additional audit repairs reject non-finite elapsed values, require exact runtime
module coverage including the outer launcher, validate canonical terminal-record
parents, and allow the new intent-preflight error only through the bounded
preflight diagnostic vocabulary.

## Checks

All test commands used source-tree imports explicitly. No test accessed
`OPENALEX_API_KEY`; synthetic canaries were used where credential behavior was
needed. GPU was not initialized because this is a CPU-only metadata lane.

| Check | Result |
| --- | --- |
| Focused launcher/supervisor/recovery-closeout matrix | `76 passed` |
| Complete affected M20 plus historical and recovery closeout matrix | `428 passed in 2.95s` |
| Python compile | passed |
| `git diff --check` | passed |
| Skeptical diff audit | passed after repairing a displaced parent-path check and two replay/timing gaps |

## Evidence Boundary

| Boundary | State |
| --- | --- |
| Historical M20B4 packet rerun | false |
| Superseded recovery v2 packet execution | false |
| Real `OPENALEX_API_KEY` inspected/read/used | false |
| Provider or other network call | false |
| Source/PDF/full-text access | false |
| M21, push, or release | false |
| M20/G3/north-star completion claim | false |

## Handoff

Create one narrow integration commit containing the v3 launcher, supervisor,
credential-free closeout, focused tests, and this result. Reproduce that exact
commit from a fresh isolated clone, build and install an offline wheel, prove
complete member equality, rerun installed synthetic checks, and create a new
versioned v3 packet and validation root. Do not reuse or execute any v2 path.

Only after the fresh packet passes exact-hash advisory review may the campaign
reach the external boundary. Credential lookup, arXiv/OpenAlex calls, and paid
usage still require explicit human authority under a total USD `$0.01` cap and
at most two provider-capable launches, with no retry after unknown or
unreconciled provider/cost state.

## Integration Attempt 1 Repair Trigger

Commit `89ad6d6019c18a3417a292fdd0f24f83378e7bac` reproduced `295/295`
tracked M20/recovery tests and built an offline wheel, but packet-generation
audit found that packet-only preflight required the outer intent to exist even
though the launcher must create that intent at the start of the real
invocation. Running packet preflight would therefore consume the path and make
the later launcher fail closed before its child started.

This is a localized launch-instrumentation failure with zero credential access,
zero provider activity, and zero cost. Commit `89ad6d60`, its clone, wheel, and
pip-less install are superseded integration-attempt evidence and must not be
used to create or execute a live packet. The repair separates packet-only
preflight (`intent path must be fresh and absent`) from execution-time child
preflight (`launcher-created intent must validate`) while retaining the rule
that intent validation completes before credential lookup.

## Integration Attempt 2 Repair Trigger

Commit `efee4bfad8f79514938bdc21fa164c7e6ec93c4a` reproduced `296/296`
tracked M20/recovery tests and built wheel SHA-256
`72ae86537cd9bfbf96db7b62a7ce8a0623ae46fda5e16349a2bef0f2494b96ae`.
The complete installed-member gate then found `__pycache__` files created by an
installed import probe despite `PYTHONDONTWRITEBYTECODE=1`. Python isolated mode
(`-I`) ignores `PYTHON*` environment variables, so the prior no-bytecode claim
was unsupported at installed execution boundaries.

This is a localized packaging/topology failure with zero credential access,
zero provider activity, and zero cost. Both attempt-2 installs are preserved as
failed local evidence and must not be used for packet creation. The repair adds
interpreter flag `-B` to the launcher, supervisor, worker, and installed replay
commands while retaining `-I`, making bytecode suppression explicit and
testable rather than environment-dependent.

## Integration Attempt 3 Repair Trigger

Commit `db4e323edc5abbd145f6b2b2782e640c7558feba` reproduced `296/296`
tracked tests, built wheel SHA-256
`d60894438aaa182937ac3490090170e73c39f3bc8a40f6e98dce89f8e54690f1`,
passed `100/100` installed equality before and after synthetic execution, and
froze unexecuted packet SHA-256
`94adcb451a01fb8021a1867cbb66137b145265a7ef29ff5ee3b385807e6e652c`.
Exact packet audit then found that its immutable status self-asserted
`reviewed` before advisory review occurred.

This is a local evidence-labeling defect with zero credential access, zero
provider activity, and zero cost. The wheel/install remain valid engineering
evidence, but the packet is superseded and must not be executed. The repair
renames the immutable packet state to
`candidate_pending_advisory_review_and_external_authority`; any later advisory
agreement must be a separate result bound to the unchanged candidate hashes.
