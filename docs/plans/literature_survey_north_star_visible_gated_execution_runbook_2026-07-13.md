# Literature Survey North-Star Visible Gated Execution Runbook

Date: `2026-07-13`
Status: `M21_G4_PASSED_M22_HUMAN_BOUNDARY_OPEN`

## Role Contract

Codex in the current visible conversation is the supervisor and executor.
Claude may be used only as a read-only reviewer. A fresh Codex agent is the
read-only fallback when environment policy prevents repository export or Claude
is unavailable. No reviewer may edit files, execute the program, or authorize
Git mutation, network/source access, genuine human decisions, scientific
claims, product defaults, funding, credentials, release, or any other human
boundary.

This runbook does not launch a detached or nested execution supervisor. Do not
use `codex exec`, detached runners, `setsid`, `nohup`, backgrounded phase
workers, or copied-workspace supervisors. All execution and repair remains
visible and recoverable in the current conversation.

## Program

| Role | Artifact |
| --- | --- |
| Master program | `docs/plans/literature_survey_north_star_gap_closure_master_program_2026-07-13.md` |
| Canonical milestone ledger | `docs/plans/literature_survey_automation_milestones.json` |
| Converged master review | `docs/reviews/literature_survey_north_star_gap_closure_plan_review_verdict_round3_2026-07-13.md` |
| Visible execution ledger | `docs/plans/literature_survey_north_star_visible_execution_ledger_2026-07-13.md` |
| Stop/handoff record | `docs/plans/literature_survey_north_star_visible_stop_handoff_2026-07-13.md` |
| Program setup result | `docs/plans/literature_survey_north_star_program_setup_result_2026-07-13.md` |
| Resolved setup blocker history | `docs/plans/literature_survey_north_star_program_setup_review_nonconvergence_blocker_2026-07-13.md` |

The north-star completion predicate remains the master program's M23 rule. A
successful setup or M17 pass is not mission completion.

## Milestone Index

| Milestone | Name | Dedicated subplan | Required result artifact | Initial authority |
| --- | --- | --- | --- | --- |
| M17 | Idea And Topic Bootstrap | `docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_subplan_2026-07-13.md` | `docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_result_2026-07-13.md` | `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING` |
| M18 | Reproducible Git Integration | `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_subplan_2026-07-13.md` | `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_result_2026-07-14.md` | `PASSED_LOCAL_GIT_INSTALL_REPRODUCIBILITY` |
| M19 | Bounded Live Metadata Validation | `docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_subplan_2026-07-13.md` | `docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_result_2026-07-13.md` | `PASSED_TERMINAL_REVIEW_AGREED_ONE_ATTEMPT_CONSUMED` |
| M20 | ArXiv Source-Grounded Backward Discovery | `docs/plans/literature_survey_north_star_m20_arxiv_only_500mb_attempt_plan_2026-07-18.md` | `docs/plans/literature_survey_north_star_m20_arxiv_only_close_result_2026-07-18.md` | `PASSED_REVISED_M20_G3_SOURCE_GROUNDED_BACKWARD_DISCOVERY` |
| M21 | Live Source Status And Anchor Intake | `docs/plans/literature_survey_north_star_m21_live_source_status_and_anchor_intake_subplan_2026-07-13.md` | `docs/plans/literature_survey_north_star_m21_live_source_status_and_anchor_intake_result_2026-07-13.md` | `PASSED_G4_SIX_PARSED_ONE_EXPLICIT_GAP` |
| M22 | Human-Attested Review And Real Missions | `docs/plans/literature_survey_north_star_m22_human_attested_review_and_real_missions_subplan_2026-07-13.md` | `docs/plans/literature_survey_north_star_m22_human_attested_review_and_real_missions_result_2026-07-13.md` | `PLANNING_REFRESHED_HUMAN_ATTESTATION_REQUIRED_DO_NOT_EXECUTE` |
| M23 | North-Star Acceptance And Operational Closeout | `docs/plans/literature_survey_north_star_m23_acceptance_and_operational_closeout_subplan_2026-07-13.md` | `docs/plans/literature_survey_north_star_m23_acceptance_and_operational_closeout_result_2026-07-13.md` | `REFRESH_AND_REVIEW_REQUIRED_DO_NOT_EXECUTE` |

M17-M20 result paths in this table contain actual evidence. The older
provider-dependent M20 results remain historical evidence only. M21 now has a
bounded passed result. M22-M23 result paths remain declarations, not evidence,
and must remain absent until their milestones write them.

