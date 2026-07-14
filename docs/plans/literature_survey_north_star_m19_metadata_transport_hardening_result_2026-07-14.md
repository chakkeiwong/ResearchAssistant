# M19A Metadata Transport And Supervisor Hardening Result

Date: `2026-07-14`
Status: `M19A_LOCAL_CLOSEOUT_CANDIDATE_REPAIRED_GATES_AND_TERMINAL_REREVIEW_PASSED_DO_NOT_EXECUTE_LIVE`
Milestone: `M19_bounded_live_metadata_validation`
Subphase: `M19A_transport_supervisor_hardening`

## Outcome

The initial M19A candidate was wrong relative to the fail-closed transport
contract: terminal review found that an unexpected parser/programmer exception
could be projected as ordinary provider unavailability. Commit
`bb4300c6bce20145a7c41620b0dffb703072e755` repairs that defect and adds two
catching regressions. Fresh gates from an isolated installed wheel now pass.

This remains local fake-transport and supervisor evidence only. No DNS,
OpenAlex, arXiv, source/PDF, GPU, push, or release action ran. M19 remains open
and `DO_NOT_EXECUTE_LIVE` remains active.

## Authority And Evidence

| Item | Value |
| --- | --- |
| M18 closeout | `e7f1499e135757c0460c040f3fa317e6bdd56dc9` |
| M19 product candidate | `23e218b563e2e554c02c1ac063fea1f73034edf4` |
| Reviewed harness commit | `945332f891e40cc02d53806bc3ca4b2157cc51e0` |
| Parser-boundary repair | `bb4300c6bce20145a7c41620b0dffb703072e755` |
| Superseding validation root | `docs/validation/literature_survey_m19_transport_hardening_round3_2026-07-14/` |
| Rejected terminal verdict | `docs/reviews/literature_survey_m19_transport_hardening_terminal_review_verdict_round1_2026-07-14.md` |
| Live root | `docs/validation/literature_survey_m19_live_metadata_2026-07-14/`, absent |

The exact single-parent lineage is
`e7f1499 -> 23e218b -> 945332f -> bb4300c`.

## Material Repair

Known malformed JSON/XML remains a closed provider-unavailable outcome.
Unexpected parser exceptions now raise a sanitized
`m19_unexpected_parser_failure` boundary error. The transport regression
requires no request row to be emitted as unavailable, and the worker regression
requires `invalid_ledger`, zero accepted rows, and no passing summary. The
focused repair gate passed `56` tests before the repair commit.

## Fresh Gate Results

All gates ran from the offline-built wheel installed in the isolated clone at
`/tmp/ra_m19_isolated_bb4300c`, with `PYTHONPATH` unset and
`CUDA_VISIBLE_DEVICES=-1`.

| Gate | Result | JUnit SHA-256 |
| --- | --- | --- |
| Transport | `26 passed in 0.10s` | `c8f4fd9347032a446652cad8e6afcd104c93af917ac497c27b5244f42e90cb6c` |
| Supervisor | `30 passed in 4.56s` | `44b5a9681a6882ee3c3ba8de3baa09931a04686eb1a3b5cae8222d99e8ddbf4c` |
| Affected Phase 7 | `58 passed in 3.32s` | `cc5f878231cb31d7d0c70459bd7b65266afa45fb71085e9f2991e9295f0bd4b0` |
| Cumulative M16/M17 | `846 passed in 544.80s` | `e7fc8397bc7d64d9ed4320175de7461014f5cec562559c2163b1e4dbbe6708c9` |
| Full CLI | `125 passed in 700.65s` | `b315f049e57a6640453d48b76ab71f927977d0cd64c98151ae6b4f118abbc850` |

The installed wheel SHA-256 is
`6605ddeb46b15c2e0f29b23466743cf2c48db6a72eb2434019b2add22d135888`.
The full-CLI scratch at `/tmp/ra_m19_full_cli_basetemp_round3/` is retained but
is not authoritative or hashed into the result root.

## Attempt Accounting

| Attempt | Classification | Decision |
| --- | --- | --- |
| Original round 1 | Material product defect: unexpected parser failure became provider unavailable | Rejected by terminal review; preserved |
| Repair focused | `56 passed` after fail-closed code/test patch | Supported commit `bb4300c` |
| Repair round 2 | Current shell lacked installed `research_assistant.survey` with `PYTHONPATH` unset | Harness failure; preserved |
| Isolated install first try | Pip skipped the wheel because inherited system package had same version | Harness failure; repaired with `--force-reinstall --no-index --no-deps` |
| Repair round 3 | All five gates from isolated installed wheel | Superseding local evidence |

## Fake Supervisor Replay

The round-3 fake run is bound to `bb4300c` and independently replayed:

- summary `passed`, `boundary_valid=true`;
- request ledger `complete`, with four ordered deterministic no-network
  unavailable rows;
- normalized record count `0`;
- root inventory count `18`; and
- route, ledger, command-exit, environment, inventory, and public-manifest
  hashes all agree.

This proves the local fake boundary transaction after the parser repair. It
does not establish real provider reachability or contents.

## Decision And Inference

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action |
| --- | --- | --- | --- | --- |
| Pass repaired M19A pending terminal rereview | Passed after material repair | Round-1 veto repaired; fresh gates pass | Real transport/provider behavior unobserved | Rereview, docs/evidence closeout, exact one-shot approval request |

No stochastic or provider ranking was performed. Test counts, runtimes,
fixture outcomes, and byte counts are descriptive. Default readiness is not
established.

## Protected Work And Nonclaims

The seven protected tracked edits remain byte-identical to their recorded
pre-M19A state. No wildcard staging, reset, restore, clean, stash, rebase,
amend, push, or release occurred.

M19A does not establish live behavior, metadata quality, citation recall,
source/claim support, completeness, scientific correctness, product readiness,
M19 completion, or north-star completion.

## Handoff

If terminal rereview agrees, create a docs/evidence-only direct child of
`bb4300c`, finalize the approval packet against that actual commit, and request
fresh user approval for exactly one live attempt. Without that approval, stop
at the valid network boundary with `DO_NOT_EXECUTE_LIVE`.

Terminal rereview round 2 returned `AGREE` with no material findings.

The docs/evidence-only closeout commit cannot contain its own commit hash. Its
actual hash will be recorded after commit in an external replay record and in
the finalized, still-uncommitted exact live approval packet.