## Program Evidence Contract

| Field | Contract |
| --- | --- |
| Question | Can the M16 local alpha be extended, integrated, exercised on bounded real evidence, genuinely reviewed, and independently operated without weakening its identity, lineage, safety, or honest-stop semantics? |
| Baseline | Frozen M16 local integrated alpha on the preserved dirty worktree, followed by each immediately preceding passed milestone. |
| Primary completion criterion | M17-M23 pass in order and M23 satisfies the master program's independent clean-install idea/topic acceptance predicate. |
| Hard vetoes | False readiness; stale/foreign authority; fabricated paper or human identity; unapproved Git/network/source action; outside write; unsupported technical claim; hidden omission/review blocker; corrupted evidence; changed criteria after results. |
| Explanatory only | Counts, result volume, scores, latency, bytes, parser yield, review duration, and operator time unless a refreshed subplan explicitly and validly assigns another role. |
| Not concluded | Literature completeness, universal scientific correctness, provider reliability at scale, autonomous human judgment, credentials/private/paid access, unbounded crawling, or production/release readiness outside the final recorded scope. |
| Preserving artifacts | Dedicated subplans/results, ledger entries, manifests, request/source/decision records, review verdicts, stop handoffs, and final close record. |

## Default And Assumption Audit

| Choice | Provenance | Justification | Failure mode | Early diagnostic | Status |
| --- | --- | --- | --- | --- | --- |
| M16 dirty-tree evidence is the initial baseline | M16 close record | It is the last passed authority | Treating it as clean Git evidence | Frozen-hash replay and explicit M18 gate | Baseline |
| Topic/idea uses `--topic` with no initial `--seed` | M17 passed authority | It makes the stated interface honest without fabricating a paper | Topic text is silently treated as title/identifier | M17 input-mode and provider-tripwire tests | Passed local engineering; live quality untested |
| Explicit-seed V2 semantics remain unchanged | M16 compatibility requirement | Avoids identity and replay regression | A schema migration rewrites historical mission identity | Fixed-vector and full M16 regression gates | Required |
| One persisted discovery confirmation | M15/M16 authority | Ordinary in-scope public actions should not reprompt by provider | Bootstrap runs before confirmation or later ordinary actions reprompt | Confirmation tripwire and resume matrix | Required |
| M18 precedes promotion-oriented live work | Converged master review | Live evidence from untracked code is not reproducible authority | A live result cannot be tied to an installable commit | Clean-checkout gate | Required |
| Claude review is advisory and optional when policy blocks export | Review gate guide and prior environment rejection | Local evidence must carry the gate | Silence or fallback is misrepresented as proof | Provenance field plus local checks | Required |

## Skeptical Plan Audit

Before each milestone, append a ledger entry that explicitly checks:

- wrong or stale baseline;
- a proxy or descriptive diagnostic promoted to a pass criterion;
- missing stop, repair, or continuation-veto conditions;
- unfair or post-result comparison changes;
- hidden identity, authority, privacy, rights, cost, or environment assumptions;
- commands whose artifacts cannot answer the milestone question;
- overlap with unrelated dirty user work; and
- mismatch between declared CPU/GPU/network state and actual execution.

If a material flaw is found, revise and review the dedicated subplan before any
implementation or experiment. Passing reason and remaining nonclaims must be
recorded in the ledger.

## Visible State Machine

Each milestone follows exactly this state machine:

1. `PRECHECK`
   - Read the master, runbook, predecessor result, current subplan, ledger, and
     handoff.
   - Verify the predecessor handoff, exact hashes, permissions, absent future
     output roots, and the subplan's edit/write allowlist.
   - Run and record the skeptical audit.
   - Restate the evidence contract and research-intent roles.
2. `EXECUTE_MINIMAL`
   - Execute only the smallest visible local slice needed by the subplan.
   - Preserve unrelated dirty work and all immutable evidence.
   - Use no live/Git/source/human authority not explicitly present.
3. `ASSESS_GATE`
   - Run catching checks first, then affected regression and boundary gates.
   - Classify hard vetoes before explanatory diagnostics.
   - Distinguish candidate failure from invalid harness, boundary, target,
     data, math, or artifact.
4. `WRITE_RESULT`
   - Write the milestone result/close record, run manifest, decision table,
     inference-status table when stochastic comparison occurs, nonclaims, and
     exact unresolved boundaries.
5. `REVIEW_IF_MATERIAL`
   - Freeze a compact, self-contained packet and request one fresh read-only
     review when it reduces a material engineering or scientific risk.
   - Findings are advisory; local evidence carries the pass predicate.
6. `REPAIR_LOOP`
   - For a fixable finding, patch visibly within the allowlist, rerun the
     smallest catching check and affected gates, update the same result, and
     rereview the material delta.
   - Continue for at most five rounds on the same material blocker.
7. `HANDOFF`
   - For M17-M22, refresh the next milestone's dedicated subplan using actual
     predecessor artifacts, commands, hashes, limits, and authority.
   - Review that successor subplan for consistency, correctness, feasibility,
     artifact coverage, inherited conditions, and boundary safety.
   - If that review returns `REVISE`, patch the successor subplan visibly, rerun
     its focused structural/boundary checks, and rereview for at most five rounds
     on the same material blocker.
   - Advance M17-M22 only after the successor subplan's material verdict is
     `AGREE` and its entry authority remains valid. On nonconvergence, write a
     blocker result and stop; reviewer silence or a missing verdict is not
     agreement.
   - M23 has no successor subplan and never calls the successor-review or
     `ADVANCE` path. After its result/review repair loop converges, use the
     fail-closed pending/pre-seal/terminal-selection/replay/activation sequence
     below and terminate with exact accomplished, blocker, or indeterminate
     status.
   - Update the milestone ledger and stop/handoff record before successor
     advance or M23 terminal close.

Expected provider unavailability, empty candidates, a failed mission arm, or a
parser yielding no anchor is a repair trigger or honest candidate result, not a
continuation veto, unless the current subplan says the harness or boundary is
invalid.

## Repair Loop Pseudocode

```text
for milestone in M17..M23:
    require reviewed dedicated subplan and predecessor handoff
    PRECHECK()
    while material_work_remains:
        EXECUTE_MINIMAL()
        ASSESS_GATE()
        if continuation_veto:
            WRITE_BLOCKER_AND_HANDOFF()
            stop
        if fixable_problem:
            PATCH_VISIBLY()
            RERUN_FOCUSED_CHECKS()
            continue
        break
    WRITE_RESULT()
    REVIEW_IF_MATERIAL()
    while verdict == REVISE and rounds < 5:
        PATCH_VISIBLY()
        RERUN_FOCUSED_AND_AFFECTED_CHECKS()
        REFRESH_RESULT_AND_REVIEW_PACKET()
        verdict = REVIEW_READ_ONLY()
    if verdict does not converge on a material blocker:
        WRITE_BLOCKER_AND_HANDOFF()
        stop
    if milestone in M17..M22:
        next_verdict = REFRESH_AND_REVIEW_NEXT_SUBPLAN()
        while next_verdict == REVISE and next_rounds < 5:
            PATCH_NEXT_SUBPLAN_VISIBLY()
            RERUN_NEXT_SUBPLAN_FOCUSED_CHECKS()
            next_verdict = REVIEW_NEXT_SUBPLAN_READ_ONLY()
        if next_verdict != AGREE:
            WRITE_NEXT_SUBPLAN_BLOCKER_AND_HANDOFF()
            stop
        ADVANCE()
    else:  # M23 terminal branch; there is no automatic next milestone.
        pending = WRITE_IMMUTABLE_PENDING_FINAL_PREDICATE_GENERATION()
        preseal = RUN_AND_PERSIST_M23_PRESEAL_PREDICATE(pending)
        terminal = BUILD_IMMUTABLE_TERMINAL_GENERATION(pending, preseal)
        VALIDATE_COMPLETE_TERMINAL_GENERATION(terminal)
        selector = ATOMIC_NO_REPLACE_SELECT_AND_FSYNC_UNDER_MISSION_LOCK(terminal)
        replay = POST_SELECTION_REPLAY_FROM_DISK(selector)
        if replay != PASS:
            DO_NOT_WRITE_ACTIVATION_RECEIPT()
            RESOLVE(terminal_blocked_final_control_selection_indeterminate)
            stop
        receipt = ATOMIC_NO_REPLACE_WRITE_AND_FSYNC_ACTIVATION_RECEIPT(selector, replay)
        final_status = CANONICAL_RESOLVER_REPLAY(selector, receipt)
        require final_status in {ACCOMPLISHED_WITHIN_RECORDED_EXPLORATORY_SCOPE, exact_blocker}
        TERMINATE_PROGRAM_LOOP(final_status)
```

Do not stop while a declared repair can proceed safely inside current
authority. Do stop at a declared human, runtime, source, privacy, cost,
scientific-claim, destructive-action, or nonconverged-review boundary.

## M23 Terminal-Control Transaction

The pending generation contains canonical projections of the final close,
milestone JSON, mission control, reset memo, master, capability/limitations
matrix, release manifest, ledger, and handoff. Every projection says
`PENDING_FINAL_PREDICATE`, binds one transaction ID and proposed terminal
status, and makes no accomplished claim. Its manifest is written last.
The transaction ID is deterministically derived from frozen M23 result/review,
substantive predicate-input digest, and null predecessor selector. The pending
proposal is accomplishment-only; a predeclared ordered first failed hard veto,
not the proposal, chooses any exact blocker.

The pre-seal predicate checks every substantive M23 completion criterion and
pending-control agreement without requiring an already-final status, selector,
or activation receipt. Its immutable pass/fail receipt deterministically fixes
the terminal generation as accomplished or one exact blocker. The complete
terminal generation is manifest-bound before a single regular-file,
non-symlink selector is published under the mission lock by atomic
same-filesystem hard-link creation from a fully written/fsynced temporary file.
The selector path must be absent, `EEXIST` fails closed, and the parent is
fsynced; ordinary overwriting rename and check-then-write are forbidden.

Selection does not activate the status. The supervisor must reread selector,
manifest, every control, all predicate inputs, and nonclaims from disk and
persist a post-selection replay record. Only a passing replay permits a
last-written activation receipt at the deterministic selector-hash path that
binds the exact selector, selected manifest, replay record, and terminal status.
It uses the same no-replace hard-link/fsync protocol; an existing receipt is
accepted only when byte-identical and valid. The canonical resolver validates
that complete pair again before reporting status. Any missing/mismatched
receipt, failed replay, corrupt/partial generation, stale or
foreign selector, or mixed status resolves exactly
`terminal_blocked_final_control_selection_indeterminate`, never accomplishment.
Resume may complete replay/activation only for unchanged, fully valid selected
bytes and makes no external/source/human call.

Selected projections do not hash-bind their downstream selector/replay/receipt;
the authority envelope binds them without a digest cycle. Optional top-level
mirrors cannot establish or override status. Missing/stale mirrors are repaired
locally from the selected generation and do not invalidate an otherwise valid
selector/receipt pair; contradictory mirror claims are ignored.

## Execution-Byte Authority Gate

M18 establishes the first identified clean commit. After M18, any product,
adapter, transport, parser, review-interface, packaging, or documentation code
changed for M19-M23 may be developed and tested locally, but it cannot generate
promotion-bearing live, source, genuine-human, or independent-acceptance
evidence from an uncommitted dirty tree.

Before each such evidence-bearing run, the current refreshed subplan must prove
one of:

1. every execution byte and required package/data/document byte equals the
   identified predecessor commit and an isolated checkout of that commit passes
   the affected gates; or
2. a separately reviewed exact include/exclude and Git procedure received
   fresh user approval, created an identified successor commit, and an isolated clean checkout/install of that successor passed the affected cumulative
   local, manifest, boundary, and command-discovery gates.

The run manifest records that commit and proves imports, executables, schemas,
fixtures, parsers, UI assets, and documentation resolve from the isolated
checkout/environment rather than the dirty source tree. A result produced by
uncommitted or mismatched bytes is diagnostic only and cannot satisfy a
milestone handoff. Git authority never implies network/source/human/release
authority, and those authorities never imply Git mutation.

## Review Protocol

For a material review, create a compact packet under `docs/reviews` with the
objective, exact artifacts or excerpts, checks run, evidence contract,
forbidden claims/actions, known limitations, and fixed verdict syntax.

If Claude use is policy-permitted, run the repository's approved noninteractive
review gate in trusted context. If a material request returns no output:

1. send a tiny health probe requiring exactly `CLAUDE_PROBE_OK`;
2. if the probe passes, redesign or split the packet rather than declaring
   Claude dead;
3. if the trusted probe fails, record reviewer unavailability and use a fresh
   Codex read-only reviewer; and
4. never route around an environment-policy export rejection.

Every verdict ends in exactly `VERDICT: AGREE` or `VERDICT: REVISE`. Claude or
fallback agreement cannot override a failed local gate or authorize a boundary.

## Quiet Visible Execution

Every Python or test command must set `CUDA_VISIBLE_DEVICES=-1` before import.
This program has no planned GPU work. Any later GPU probe or job requires an
escalated trusted command under the repository policy and a refreshed subplan.

For commands with large output:

1. predeclare log and structured-artifact paths;
2. redirect full output to the log without `tee`;
3. print only exit status, artifact paths, pass/fail fields, and at most the
   last 40 lines on failure;
4. poll bounded status rather than stream; and
5. preserve logs in the milestone result.

Network, provider, source, PDF/full-text, credential, paid-model, and external
human-review actions are absent from M17 and must not be inferred from this
runbook.

## Approval Map

### 2026-07-14 Policy Migration

The newest repository `AGENTS.md` policy retires the legacy requirement for
special hash-bound approval wording before ordinary trusted-local staging,
committing, cloning, wheel building, installation into `/tmp`, and CPU-only
validation. Historical approval-token language is preserved as history but is
not active authority. The user's repeated `execute` and crash-resume requests
authorize M18's reviewed non-destructive local integration campaign. Push,
public release, destructive/history-rewriting action, credentials, paid or
expanded compute, privacy changes, and M19-M22 live/source/human boundaries
still require authority at the actual boundary.

| Boundary | Earliest milestone | Required authority |
| --- | --- | --- |
| Local M17 implementation and CPU-only tests | M17 | Passing reviewed program setup and unchanged M16 entry authority |
| Exact local stage/commit/clone integration procedure | M18 | User's execute/resume request plus current repository policy, after exact include/exclude review |
| One metadata-only live attempt | M19 | Fresh exact endpoint/query/cap/hash/output approval after plan convergence |
| One bounded arXiv-only source/backward-discovery attempt | M20 | Active reviewed arXiv-only plan and the user's existing single-attempt authorization |
| Source/status or source/PDF/full-text retrieval | M21 | Separate reviewed rights/domain/type/cap/retention plan and fresh approval |
| Genuine review decisions | M22 | Identified human reviewer actions under an approved attestation policy |
| Credentials, private/paid data or models, unbounded crawl, defaults, public release | None implicit | Separate explicit human decision and scoped plan |

Production end-user behavior remains one persisted bounded public-discovery
confirmation for all implemented ordinary public steps. Development approvals
above authorize frozen validation runs, not extra provider-shaped product
prompts.

## Human-Required Stop Conditions

Stop and update the handoff when continuing requires:

- missing exact authority in the approval map;
- destructive Git/filesystem action or modification of unrelated user work;
- changing a primary criterion after seeing results;
- unresolved rights, privacy, credential, cost, or source-version boundary;
- unavailable genuine human review required by M22;
- a corrupt/invalid harness or evidence artifact whose repair scope is unclear;
- a material project-direction, product-default, scientific-claim, or release
  decision not already authorized; or
- five nonconvergent review rounds on the same material blocker.

## Current Launch Gate

The active M20/G3 launch gate is superseded by the `2026-07-18` arXiv-only
governance migration. Credential/provider routes, packet hashes, approval
tokens, and forward-citation promotion predicates below are historical only.
The supervisor must finish local tests, compile/static/JSON/diff checks, and
the skeptical audit for
`docs/plans/literature_survey_north_star_m20_arxiv_only_500mb_attempt_plan_2026-07-18.md`,
then execute the already authorized invocation exactly once. The live runner
may make only one public arXiv source request, may retain at most
`500,000,000` source bytes and `500,000,000` total evidence-root bytes, and may
not retry or rerun. Forward coverage is `unavailable_out_of_scope` and
non-blocking. The older launch history below does not control execution.

M19 passed its bounded engineering result and terminal review. The exact live
root is immutable, all `14` replay checks pass, and the one-attempt budget is
consumed. M20A local no-network engineering also passes: the official
documentation campaign closed at `6/6`, all `294` route-independent
composition states are covered, strict route-specific adapter gates pass, and
material review agrees. M20B1 now passes and its one two-document attempt is
consumed. Retained official bytes establish query-parameter key placement,
current USD route costs, `meta.cost_usd`, rate-limit USD fields, and `$0.0011`
documented planned OpenAlex usage for the frozen matrix. M20B2 passes its
authorized local synthetic-only scope with `33` focused, `221` combined, and
`42` retained tests plus round-2 terminal review agreement. M20B3 local
integration was then authorized, but five material review rounds did not
converge: round 5 found producer-impossible blocked-after-dispatch
`observed_cost_usd` evidence can pass offline replay. The runbook stopped before
Git staging, commit, clone, wheel, installed validation, or packet freeze. It
read no real key and made no provider call. Continuing now requires human
direction for one additional narrowly scoped replay-integrity repair/review
round. M20B4 and M21-M23 remain non-executable until their separate boundaries
and refreshed predecessor handoffs are satisfied.

The human then authorized that one extra narrow repair/review round. The
repaired replay passes `54` focused and `227` cumulative tests, and terminal
read-only review returned `AGREE`. M20B3 subsequently passed its exact
Git/clone/wheel/install/packet-freeze and packet-review gates. This paragraph
records the historical pre-launch state; the terminal launch gate below
supersedes it. M21-M23 remain non-executable.

## Final Visible Handoff

At any completion or stop, the handoff must state the final milestone reached,
status, result paths, review provenance, commands/tests actually run,
unresolved blockers, nonclaims, and the exact safest next authorized action.

## M20B4 Five-Round Stop - 2026-07-16

M20B4's pre-launch plan/closeout review ended `REVISE` in all five material
rounds. Round 5 rejected the closeout signal predicate for accepting impossible
`supervisor_lifecycle_error` histories. The packet remains unexecuted, both
roots absent, the credential untouched, and attempt authority unconsumed.

Stop before live authorization or launch. Continuing requires human direction
for one extra local repair and one terminal review limited to permitting only
no signal or one cleanup KILL for `supervisor_lifecycle_error` and correcting
its focused tests. M21-M23 remain non-executable.

## M20B4 Extra Repair Review Agreement - 2026-07-16

The human-authorized extra local signal repair passed terminal review. The
active gate is now exact M20B4 human live authorization for the unchanged
packet, not another local repair. Do not read the credential or invoke the
packet before that authorization; M21-M23 remain non-executable.

## M20B4 Terminal Launch Gate - 2026-07-16

The exact authorization was granted and the frozen executable was invoked
once. It returned closed exit code `2`, created no live root, and published no
supervisor manifest. Classify only
`early_supervisor_exit_no_manifest`; the precise internal cause and all
credential/provider/network/cost/privacy/candidate outcomes remain
`not_established`.

The attempt is consumed. Never rerun this packet or reacquire the credential.
M20 is blocked and M21-M23 remain non-executable. The only next boundary is
human direction for a wholly new reviewed M20 campaign with a new packet,
budget, versioned output root, and explicit authority.

## M20/G3 ArXiv-Only Repair Loop - 2026-07-18

This section supersedes all preceding current-gate language. The repair loop
is local and evidence-driven: run the focused tests; patch a localized defect;
rerun the focused test; run the related M20 regression slice; then run compile,
static route/interface scans, JSON validation, program consistency, and diff
hygiene. A material scientific, safety, identity, cap, raw-confinement, or
replay defect blocks launch. Procedural disagreement about retired provider
criteria does not.

After all local checks pass and the plan audit is `PASS`, launch once into a
fresh versioned root. A successful result must include exact source evidence,
backward candidates, complete preliminary classifications, six scholarly
ledgers, omission risks, execution-source preservation, and offline replay. A
failed live result is terminal for the invocation and receives an honest close
record; there is no automatic repair/retry. A pass closes revised M20/G3 and
refreshes the M21 subplan, but does not execute M21 or claim the north-star
mission complete.

## M20/G3 Passed Handoff - 2026-07-18

The one authorized invocation passed with one arXiv request, zero retries,
`26,842,514` retained source bytes, `62` unique preliminary backward
candidates, six scholarly ledgers, explicit forward-unavailable and
identifier-free omission risks, preserved execution sources, and passing
offline replay. The exact close authority is
`docs/plans/literature_survey_north_star_m20_arxiv_only_close_result_2026-07-18.md`.

Do not rerun M20 or M21 or reintroduce a provider feasibility gate. The current
lane is M22 planning only. Its refreshed subplan must be checked for genuine
human identity/attestation, privacy, frozen mission cases, exact evidence
queues, identified execution bytes, and external-action boundaries before any
M22 execution.

## M21 Closed Gate - 2026-07-18

M21 local retained-seed anchors, candidate-context triage, and the authorized
seven-source campaign executed and passed their bounded contracts. The
campaign dispatched seven requests with zero retries and retained seven
packages. Six yielded `288` machine anchors; `1412.6980` is an explicit
`SOURCE_AVAILABLE_TEXT_PARSE_GAP_PDF_FALLBACK_OUT_OF_SCOPE` outcome. Preserved
and repaired offline replay pass, supported claims remain zero, and the live
root is immutable.

M21/G4 is closed. No retry, PDF fallback, provider feasibility, credential,
approval-token, claim-support, or completeness conclusion follows. The active
gate is M22's genuine-human boundary.
